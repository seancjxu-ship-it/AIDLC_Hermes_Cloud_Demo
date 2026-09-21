FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN sed -i 's/\r$//' /app/scripts/entrypoint.sh /app/scripts/git-askpass.sh \
    && chmod +x /app/scripts/entrypoint.sh /app/scripts/git-askpass.sh

EXPOSE 8000
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["api"]
