FROM python:3.12-alpine

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apk add --no-cache ca-certificates curl tzdata su-exec \
    && addgroup -S appgroup \
    && adduser -S -D -H -u 10001 -G appgroup appuser \
    && mkdir -p /app /data

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY export_energy_to_excel.py sync_energy_to_sqlite.py addon_runner.py ./
COPY run.sh /run.sh
RUN chmod 755 /run.sh \
    && chown -R appuser:appgroup /app \
    && chmod -R a+rX /app

VOLUME ["/data"]
ENTRYPOINT ["/run.sh"]