# Git workflow

Use a focused branch and pull request for each coherent change. Use descriptive branch
names, for example:

```text
thameem/superadmin-website-contract
```

Before every AI commit/push and before opening a pull request, run from the repository root:

```bash
bash backend/scripts/check-ci.sh
```

This runs the complete local lint, PostgreSQL 18 test and Docker verification.
Use a Python environment with the development dependencies installed and Docker
running; see [CI/CD](../backend/docs/CI_CD.md) for Windows and Linux commands.
Fix failures before delivery. After an authorized push, verify GitHub checks for
that exact commit before merging. Eligible owner merges to `main` automatically
deploy production after the workflow checks and release guards pass. Production
migrations still require their separate reviewed procedure.

Do not commit secrets, local `.env` files, generated caches, or frontend source. Do not
commit directly to a stable `main` branch unless the project owner explicitly requests
it.
