# Problem statement — pers-375-silent-key-regeneration

GitHub issue #2 reports that losing `/data/privacyidea/keys` makes bootstrap generate fresh encryption and audit keys, so existing tokens cannot be decrypted and old audit signatures stop verifying. At the base SHA the encryption half is already guarded: with a non-SQLite database, no marker and no `PI_ENCFILE`, bootstrap probes the database and exits 1 when privacyIDEA tables exist (`rootfs/usr/local/bin/configure_privacyidea.sh:225-246`, added by `bf2c26e`).

The remaining problem is narrower but the same class of harm. Audit keys are regenerated whenever `private.pem` is missing, with no database check (`:264-271`); when the marker survives but a separately mounted key path does not, bootstrap is skipped and the refusal is never reached (`:218-221`); and the database probe swallows every error, so "cannot determine" is treated as "no data" (`:230-240`). `README.md:113` already promises that startup refuses to generate new key files when data exists, so the code is behind its own documented contract.

Scope of the problem: non-SQLite deployments, because the guard excludes SQLite by design (the SQLite database and its keys share `PI_DATA_DIR`, so losing one loses both). The goal is an actionable, fail-closed refusal with a correct recovery message, not silent key replacement.
