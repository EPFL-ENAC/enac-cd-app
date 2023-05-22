FROM python:3.10-alpine as poetry-stage
WORKDIR /app
RUN apk add --no-cache \
    gcc \
    curl \
    musl-dev
RUN curl -sSL https://install.python-poetry.org | python3 -
COPY ./pyproject.toml ./poetry.lock* /app/
RUN /root/.local/bin/poetry export --without-hashes --format=requirements.txt --output requirements.txt


FROM python:3.10-slim as production-stage
EXPOSE 80
WORKDIR /app
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY --from=poetry-stage /app/requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt

COPY ./enac_cd_app /app/enac_cd_app
COPY ./log_conf.yml /app/

CMD [ "uvicorn", "enac_cd_app.main:app", \
    "--host", "0.0.0.0", \
    "--port", "80", \
    "--proxy-headers", "--forwarded-allow-ips", "*", \
    "--log-config", "log_conf.yml" \
]
