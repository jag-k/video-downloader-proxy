# FastAPI Dockerfile with Python 3.11
FROM python:3.11-slim-buster

# Set the working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DATA_PATH="/data"
ENV CONFIG_PATH="/config"
ENV DATABASE_JSON_PATH="data/database.json"
ENV ROOT_PATH="/"

# Install poetry dependencies
COPY poetry.lock pyproject.toml ./
RUN pip install poetry==1.4.1
RUN poetry config virtualenvs.create false
RUN poetry install --no-dev --no-interaction --no-ansi --no-root

# Copy the rest of the code
COPY . .

# Expose the port
EXPOSE 62284

# Run the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "62284", "--root-path", "echo $ROOT_PATH"]

