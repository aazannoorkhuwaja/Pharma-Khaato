# Pharma-Khaato v2.3.1 — First-Run Setup UI Hotfix

This patch resolves the maximised/light-theme setup-screen issue reported during real-device testing.

## What was wrong

- The first-run wizard had a local stylesheet that captured palette values independently from the live global theme. This could produce a light application with dark/black setup section backgrounds.
- The setup form stretched across very wide windows, increasing eye travel and making the form look unfinished on large displays.
- A single vertical form required unnecessary scrolling and did not use desktop space efficiently.
- Required/optional fields were not visually explicit enough.
- The bottom action area felt detached from the setup flow.

## Fix

- Removed the wizard-specific palette stylesheet; setup now inherits the same live Light/Dark design system as every other screen.
- Replaced group boxes with standard design-system cards.
- Capped the readable form width at 960 logical pixels and centers it when the dialog is maximised.
- Added responsive two-column field layout above 860px and automatic single-column reflow below it.
- Kept the cards scrollable on short screens while the final action stays visible without overlapping form content.
- Improved wording, required/optional indicators, input examples, accessible names, label buddies, focus handling, and validation messages.
- Changed the final action to **Complete setup** and explains the next step (sign in).

## Verification

- 71/71 automated pytest tests pass.
- Added source-level first-run UI regression guards so stale local theme styling, unbounded form width, and lost responsive reflow are caught in CI.
