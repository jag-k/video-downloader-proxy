import os
from pathlib import Path
from typing import AsyncGenerator

from aiohttp import ClientSession, ClientConnectorError
from dotenv import load_dotenv
from fastapi import FastAPI, Request, exceptions
from starlette.responses import StreamingResponse
from tortoise import Tortoise

from models import Proxy, ProxyRequest

app = FastAPI()

BASE_PATH = Path(__file__).resolve().parent
CONFIG_PATH = Path(os.getenv("CONFIG_PATH", BASE_PATH / "config"))
DATA_PATH = Path(os.getenv("DATA_PATH", BASE_PATH / "data"))

for path in (BASE_PATH, CONFIG_PATH, DATA_PATH):
    if not path.exists():
        path.mkdir()

for path in (
        BASE_PATH / ".env",
        CONFIG_PATH / ".env",
        BASE_PATH / ".env.local",
        CONFIG_PATH / ".env.local",
):
    if path.exists():
        load_dotenv(path)
        print(f"Loaded envs from {path}")
        break
else:
    print("No .env file found")

BASE_URL = os.getenv("BASE_URL", None)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite://{DATA_PATH}/db.sqlite3")
BEARER_AUTH = os.getenv("BEARER_AUTH", None)


@app.middleware("http")
async def auth(request: Request, call_next):
    if BEARER_AUTH:
        auth_header = request.headers.get("Authorization")
        if not auth_header or auth_header != f"Bearer {BEARER_AUTH}":
            raise exceptions.HTTPException(
                status_code=401,
                detail="Unauthorized",
                headers={"WWW-Authenticate": "Bearer"},
            )
    return await call_next(request)


@app.on_event("startup")
async def startup():
    await Tortoise.init(
        db_url=DATABASE_URL,
        modules={'models': ['models']}
    )
    # Generate the schema
    await Tortoise.generate_schemas()


@app.on_event("shutdown")
async def shutdown():
    await Tortoise.close_connections()


@app.post("/", response_description="Url to download")
async def request_url(request: Request, proxy: ProxyRequest) -> str:
    proxy_data, _ = await Proxy.get_or_create_proxy(proxy)

    base_url = BASE_URL or str(request.url).rstrip('/')

    return f"{base_url}/{proxy_data.hash}"


async def get_file(proxy: ProxyRequest) -> AsyncGenerator[bytes, bytes]:
    headers = None
    if proxy.user_agent:
        headers = {"User-Agent": proxy.user_agent}
    async with ClientSession(headers=headers) as session:
        async with session.get(proxy.url) as resp:
            async for c in resp.content.iter_chunks():
                data, end = c
                yield data
                if end:
                    break


@app.get("/{proxy_hash}")
async def download(proxy_hash: str) -> StreamingResponse:
    proxy = await Proxy.get_or_none(hash=proxy_hash)
    if not proxy:
        raise exceptions.HTTPException(404, "Not Found hash")
    try:
        async with ClientSession(
                headers={"User-Agent": proxy.user_agent}) as session:
            async with session.get(proxy.url) as resp:
                data = dict(
                    status_code=resp.status,
                    headers=resp.headers,
                    media_type=resp.content_type,
                )
    except ClientConnectorError:
        raise exceptions.HTTPException(400, "Cannot connect to host")
    except Exception as e:
        raise exceptions.HTTPException(500, str(e))

    return StreamingResponse(
        get_file(proxy.request),
        **data,
    )
