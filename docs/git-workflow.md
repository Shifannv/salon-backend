# Git workflow

Use one branch and one pull request per Jira task. Include the Jira key in the branch
name, for example:

```text
thameem/SACS-48-backend-location
```

Before opening a pull request, run from `backend/`:

```bash
python -m pytest
python -m ruff check app tests migrations
```

Do not commit secrets, local `.env` files, generated caches, or frontend source. Do not
commit directly to a stable `main` branch unless the project owner explicitly requests
it.
