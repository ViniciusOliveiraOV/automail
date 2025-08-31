# Changelog

All notable changes to this project are documented in this file.

## Unreleased
- Remove temporary debug endpoint `/_debug_llm_config` for production readiness.
- Preserve classifier HTML classes when sanitizing to allow CSS feedback (green/red) to apply.
- Fix heading and score colors; include explicit `.score-good` / `.score-bad` CSS rules.
- Make `/classify` GET render the index form and stabilize route registration.
- Add local Tailwind build files and integrate `npm run build:css`.
- Add Cypress E2E spec improvements and CI wiring for unit and e2e tests.
- Minor tests added and adjusted (`test_score_html_safety`, `test_llm_endpoint`, etc.).

