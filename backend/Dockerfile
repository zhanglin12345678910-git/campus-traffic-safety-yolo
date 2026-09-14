FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend
COPY backend/requirements.txt /tmp/requirements.txt
ARG PYTORCH_CPU_INDEX_URL=https://download.pytorch.org/whl/cpu
RUN pip install --upgrade pip \
    && pip install --index-url ${PYTORCH_CPU_INDEX_URL} \
        torch==2.2.2+cpu torchvision==0.17.2+cpu \
    && pip install -r /tmp/requirements.txt

COPY backend /app/backend
RUN mkdir -p /app/uploads /app/outputs /app/models

EXPOSE 8000
CMD ["sh", "/app/backend/docker-entrypoint.sh"]
