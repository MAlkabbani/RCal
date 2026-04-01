# Open-Source Release Checklist

This checklist is tailored to the current RCal repository state.

## 1. Project framing

- [ ] README states RCal is a planning calculator, not a filing engine
- [ ] README clearly defines target users and out-of-scope users
- [ ] README limitations match current implementation in `main.py`
- [ ] README setup paths (`./rcal` and manual setup) are runnable

## 2. Governance assets

- [ ] `LICENSE` exists and matches README
- [ ] `CONTRIBUTING.md` exists
- [ ] `CODE_OF_CONDUCT.md` exists
- [ ] `SECURITY.md` exists

## 3. Community workflows

- [ ] Issue templates exist for bug and feature requests
- [ ] Pull request template exists
- [ ] Maintainers review template language for tone and scope fit

## 4. Quality and verification

- [ ] `bash qa.sh` passes in a clean `.venv`
- [ ] Test count and coverage claims in docs match actual output
- [ ] Benchmark command runs without errors
- [ ] State persistence and clear-memory flow are tested

## 5. Documentation parity

- [ ] Tax constants in docs match constants in `main.py`
- [ ] Threshold values in docs match computed values in code
- [ ] CLI screenshots/text examples reflect current prompts and menu
- [ ] Changelog entries match merged behavior

## 6. Release operations

- [ ] Tag/version strategy is defined
- [ ] GitHub release notes summarize scope assumptions and limitations
- [ ] A post-release verification run of `bash qa.sh` is recorded

## 7. Optional hardening

- [ ] Add CI workflow for lint, type check, tests, and coverage gate
- [ ] Add pinned development dependency file
- [ ] Add architecture notes for future contributors
