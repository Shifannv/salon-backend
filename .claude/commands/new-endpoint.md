---
description: Plan then implement a new API endpoint through all layers, with tests.
argument-hint: "{description of the endpoint}"
allowed-tools: Read, Grep, Glob, Edit, Write, Skill, Bash(python -m ruff:*), Bash(python -m pytest:*), Bash(git status:*), Bash(git diff:*)
---

Endpoint requested: $ARGUMENTS

Apply `karpathy-guidelines`, `fastapi-endpoint` and `auth-and-roles`.

1. **Plan first.** State assumptions, the layers and files you will touch (domain, port, use case, adapter, schema, route), the roles allowed and the ownership rule, error cases and their HTTP codes, and the test list (including the role matrix). Then **stop and wait for the user's OK**.
2. After approval, implement in layer order per `fastapi-endpoint`. Match neighbouring code. No extras.
3. Add the tests from the plan.
4. From `backend/`, run `python -m ruff check app tests migrations` and `python -m pytest -q`. Report the real results.
5. If the endpoint needs a schema change, stop and use `/new-migration` instead of touching SQL here.
