# Nginx Config for Production SPA with API Proxy

**Extracted:** 2026-03-17
**Context:** Nginx serving a React/Vue/Svelte SPA that proxies API calls to a backend service

## Problem
Several common gotchas when setting up nginx for a containerised SPA + backend stack:
1. File uploads fail with 413 — nginx default body limit is 1MB
2. Missing SPA fallback — direct URL access returns 404
3. Missing forwarded headers — backend can't see real client IP/protocol
4. API proxy path not stripped — `/api/foo` hits backend as `/api/foo` instead of `/foo`

## Solution

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;
    client_max_body_size 200m;  # match your app's upload limit

    location /api/ {
        proxy_pass http://backend:8000/;  # trailing slash strips /api prefix
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;  # increase for long-running API calls
    }

    location / {
        try_files $uri $uri/ /index.html;  # SPA fallback
    }
}
```

Key details:
- `proxy_pass http://backend:8000/` — trailing slash on proxy_pass URL strips the matched location prefix (`/api/`)
- `try_files $uri $uri/ /index.html` — serves real files first, falls back to SPA for client-side routing
- `client_max_body_size` — must be set at `server` or `http` level, defaults to 1m

## When to Use
Any React/Vue/Svelte app in Docker where:
- Frontend is served by nginx
- API calls go to a separate backend container on the same Docker network
- App has file uploads