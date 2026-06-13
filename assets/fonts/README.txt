Current font assets:
- `msyh.ttc`: temporary development fallback copied from the local Windows system.

Before publishing outside the current machine, replace this with a redistributable font,
for example an open-source Chinese font placed under `assets/fonts/`, such as:
- `NotoSansSC-Regular.otf`
- `NotoSansCJKsc-Regular.otf`
- `SourceHanSansSC-Regular.otf`

The app will prefer those bundled open-source fonts first.
