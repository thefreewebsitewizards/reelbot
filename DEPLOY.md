# Deployment Guide

Production deployment uses Docker Compose with Cloudflare Tunnel for secure HTTPS ingress without exposing ports or managing certificates.

## Prerequisites

- Docker and Docker Compose installed on the host
- A Cloudflare account with a domain configured (leadneedleai.com)
- `.env` file with all required application secrets

## Setup Steps

### 1. Create a Cloudflare Tunnel

1. Go to [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/)
2. Navigate to **Networks > Tunnels**
3. Click **Create a tunnel**
4. Choose **Cloudflared** as the connector type
5. Name the tunnel (e.g., `reel-bot`)
6. Copy the tunnel token from the install page

### 2. Configure Tunnel Routing

In the tunnel configuration, add a public hostname:

| Field       | Value                              |
| ----------- | ---------------------------------- |
| Subdomain   | `reel-bot`                         |
| Domain      | `leadneedleai.com`                 |
| Type        | `HTTP`                             |
| URL         | `app:8000`                         |

This routes `reel-bot.leadneedleai.com` to the `app` Docker service on port 8000. Cloudflare handles TLS termination automatically.

### 3. Configure Environment Variables

Add these to your `.env` file:

```bash
# Cloudflare Tunnel
CLOUDFLARE_TUNNEL_TOKEN=<paste-token-from-step-1>

# Public URL (used by the app for webhook callbacks, etc.)
PUBLIC_URL=https://reel-bot.leadneedleai.com
```

### 4. Deploy

```bash
# Build and start all services
docker compose up -d --build

# Check that both containers are running
docker compose ps

# View app logs
docker compose logs -f app

# View tunnel logs
docker compose logs -f cloudflared
```

### 5. Verify

```bash
# Health check via public URL
curl https://reel-bot.leadneedleai.com/health
```

Expected response: `{"status": "ok"}`

## Updating

```bash
# Pull latest code, rebuild, and restart
git pull
docker compose up -d --build
```

## Troubleshooting

**Tunnel not connecting:** Check `CLOUDFLARE_TUNNEL_TOKEN` is correct in `.env`. View logs with `docker compose logs cloudflared`.

**App not starting:** Check application logs with `docker compose logs app`. Ensure all required env vars are set.

**502 errors on the public URL:** The app container may still be starting. Wait a few seconds and retry. Check `docker compose ps` to confirm the app is healthy.
