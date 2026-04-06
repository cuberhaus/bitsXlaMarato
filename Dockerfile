# Stage 1: Build Angular frontend
FROM node:22-slim AS frontend

WORKDIR /app
COPY web/frontend/package.json web/frontend/package-lock.json ./
RUN npm ci

COPY web/frontend/ ./
RUN npm run build

# Stage 2: CUDA runtime with Python backend
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-dev \
    libgl1 libglib2.0-0 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY web/backend/requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

COPY models/maratoNuevo.pt models/marato.pt ./models/
COPY web/backend/ ./web/backend/
COPY --from=frontend /app/dist/frontend/browser/ ./web/frontend/dist/frontend/browser/

WORKDIR /app/web/backend

ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV PORT=8001

EXPOSE 8001

CMD ["python3", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
