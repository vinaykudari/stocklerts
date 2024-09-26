FROM python:3.11

ARG FINNHUB_API_KEY
ARG ENCRYPT_KEY

ENV FINNHUB_API_KEY=${FINNHUB_API_KEY}
ENV ENCRYPT_KEY=${ENCRYPT_KEY}

RUN pip install poetry

WORKDIR /app

COPY pyproject.toml poetry.lock config.yaml ./
COPY app ./app

RUN poetry install --no-interaction --no-ansi

CMD ["poetry", "run", "python", "-m", "app.main"]