# Exact known differences

Mumbai `wqjlgpnbiapcrlkxumcp`; head `0037_customer_processing_charge`.
The JSON includes exact names/definitions/raw differences. Structural comparison is
the earlier same-session clean PG18 build against unchanged migration sources;
destination is PG17.11. Latest scoped Mumbai SELECT refreshes ACL/function/trigger/history
metadata. This is not a new clean-head build or proof of effective ACL equality.

| Category | Exact result | Proposal |
| --- | --- | --- |
| Extra columns | public.bookings.cancellation_reason_code; public.bookings.cancellation_reason_text | Retain/adopt, subject to erasure review |
| Extra definitions | Both text, nullable, no default/identity/generated expression | ADD IF NOT EXISTS for future expected-head build; already present in Mumbai |
| Missing columns | None established; all 538 required head columns present | None |
| Changed required columns | None in comparison | None |
| Tables/enums | 44 tables, 9 enums; no missing/extra/changed | None |
| Constraints | No real missing/extra established; catalog differences below | No constraint DDL |
| Indexes | 148; no missing/extra/changed | No index DDL |
| Application functions | 52; no missing/extra; one config mismatch below | Config only; no body changes |
| Triggers | 74 incl signup; no missing/extra/changed in prior comparison | Retain signup; create only if absent and reviewed function matches |
| RLS | All 44 tables enabled; 43 policies; no missing/extra/changed | No policy/RLS changes or client read grants |
| Alembic history | Zero destination rows vs head's single version row | Plan only, no history writes |

Function: `public.is_subscription_promotion_active(public.subscription_status,timestamptz,timestamptz,timestamptz,timestamptz)`.
Head config NULL; Mumbai `{search_path=public}`. Body/result/immutable volatility/
plpgsql/SECURITY INVOKER match after whitespace normalization. 0030 recreates it without
0024's setting. Draft codifies Mumbai's existing hardening without replacing the body.

Constraints: 317 head-only named `*_not_null` entries are PG18 NOT NULL catalog records.
All corresponding column NOT NULL flags match. Exact names remain in the JSON; do not
manufacture these on PG17. One CHECK deparser difference:

- Object: public.subscription_plans.ck_subscription_plans_interval.
- Head: `CHECK (((billing_interval)::text = ANY ((ARRAY['monthly'::character varying, 'quarterly'::character varying, 'semiannual'::character varying, 'yearly'::character varying])::text[])))`
- Mumbai: `CHECK (((billing_interval)::text = ANY (ARRAY[('monthly'::character varying)::text, ('quarterly'::character varying)::text, ('semiannual'::character varying)::text, ('yearly'::character varying)::text])))`

These permit the same four values; no CHECK change proposed.

## Exact grant evidence and limits

The snapshot/JSON contain all 44 table and 52 application-function raw ACLs, owners and
signatures. Current PUBLIC/anon/authenticated app rights are absent. Owner/service-role
grants and defaults remain. Managed extension ACLs are not changed. Both proposed
service-role EXECUTE grants already exist.

backup-client-grant-differences.json records 106 exact backup client GRANT statements
with source lines, all absent in Mumbai. Examples: bookings SELECT, REFERENCES, TRIGGER,
TRUNCATE, MAINTAIN for both clients; get_available_slots EXECUTE for both clients.
None are restored. The matrix separately lists every proposed object/grantee/privilege.

The clean-head comparison excluded ACLs. A schema's effective ACL depends on its creator,
initial defaults/platform roles. Therefore the backup delta is not mislabeled as an
exact effective clean-head ACL diff. repository-acl-source-ledger.json records exact
repository ACL source excerpts/file/line; upgrade/downgrade and dynamic SQL context must
be read in source. Reproducing expected effective head ACLs remains a pre-stamp gate.

Supabase history, separate from Alembic:

| Version | Name |
| --- | --- |
| 20261015100439 | mumbai_roles_compatible_restore_20261015 |
| 20261015100737 | mumbai_schema_only_restricted_restore_20261015 |
| 20261015100828 | mumbai_reviewed_auth_signup_trigger_20261015 |
| 20261015101623 | mumbai_reconcile_0024_function_search_path_20261015 |

These entries do not prove 37 Alembic revisions executed. No missing historical migration
has been established. Base-to-head replay would collide with restored objects and may
reintroduce grants; do not run it.
