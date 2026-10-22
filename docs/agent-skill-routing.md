# Task-based skill routing for the salon projects

Read this at the start of each chat in the backend, customer or owner repository,
and reassess when the user adds a task. Choose skills by the work being performed;
load only the matching SKILL.md and necessary references. A routine product fix does
not require a business-plan, pricing, competitor or branding workflow.

Keep the three repositories separate. Follow each repository's architecture,
secrets, verification and deployment rules. Read existing branch/session notes before
resuming work. Source changes, installed verification builds and deployed releases
must be reported separately.

| Task | Guidance to load when available |
| --- | --- |
| Backend investigation or changes | Backend `.claude/skills/senior-backend-engineer/SKILL.md`, then the matching local domain skill |
| API implementation, contract, testing or deployment | `postman:api-engineer`, or its specific testing/documentation skill when intent is already narrow |
| Supabase work | `supabase`; database/schema/SQL changes also use `supabase-postgres-best-practices` |
| Owner staff, catalog, photos or QR configuration | Owner `.claude/skills/salon-setup-and-media/SKILL.md` |
| Owner booking/calendar flows | Owner `.claude/skills/booking-management-ui/SKILL.md` |
| Owner API/cache/session work | Owner `api-client-and-state` or `auth-roles-and-approval` skill, according to the change |
| UI defects, accessibility or visual refinement | `impeccable`, using the native workflow for the mobile apps and preserving the incumbent design for scoped fixes |
| Owner tests or local build verification | Owner `.claude/skills/testing-and-release/SKILL.md` |
| Customer app changes | Customer `AGENTS.md`, exact installed Expo-version documentation, and relevant available native UI/API/testing skills |
| Coding/review in owner app | Owner `.claude/skills/karpathy-guidelines/SKILL.md` |
| Cloud runtime/deployment | Backend `.claude/skills/workers-and-deploy/SKILL.md` and the actual target platform documentation |
| Codex skill/configuration changes | `openai-docs`; use `skill-creator` only when creating or modifying a skill |

Resolve named skills from the session catalog first, then existing repository
`.agents/skills/` or `.claude/skills/` directories. Do not install another copy merely
because a skill is absent from one repository. Report a missing required skill and
use a supported fallback when the task permits it. Missing optional workflow tools
do not justify abandoning authorized work.

For UI verification, exercise real app screens against the intended API, including
loading, empty, error and disabled states. A Jest pass does not establish native
layout correctness. Distinguish actual device interaction, browser automation,
mocked requests and live API/database evidence. Do not claim every screen or flow
passed when it was not exercised.

This routing is an instruction for task-relevant selection in these repositories.
It does not grant production release, migration, deletion or billing authority.
Follow the user's existing authorizations and keep any remaining approval scoped to
the concrete reviewed operation. Never select all skills at startup.
