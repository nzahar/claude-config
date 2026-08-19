---
name: ghcr-actions
description: "GHCR + GitHub Actions gotchas — use when a workflow pushes or pulls ghcr.io images under a GitHub organization, or a deploy step on a remote server needs to docker login to GHCR: org packages need per-package Actions access (repo-level permissions are not enough) and GITHUB_TOKEN can be passed straight into the SSH script instead of a PAT."
---

# GHCR + GitHub Actions gotchas

# GHCR Organization Packages — Actions Permission Denied

**Context:** GitHub Container Registry + GitHub Actions + org-owned packages

## Problem
When GHCR packages exist under a GitHub **organization**, `GITHUB_TOKEN` cannot read or write them — even with `permissions: packages: write` in the workflow. Errors:

**Push (build):**
```
ERROR: denied: permission_denied: write_package
```

**Pull (deploy):**
```
403 Forbidden: unexpected status from HEAD request to
https://ghcr.io/v2/<owner>/<image>/manifests/latest
```

This happens because org packages have their own access control, independent of workflow permissions. Packages created by a local push (not via Actions) are not linked to any repo at all.

## Solution

**Two required steps:**

### 1. Add OCI source label to Dockerfile
GHCR reads this label on push and links the package to the specified repository:

```dockerfile
LABEL org.opencontainers.image.source=https://github.com/OrgName/RepoName
```

Place it on the final stage image (after `FROM`).

### 2. Grant Actions access in package settings
Go to: `https://github.com/orgs/<org>/packages/container/<image>/settings`
→ **Manage Actions access** → **Add Repository** → select the repo → role **Write** (for push) or **Read** (for pull-only)

This must be done for **each package** (e.g., both `pnl-backend` and `pnl-frontend`).

**Note:** Repo-level "Workflow permissions: Read and write" is necessary but NOT sufficient for org packages.

## Diagnostic Checklist
1. Check workflow has `permissions: packages: write` — ✅ but not enough alone
2. Check repo Settings → Actions → Workflow permissions → "Read and write" — ✅ but not enough alone
3. Check each **package settings** → Manage Actions access → repo added with correct role — **this is usually the missing step**

## When to Use
- `write_package` or `403` errors pushing/pulling GHCR images from GitHub Actions
- Images stored in GHCR under a GitHub organization
- Packages were initially created by local push (not via Actions)


---

# GITHUB_TOKEN for Server-Side Docker Pull in SSH Deploy Steps

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
