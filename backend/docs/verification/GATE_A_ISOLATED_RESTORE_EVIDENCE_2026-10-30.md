# Gate A isolated restore evidence — 30 October 2026

**Decision: FAILED / STOPPED.** Gate A is not complete and does not authorize Gate B, any Alembic operation, migration, deployment, traffic change, or automatic deployment.

## Backup

| Field | Evidence |
|---|---|
| Project | `wqjlgpnbiapcrlkxumcp` |
| Backup ID | `reconciliation-20261030T064659956916Z` |
| Snapshot timestamp | `2026-10-30T06:46:59.549166+00:00` |
| Source PostgreSQL | `17.11` (`server_version_num=170011`) |
| Format | PostgreSQL custom archive streamed directly into OpenPGP encryption |
| Ciphertext bytes | 197643 |
| Ciphertext SHA-256 | `5f9595dc1ed39a893d2ff7d5b88ab30a18ddedcaa2fc6498dec66bc540815866` |
| Plaintext archive SHA-256 | `925e8b88a94366a76139595c9cd05cb0dda3163f6c7e629ede5cbab3bc4cad0e` |
| Decrypt/hash verification | PASS |
| Table-data entries | 84 |
| Plaintext backup written | No |
| Production writes | No; repeatable-read, read-only snapshot |

This was a logical database backup of objects and data visible to the configured production role, with password-free role and ACL metadata. It did not include Storage/R2 object bytes, cloud configuration, runtime credentials, or PostgreSQL role passwords. The encrypted local backup and its local metadata were deleted after recording this evidence, as required by the owner.

## Isolated restore

The verified target was `salon-gate-a-primary-20261030-064659:5432/restore_baseline` inside disposable Docker infrastructure. It had no published ports or host mounts. During restore it used `--network=none`; for the harness it was connected only to a temporary Docker `--internal` network shared with the harness container.

| Check | Result |
|---|---|
| Restore completed | PASS |
| Restore duration | 16.225 seconds |
| Table fingerprints | PASS — 84 verified, 0 mismatches |
| Financial totals | PASS |
| Original owners and effective ACLs | PASS — 0 differences |
| Background cron | Disabled |
| Migrations applied | None |

An initial disposable attempt restored the archive but its verifier queried a renamed local database that did not exist. Its isolation was verified (`network=none`, zero ports, zero mounts), and the container was deleted. The corrected fresh restore above used the verifier's expected database name and passed.

## Harness results

| Phase/check | Result |
|---|---|
| Safety `_validate_not_production()` | PASS |
| Project confirmation | PASS |
| `preflight` | PASS |
| `empty_alembic_version` | PASS — zero rows |
| `baseline_0040_tables` | PASS |
| `fastapi_only_acl` | PASS |
| `0049-equivalence` | **FAIL** |
| `0049_table_structure` | PASS, including the existing `valid_until` column |
| `0049_primary_key` | PASS — `(salon_id, plan_id)` |
| `0049_subscription_plan_prices` | **FAIL** |
| `schema-check` | NOT RUN — required stop after failed harness check |
| Rollback/second-restore rehearsal | NOT RUN — required stop after failed harness check |

The failing values were:

| Plan | Harness expected | Restored value |
|---|---:|---:|
| `growth_6m` | 1675.00 | 2000.00 |
| `growth_12m` | 2932.00 | 2999.00 |
| `premium_6m` | 2875.00 | 2875.00 |
| `premium_12m` | 5032.00 | 5032.00 |

Raw harness evidence:

- `RECONCILIATION_EVIDENCE_PREFLIGHT_20261030_065011.json` — captured harness SHA-256 `ef2496be61e2a79e5a0869657236b4c72e8c991284adec05d84cb943f7e3f2c4`; repository evidence JSON SHA-256 `3947229818ada74b6948d0d43cd681c560436326acf21e62c563462ae77fb2d2`
- `RECONCILIATION_EVIDENCE_0049-EQUIVALENCE_20261030_065019.json` — captured harness SHA-256 `0b040601ef2cedcf9ae8bbeb5c7169b80ad4b5148cb4e4cdc4935cb38ab46084`; repository evidence JSON SHA-256 `e9cab995580c400198fb92fc8d2b573940c9066821e90ba1841fcda883d75989`

## Stop condition and cleanup

The failed price-equivalence check triggered the owner's stop rule. No subsequent harness phase or rollback rehearsal was attempted. Both disposable containers, the private Docker network, the encrypted backup, local recovery metadata, and control receipts were deleted after evidence capture.

No production schema or data was modified. No Alembic stamp, migration, Cloud Run deployment, traffic change, GitHub/GCP configuration change, commit, or push occurred.
