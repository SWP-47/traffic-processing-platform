# Contributing to the Traffic Processing Platform

Thank you for your interest in contributing to the Traffic Processing Platform! This document outlines the workflow and expectations for human contributors. For AI coding agents, please refer to [`AGENTS.md`](./AGENTS.md).

## 1. Development Setup
Before contributing, ensure you have followed the local setup instructions in the root [`README.md`](./README.md). 
- The project is a **monorepo**. Always work strictly within your assigned component directory (`traffic-processor/`, `communication-node/`, `cnss/`, or `mui/`).
- Ensure all environment variables are configured using `.env.example` templates. **Never commit actual `.env` files.**

## 2. Git Workflow & Branching
We follow an adapted Gitflow model. **Strict adherence to the following rules is required:**
1. **Base Branch:** All feature branches must be created from `develop`.
2. **Branch Naming:** Use the format `<prefix>/<issue-number>-<short-description>`.
   - Examples: `feature/42-tp-packet-counter`, `docs/15-update-readme`, `fix/88-websocket-timeout`.
3. **Commit Messages:** Use [Conventional Commits](https://www.conventionalcommits.org/) (e.g., `feat:`, `fix:`, `docs:`, `ci:`, `chore:`).
4. **NO SQUASH OR REBASE:** Squash and Rebase merging are explicitly disabled to preserve history. **You must use standard Merge commits.**

## 3. Local Verification Before Pushing
Before opening a Pull Request, you must verify your changes locally:
- **Python (TP / CN / CnSS):** Run `black .` and `flake8 .` (or equivalent project linters), and ensure `pytest` passes.
- **Node/React (MUI):** Run `npm run lint` and ensure `tsc --noEmit` passes without type errors.
- **Links:** Ensure no broken internal links are introduced (Lychee CI will check this).

## 4. Pull Request Process
1. Push your branch and open a PR targeting the `develop` branch.
2. Fill out the PR template completely:
   - Link the issue using `Closes #<issue-number>`.
   - Document the testing you performed.
   - Check the Changelog box: Either add a user-visible entry to `CHANGELOG.md` under `[Unreleased]` or mark it as an internal change.
3. **Review:** A PR requires at least one approving review from a teammate. Authors cannot approve their own PRs.
4. **CI Gates:** All GitHub Actions checks (including Lychee link checking, pytest, and type checks) must pass before merging.

## 5. Further Reading
- [Team Documentation & Standard Operating Procedure](./docs/team_documentation.md)
- [Definition of Done](./docs/definition-of-done.md)
- [System Architecture](./docs/system-documentation.md)
