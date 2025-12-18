FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY . ./

RUN pip install --no-cache-dir .

EXPOSE 5000

VOLUME ["/data", "/logs"]

CMD ["python", "-m", "parkVar.main"]
