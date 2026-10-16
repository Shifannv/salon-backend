# Local Mumbai database health recovery — 2026-10-16

The approved local fix is applied. Three consecutive requests to
`http://127.0.0.1:8000/health/db` returned HTTP 200 with
`{"status":"ok","database":"reachable"}`. No migration or stamp ran.

## Diagnosis and evidence limits

The original timing reports acquisition failure before SQL, not a database outage.
The old Docker API's startup exception was exactly
`socket.gaierror: [Errno -2] Name or service not known`. DNS resolution of the direct
Mumbai hostname failed again inside that container. The original request ID
`6182823cdafd4188b432519ad4e13821` appeared in request logging, but its caught exception
was not logged with a stack trace. Therefore that historical request's exact underlying
exception cannot be established from the retained logs; the matching startup failure
and reproduced DNS failure are supporting evidence, not a request-linked traceback.

A second, older Windows Uvicorn reload server also held IPv4 port 8000. After Docker
recovery, IPv6/localhost and container-direct checks passed while IPv4 still returned
503. Its reload parent, launcher and orphan multiprocessing child were identified as
this repository's backend and stopped. Both problems had to be resolved to fix the
user-facing IPv4 address. No unverified host-process exception is attributed to it.

## Effective target and configuration

Only Mumbai project `wqjlgpnbiapcrlkxumcp` was tested. Before: direct host
`db.wqjlgpnbiapcrlkxumcp.supabase.co`, port 5432, user `postgres`. After:
`aws-0-ap-south-1.pooler.supabase.com`, port **5432**, scoped user
`postgres.wqjlgpnbiapcrlkxumcp`, database `postgres`, driver `postgresql+asyncpg`.
No full connection URL is recorded.

The hidden password was retained from `backend/.env`'s `DATABASE_URL`; no password
reset occurred. The Docker API receives it through Compose `env_file`; the host shell
had no `DATABASE_URL` override. Compose's explicit runtime values do not override that
variable. Process environment takes precedence over application dotenv loading; no
image-local dotenv file supplied a competing value. The old Docker target and rendered
Compose target agreed. The stale Windows process had already loaded its settings.

Pool settings remain size 5, overflow 5, acquisition timeout 10 seconds, connection
timeout 10 seconds, recycle 1800 seconds. The isolated candidate pool released all
connections (checked out 0). This does not establish historical Windows pool occupancy.

Before changing files, the candidate passed IPv4 DNS, TCP, hidden-password authentication,
TLS 1.3 with hostname/certificate verification, SELECT 1, a read-only transaction,
SQLAlchemy pool release and the actual health route in an isolated process. The approved
ignored override `.artifacts/local-db-fix/compose.override.yml` mounts the public CA at
`/run/salon/mumbai-supabase-ca.pem` read-only and sets `DB_SSL_CA_FILE` and
`DB_SSL_STRICT=true`. Verification was not disabled.

## Applied local changes and commands

The user explicitly approved the environment-file change and API-only recreation.
Only `DATABASE_URL` in ignored `backend/.env` changed; other parsed dotenv values were
compared and remained equal. The update used `dotenv.set_key` with the original parsed
SQLAlchemy URL's password retained and only host/user/port/driver replaced. Its return
value and the URL were never printed.

Docker's original API image was no longer present, although its container still ran.
The first recreation attempt failed with `No such image`; it did not update the API.
Rather than build new application code, the running container was preserved as the
local-only image `salon-local-db-recovery:preserved-api`, then recreated from that image.
The digest necessarily changed. This is a preserved runtime snapshot, not a byte-identical
original image. It contains private local container configuration and must not be pushed.

Commands below ran from the repository root; the recreation subprocess also set
`SALON_API_IMAGE=salon-local-db-recovery:preserved-api`, `COMPOSE_ENV_FILE=.env`, and
`ENVIRONMENT=local`:

```powershell
docker --context desktop-linux commit backend-api-1 salon-local-db-recovery:preserved-api
docker --context desktop-linux compose --project-name backend --env-file backend/.env -f backend/docker-compose.yml -f backend/.artifacts/local-db-fix/compose.override.yml up -d --no-deps --no-build --pull never --force-recreate api
Get-NetTCPConnection -LocalPort 8000 -State Listen
```

Read-only diagnostics used `docker inspect`, sanitized `docker logs`, Python
`socket.getaddrinfo`, TCP connect, verified SSL contexts, asyncpg/SQLAlchemy queries,
and urllib GET requests. Only verified duplicate local Uvicorn process IDs
27392, 18948 and its child 35120 were stopped; workers and Redis were not recreated.

Final request IDs and server timing (milliseconds):

| Request ID | HTTP | App | DB acquire | SQL | Queries |
| --- | ---: | ---: | ---: | ---: | ---: |
| local-mumbai-final-1 | 200 | 152.70 | 98.08 | 52.91 | 1 |
| local-mumbai-final-2 | 200 | 151.34 | 101.47 | 49.07 | 1 |
| local-mumbai-final-3 | 200 | 186.41 | 134.97 | 50.78 | 1 |

These three checks are functional evidence, not latency percentiles or deployed Mumbai
FastAPI measurements. See the separate CI verification report for the 30-sample series.

## Rollback and remaining limits

No remaining blocker for local `/health/db`. Keep the ignored CA artifact while this
override is in use. Subsequent local recreations must include this override; otherwise
the CA mount is lost. No shared Compose defaults or worker environments were changed.
The previously unhealthy account-deletion worker is outside this API-only fix.

To undo this local configuration, stop only this local API and review the preserved
snapshot and prior target before restoring the old `DATABASE_URL` host/user. Restoring
the direct hostname can restore the reproduced DNS failure; it is not a healthy rollback.
Do not restart the duplicate host Uvicorn listener on port 8000 alongside Docker.
No production/Sydney/Cloud Run changes, shared migrations, password changes or Git commits.
