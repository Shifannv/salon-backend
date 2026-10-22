#!/usr/bin/env python3
"""Route each prompt to the skills that match it, and load routing at chat/agent start.

Modes (first CLI arg):
  session   SessionStart: print the routing doc so the chat starts with it.
  prompt    UserPromptSubmit: read the prompt from stdin JSON, print matched skills.
  subagent  SubagentStart: emit JSON additionalContext so agents read the routing doc.

Only skills whose keywords match are suggested; nothing is loaded for all tasks.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROUTING_DOC = ROOT / "docs" / "agent-skill-routing.md"

# (skill, reason, keyword regex). Order = priority within the printed list.
RULES = [
    ("superpowers:systematic-debugging", "bug, error or failing test",
     r"\b(bug|error|exception|traceback|fail(s|ed|ing|ure)?|broken|crash|500|not working|regression)\b"),
    ("superpowers:brainstorming", "new feature or behaviour change",
     r"\b(new feature|add (a |an )?(feature|endpoint|screen)|build|implement|design a|let'?s add|i want (to )?(add|create|make))\b"),
    ("fastapi-endpoint", "adding or changing an endpoint",
     r"\b(endpoint|router|route|response_model|schema|api (change|contract))\b"),
    ("auth-and-roles", "JWT, roles, MFA or ownership",
     r"\b(auth|jwt|role|mfa|aal2|permission|ownership|idor|login|token)\b"),
    ("alembic-migration", "schema change",
     r"\b(migration|alembic|schema|column|table|index|ddl|rls)\b"),
    ("booking-and-payments", "booking, availability, payment or webhook",
     r"\b(booking|availability|slot|payment|razorpay|webhook|refund|payout|commission)\b"),
    ("pytest-testing", "writing or fixing tests",
     r"\b(test|tests|pytest|coverage|fixture|mock)\b"),
    ("workers-and-deploy", "workers, Compose, CI or deploy",
     r"\b(deploy|cloud run|docker|compose|worker|ci|release|rollout|traffic|revision|vm)\b"),
    ("supabase", "Supabase queries, RLS, storage or auth",
     r"\b(supabase|rls|storage bucket|postgres|sql)\b"),
    ("supabase-postgres-best-practices", "Postgres schema, index or query design",
     r"\b(index|query plan|slow query|schema design|explain analyze|n\+1)\b"),
    ("agent-memory", "memory or session notes",
     r"\b(agent-memory|progress file|sessions\.md|checkpoint|wrap)\b"),
    ("interview", "requirements unclear",
     r"\b(not sure|unclear|scope this|spec|requirements)\b"),
    ("ste", "documentation or explanation wording",
     r"\b(document(ation)?|docs?|readme|explain|comment)\b"),
    ("webapp-testing", "HTTP or browser testing",
     r"\b(playwright|browser test|e2e|smoke test)\b"),
    ("mcp-builder", "MCP server work",
     r"\b(mcp server|\.mcp\.json|fastmcp)\b"),
    ("founder-board", "new product idea (business lens)",
     r"\b(business idea|pricing plan|subscription tier|monetis|monetiz|go to market|competitor)\b"),
    ("graphify", "codebase question",
     r"\b(where is|how does|architecture|explain the code|call path|who calls)\b"),
]

ALWAYS = ["senior-backend-engineer (first in every chat)", "karpathy-guidelines (any code written or reviewed)"]


def read_doc() -> str:
    try:
        return ROUTING_DOC.read_text(encoding="utf-8")
    except OSError:
        return "docs/agent-skill-routing.md is missing; read AGENTS.md and CLAUDE.md instead."


def match(prompt: str):
    text = prompt.lower()
    return [(s, why) for s, why, rx in RULES if re.search(rx, text)]


def prompt_mode() -> None:
    try:
        prompt = json.load(sys.stdin).get("prompt", "")
    except (json.JSONDecodeError, ValueError):
        return
    hits = match(prompt)[:5]
    lines = ["<skill-routing>", "Always: " + "; ".join(ALWAYS)]
    if hits:
        lines.append("Matched for this prompt (invoke with the Skill tool before acting):")
        lines += [f"- {s}: {why}" for s, why in hits]
    else:
        lines.append("No extra skill matched; pick from docs/agent-skill-routing.md if the task changes.")
    lines.append("Skip founder-* skills for fixes/refactors. Reassess if the task changes.")
    lines.append("</skill-routing>")
    print("\n".join(lines))


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "prompt"
    if mode == "session":
        print("<skill-routing-doc>\n" + read_doc() + "\n</skill-routing-doc>")
    elif mode == "subagent":
        ctx = "Read this skill routing first, then pick only the skills your task needs:\n" + read_doc()
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "SubagentStart", "additionalContext": ctx}}))
    else:
        prompt_mode()


if __name__ == "__main__":
    main()
