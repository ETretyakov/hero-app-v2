FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir poetry==2.4.1 poetry-plugin-export

COPY pyproject.toml poetry.lock ./

RUN poetry export --without dev --without-hashes -f requirements.txt -o /tmp/requirements.txt \
    && pip install --no-cache-dir -r /tmp/requirements.txt

COPY . .

EXPOSE 8080

ENTRYPOINT ["./entrypoint.sh"]
