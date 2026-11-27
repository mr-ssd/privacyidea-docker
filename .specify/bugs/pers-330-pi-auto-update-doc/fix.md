# Bug fix record — pers-330-pi-auto-update-doc (PERS-330)

Prompt: "Update README.md:114. Replace the old phrase `will update privacyIDEA to the latest version`. Write exactly this BUG-2 sentence: PI_AUTO_UPDATE set to **true** will run the privacyIDEA schema upgrade. Preserve exactly this BUG-3 sentence: Make sure you have backup your data before setting `PI_AUTO_UPDATE` to **true**. Do not change code."

## Change

`README.md` line 114, old:

> `PI_AUTO_UPDATE` set to **true** will update privacyIDEA to the latest version. Make sure you have backup your data before setting `PI_AUTO_UPDATE` to **true**.

new:

> PI_AUTO_UPDATE set to **true** will run the privacyIDEA schema upgrade. Make sure you have backup your data before setting `PI_AUTO_UPDATE` to **true**.

- BUG-2 sentence written exactly: `PI_AUTO_UPDATE set to **true** will run the privacyIDEA schema upgrade.`
- BUG-3 sentence preserved exactly: `` Make sure you have backup your data before setting `PI_AUTO_UPDATE` to **true**. ``
- Old phrase `will update privacyIDEA to the latest version` removed from the file.
- Docs-only: `git diff` touches `README.md` and this case's report/manifest paths only; no code change.
