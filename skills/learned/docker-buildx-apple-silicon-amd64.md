---
name: Docker Buildx Cross-Platform Build for Apple Silicon
description: Building linux/amd64 images on Apple Silicon (M-series) for deployment to amd64 servers
type: feedback
---

# Docker Buildx Cross-Platform Build for Apple Silicon

**Extracted:** 2026-03-17
**Context:** Local build scripts on macOS M-series deploying to Linux amd64 servers

## Problem
Images built on Apple Silicon (arm64) and pushed to a registry will fail on amd64 Linux servers with:

```
The requested image's platform (linux/arm64) does not match the
detected host platform (linux/amd64/v4) and no specific platform was requested
```

The container starts but immediately crashes or behaves incorrectly.

## Solution
Use `docker buildx build --platform linux/amd64` with `--push` to build and push in one step:

```bash
docker buildx build --platform linux/amd64 --push \
  -t ghcr.io/org/image:tag ./path/to/context

# For non-default Dockerfile:
docker buildx build --platform linux/amd64 --push \
  -f ./path/to/Dockerfile \
  -t ghcr.io/org/image:tag ./path/to/context
```

`--push` is required with `--platform` for cross-platform builds (buildx sends to registry directly; local `docker images` won't show it).

## When to Use
- Any build script run on an Apple Silicon Mac targeting Linux amd64 servers
- Replace `docker build` + `docker push` pair with single `docker buildx build --platform linux/amd64 --push`
- GitHub Actions ubuntu-latest runners are amd64 natively — no change needed there