# Payout account number encryption

Prepared only. Nothing here has been applied to Mumbai, staging or production.

## What changes

The owner's bank account number is encrypted by the API before it is written, using a key that
lives in the environment and not in the database. A copy of the database alone no longer shows
account numbers.

Visibility is unchanged:

| Who | Sees |
| --- | --- |
| Owner | UPI ID, IFSC, bank name, holder name, account number as last four digits |
| Super admin, paying a request | The full account number (decrypted for that one reveal, which is audited) |
| Anyone else | Nothing; the table has no browser-facing grants |

UPI ID, IFSC and bank name are stored as before; they are not enough to move money.

## How it works

* New column `bank_account_last4`, written by the API with every number. Masking, the history
  trigger and the owner and admin screens use it, so none of them ever decrypt.
* `bank_account_number` holds `enc:v1:<token>`. The token also carries the salon id, so a
  ciphertext copied onto another row will not open.
* Rows written before this change stay plain digits and keep working until converted.
* Without `PAYOUT_ENCRYPTION_KEY` the API writes plain digits, exactly as before.

## Deploy order (each step is safe on its own)

1. Apply migration `0059_payout_account_encryption`. Additive; plaintext rows remain valid.
2. Deploy this API version. Still writing plain text because no key is set yet.
3. Generate a key and store it in the secret manager:
   `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
   Keep a copy somewhere separate from the database backups. Losing it loses the numbers.
4. Set `PAYOUT_ENCRYPTION_KEY` on the API and redeploy. New and edited numbers are encrypted.
5. Convert existing rows, as the database owner:
   * `python scripts/encrypt_payout_accounts.py` (dry run, prints how many rows)
   * `python scripts/encrypt_payout_accounts.py --apply`
   The script changes only the number columns, does not touch `updated_at` or history, proves
   each round trip before writing, and runs in one transaction.
6. Check one pending payout in the admin screen: the full number still appears, and the owner
   still sees the last four digits.

## Key rotation

Set `PAYOUT_ENCRYPTION_KEY="<new>,<old>"`. The first key encrypts, every key decrypts. Re-run
step 5 with `--decrypt` then without it to re-encrypt everything under the new key, then drop
the old key.

## Rollback

Set the key back to empty only after running `scripts/encrypt_payout_accounts.py --decrypt
--apply`; the 0059 downgrade refuses to run while any encrypted number exists.

## Tested against

Disposable local PostgreSQL 18: migration apply, owner write, masked read, history, admin
reveal, legacy rows, clearing, constraint rejection, backfill both ways
(`tests/integration/test_payout_encryption_sql.py`), and `tests/unit/test_field_crypto.py`.
