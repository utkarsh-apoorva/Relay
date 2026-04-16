# ── Stage 1: build frontend ──────────────────────────────────────────────────
FROM node:20-slim AS frontend-build

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ── Stage 2: backend + Tailscale ─────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Install Tailscale
RUN apt-get update && apt-get install -y curl iptables iproute2 && \
    curl -fsSL https://tailscale.com/install.sh | sh && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend-build /frontend/dist ./frontend/dist

EXPOSE 8000

# Start Tailscale in userspace mode, then run uvicorn
CMD tailscaled --tun=userspace-networking --socks5-server=localhost:1055 & \
    sleep 2 && \
    tailscale up --authkey=${TS_AUTHKEY} --hostname=relay-railway --accept-routes & \
    sleep 3 && \
    uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
