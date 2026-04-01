# Repository Housekeeping Plan

This plan lists candidates to move out of the public repository surface into a local archive folder such as `local_archive/`.

## Keep in repository

- `README.md`
- `PRD.md`
- `CHANGELOG.md`
- `LICENSE`
- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `SECURITY.md`
- `main.py`
- `test_main.py`
- `qa.sh`
- `requirements.txt`
- `requirements-dev.txt`
- `pyproject.toml`
- `.github/` templates and CI workflow
- `docs/AI_REFERENCE_DOC.md`
- `docs/OSS_RELEASE_CHECKLIST.md`

## Archive candidates (recommended)

- `docs/initial-prompt.md`
  - Internal prompt history, not needed for external users or contributors.
- `docs/walkthrough.md`
  - Development chronology is useful internally but can distract from core user docs.
- `docs/COMPLIANCE_AUDIT.md`
  - Internal audit artifact; consider summarizing key boundaries in README/PRD and archiving full note.
- `.vscode/launch.json`
  - Editor-specific convenience profile, optional for public repository.
- `.vscode/settings.json`
  - Editor-specific autosave preferences, optional for public repository.
- `backup_workspace.py`
  - Local workflow utility; optional for public consumers if backups are not part of project contract.

## Optional consolidation before archiving

1. Move essential compliance boundaries from `docs/COMPLIANCE_AUDIT.md` into:
   - `README.md` limitations section
   - `PRD.md` assumptions and scope section
2. Keep one concise developer doc map in README.
3. Move historical/development narrative docs to `local_archive/docs/`.

## Local archive conventions

- Use `local_archive/` as the local-only storage path.
- `local_archive/` is ignored by `.gitignore`.
- Keep date-stamped folders if needed for traceability, for example:
  - `local_archive/2026-04-cleanup/docs/`

## Suggested cleanup sequence

1. Move candidate files to `local_archive/`.
2. Run `bash qa.sh` to confirm no references break.
3. Update README docs map if any files moved.
4. Commit cleanup as a standalone change for clear project history.
