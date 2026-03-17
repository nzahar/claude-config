---
name: GHCR Organization Packages — Actions Permission Denied
description: GHCR packages under a GitHub org require explicit repo-level Actions access, causing write_package or 403 errors even with correct workflow permissions
type: feedback
---

# GHCR Organization Packages — Actions Permission Denied

**Extracted:** 2026-03-17
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