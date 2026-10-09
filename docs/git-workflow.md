# Git workflow

Use a focused branch and pull request for each coherent change. Use descriptive branch
names, for example:

```text
thameem/superadmin-website-contract
```

Before opening a pull request, run from `backend/`:

```bash
python -m pytest
python -m ruff check app tests migrations
```

Do not commit secrets, local `.env` files, generated caches, or frontend source. Do not
commit directly to a stable `main` branch unless the project owner explicitly requests
it.
