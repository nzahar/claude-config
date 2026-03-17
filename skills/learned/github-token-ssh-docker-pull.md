# GITHUB_TOKEN for Server-Side Docker Pull in SSH Deploy Steps

**Extracted:** 2026-03-17
**Context:** GitHub Actions deploy workflows that SSH into a server and pull images from GHCR

## Problem
When deploying via SSH in GitHub Actions, the server needs to authenticate with GHCR to pull images.
The naive solution is to create a separate PAT secret (`GHCR_PAT`) with `read:packages` scope — but this requires manual token creation and rotation.

## Solution
Pass `${{ secrets.GITHUB_TOKEN }}` directly inside the SSH script string.
GitHub Actions substitutes all `${{ }}` expressions **before** sending the script to the server via SSH.
By the time the shell runs on the server, it sees a literal token string — no PAT needed.

```yaml
- name: Deploy
  uses: appleboy/ssh-action@v1
  with:
    host: ${{ secrets.SERVER_HOST }}
    username: ${{ secrets.SERVER_USER }}
    key: ${{ secrets.SERVER_SSH_KEY }}
    script: |
      echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin
      docker compose pull
      docker compose up -d
```

Also requires the deploy job to explicitly declare `packages: read` permission, otherwise GITHUB_TOKEN won't have that scope:

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: read
```

## When to Use
Any GitHub Actions workflow that:
- SSHes into a server to deploy
- Needs to pull images from GHCR (GitHub Container Registry)
- You want to avoid creating and managing a separate PAT secret

## Notes
- GITHUB_TOKEN is valid only for the duration of the workflow run — sufficient for `docker pull`
- Fine-grained PATs do NOT support `packages` scope — must use classic PATs if a persistent token is needed
- The `${{ }}` substitution trick works for any secret passed into SSH scripts, not just GITHUB_TOKEN