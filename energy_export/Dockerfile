FROM python:3.12-alpine

ARG SOURCE_COMMIT=5413bd69e674fb5c807ddc832dab420af6d81518
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apk add --no-cache ca-certificates curl tzdata su-exec \
    && addgroup -S appgroup \
    && adduser -S -D -H -u 10001 -G appgroup appuser \
    && mkdir -p /app /data \
    && curl --fail --silent --show-error --location --retry 3 "https://raw.githubusercontent.com/DIAZGZA/export-homeassistant-energy/${SOURCE_COMMIT}/requirements.txt" -o /app/requirements.txt \
    && curl --fail --silent --show-error --location --retry 3 "https://raw.githubusercontent.com/DIAZGZA/export-homeassistant-energy/${SOURCE_COMMIT}/export_energy_to_excel.py" -o /app/export_energy_to_excel.py \
    && curl --fail --silent --show-error --location --retry 3 "https://raw.githubusercontent.com/DIAZGZA/export-homeassistant-energy/${SOURCE_COMMIT}/sync_energy_to_sqlite.py" -o /app/sync_energy_to_sqlite.py \
    && pip install --no-cache-dir -r /app/requirements.txt \
    && chown -R appuser:appgroup /app \
    && chmod -R a+rX /app

COPY addon_runner.py /app/addon_runner.py
COPY run.sh /run.sh
RUN chmod 755 /run.sh /app/addon_runner.py

WORKDIR /app
VOLUME ["/data"]
ENTRYPOINT ["/run.sh"]