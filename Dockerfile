FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY . ./

RUN pip install --no-cache-dir .

ARG APP_UID=1000
ARG APP_GID=1000
RUN groupadd -g ${APP_GID} appuser && \
    useradd -u ${APP_UID} -g appuser -s /bin/bash -m appuser

RUN mkdir -p /data /logs && \
    chown -R appuser:appuser /data /logs /app

USER appuser

EXPOSE 5000

VOLUME ["/data", "/logs"]

CMD ["python", "-m", "parkVar.main"]
