# Bug assessment — pers-330-pi-auto-update-doc (PERS-330)

Prompt: "PERS-330 PI_AUTO_UPDATE README wording: the note says will update privacyIDEA to the latest version. Source rootfs/usr/local/bin/configure_privacyidea.sh runs privacyidea-schema-upgrade. Correct README.md:114 to say the schema upgrade runs and retain its backup advice. Docs-only; no code change."

## Reported behavior

`README.md:114` (base `f3c01c28cefd6f3df6ea2fe95c4653088ee4024e`) states:

> `PI_AUTO_UPDATE` set to **true** will update privacyIDEA to the latest version.

## Cause

The implementation does not update privacyIDEA to a newer version. `rootfs/usr/local/bin/configure_privacyidea.sh:297-303` runs, when `PI_AUTO_UPDATE` is true:

```sh
if ! privacyidea-schema-upgrade -d /opt/privacyidea/lib/privacyidea/migrations; then
```

i.e. it runs the **privacyIDEA schema upgrade** against the existing installation's database migrations — it does not change the installed package version. The README note misdescribes the action as a version update ("latest version").

## Reproduction / evidence

- `git show f3c01c28:README.md | sed -n '114p'` → old wording present (BUG-1 baseline probe).
- `git show f3c01c28:rootfs/usr/local/bin/configure_privacyidea.sh | grep -n privacyidea-schema-upgrade` → line 299 (BUG-4).
- `Dockerfile:51-55` → image default `PI_AUTO_UPDATE=false`.

## Scope of fix

Docs-only correction of `README.md:114`: state that the schema upgrade runs; retain the backup advice sentence byte-identical. No code change.
