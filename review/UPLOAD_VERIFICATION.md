# Upload-folder verification

This clean submission copy was prepared from step6 fix567 improved. It includes
source, dependencies, tests, documentation, current numerical evidence and figures.
Archived robustness/old-guard studies, earlier project versions, ZIP archives,
virtual environments, Python/pytest caches and .DS_Store files were excluded.
Historical review documents may refer to development archives not included here.

Verification executed from this folder:

```bash
python -m pytest -q -p no:cacheprovider
```

**206 passed in 218.86 seconds.** The 24,072 warnings are existing PuLP
deprecations. Tests include output regeneration into a temporary empty directory.
This used the existing locked environment, not a new dependency installation.

All top-level Python source files match the previously verified improved version.
Checked for expected current evidence, saved configuration manifests, caches,
personal absolute paths and common private-key/token patterns. No matches for
those unwanted artifacts/patterns were found; this is not an exhaustive security
guarantee. The .gitignore includes local secrets and permits tracking results/.

Upload this directory's contents into the GitHub repository root. Include the
hidden .gitignore file. Then test a fresh clone of the actual published repository
using review/STEP1_VERIFICATION.md. Creating this folder does not itself publish
or submit the project.
