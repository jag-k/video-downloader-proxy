from hashlib import md5
from typing import Self

from pydantic import BaseModel, Field
from tortoise import Model, fields


class ProxyRequest(BaseModel):
    url: str = Field(..., description="Url to download", max_length=2048)
    user_agent: str | None = Field(
        None,
        description="User-Agent for download data from url",
        max_length=1024,
    )


class Proxy(Model):
    hash = fields.CharField(max_length=32, pk=True)
    url = fields.TextField()
    user_agent = fields.CharField(max_length=1024, null=True)

    # Defining ``__str__`` is also optional, but gives you pretty
    # represent of model in debugger and interpreter
    def __str__(self):
        return str(self.url)

    @classmethod
    async def get_or_create_proxy(
            cls,
            proxy: ProxyRequest,
    ) -> tuple[Self, bool]:
        proxy_hash = md5(
            '\t'.join(
                (
                    proxy.url,
                    proxy.user_agent or ''
                )
            ).strip().encode()
        ).hexdigest()
        obj, created = await cls.get_or_create(
            hash=proxy_hash,
            defaults={
                'url': proxy.url,
                'user_agent': proxy.user_agent,
            }
        )
        return obj, created

    @property
    def request(self) -> ProxyRequest:
        return ProxyRequest(url=self.url, user_agent=self.user_agent)
