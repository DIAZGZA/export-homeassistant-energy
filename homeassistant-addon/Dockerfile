FROM python:3.12-alpine

ARG SOURCE_COMMIT=28a167610bf66e4cb46833927d5c20597dc85bd6
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENERGY_SQLITE_DB=/data/energy_daily.sqlite

RUN apk add --no-cache ca-certificates curl tzdata \
    && addgroup -S appgroup \
    && adduser -S -D -H -u 10001 -G appgroup appuser \
    && mkdir -p /app /data \
    && curl -fsSL "https://raw.githubusercontent.com/DIAZGZA/export-homeassistant-energy/${SOURCE_COMMIT}/requirements.txt" -o /app/requirements.txt \
    && curl -fsSL "https://raw.githubusercontent.com/DIAZGZA/export-homeassistant-energy/${SOURCE_COMMIT}/export_energy_to_excel.py" -o /app/export_energy_to_excel.py \
    && curl -fsSL "https://raw.githubusercontent.com/DIAZGZA/export-homeassistant-energy/${SOURCE_COMMIT}/sync_energy_to_sqlite.py" -o /app/sync_energy_to_sqlite.py \
    && curl -fsSL "https://raw.githubusercontent.com/DIAZGZA/export-homeassistant-energy/${SOURCE_COMMIT}/docker-scripts/scheduler_loop.py" -o /app/scheduler_loop.py \
    && pip install --no-cache-dir -r /app/requirements.txt \
    && chown -R appuser:appgroup /app /data \
    && chmod -R a+rX /app

COPY run.sh /run.sh
RUN chmod 755 /run.sh

VOLUME ["/data"]
USER appuser
ENTRYPOINT ["/run.sh"]