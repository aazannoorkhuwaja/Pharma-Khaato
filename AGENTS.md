# AGENTS.md

## Agent skills

### Issue tracker

GitHub Issues (uses `gh` CLI against `aazannoorkhuwaja/Pharma-Khaato`). See `docs/agents/issue-tracker.md`.

### Triage labels

Canonical 5-role triage label vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout (`CONTEXT.md` + `docs/adr/` at repo root). See `docs/agents/domain.md`.

## Execution Rules

- **Auto-continue across phases**: After confirming or completing Phase 1 of any engineering skill or workflow (e.g. `/diagnosing-bugs`, `/implement`, `/wayfinder`), automatically proceed through all subsequent phases continuously.

