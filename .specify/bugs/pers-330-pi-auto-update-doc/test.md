# Bug test record — pers-330-pi-auto-update-doc (PERS-330)

Verification against the original reported behavior, via the fixed dispatcher (`check-case.py`) and the plan §6 executable checks:

- BUG-1 (baseline probe): `git show <base>:README.md | grep -F 'will update privacyIDEA to the latest version'` → present at base. PASS.
- BUG-2 (corrected note): head `README.md` contains exactly `PI_AUTO_UPDATE set to **true** will run the privacyIDEA schema upgrade.` and no longer contains `will update privacyIDEA to the latest version`. PASS.
- BUG-3 (backup advice retained): head `README.md` contains exactly `` Make sure you have backup your data before setting `PI_AUTO_UPDATE` to **true**. `` PASS.
- BUG-4 (implementation source): head `rootfs/usr/local/bin/configure_privacyidea.sh` contains `privacyidea-schema-upgrade`. PASS.
- Docs-only diff: `git diff --no-renames --name-only <base>...HEAD` = `README.md`, `.specify/bugs/pers-330-pi-auto-update-doc/{assessment,fix,test}.md`, `.specify/traceability/cases/pers-330-pi-auto-update-doc.yml` — all inside `allowed_paths`. PASS.
