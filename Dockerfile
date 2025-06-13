FROM python:3.11

ARG FINNHUB_API_KEY
ARG ENCRYPT_KEY

ENV FINNHUB_API_KEY=${FINNHUB_API_KEY}
ENV ENCRYPT_KEY=${ENCRYPT_KEY}

RUN pip install uv

WORKDIR /app

COPY pyproject.toml uv.lock config.yaml ./
COPY app ./app
COPY resources ./resources

RUN uv pip install --system .

RUN mkdir -p /app/logs

CMD ["python", "-m", "app.main"]
