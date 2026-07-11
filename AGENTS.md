# Agent Instructions

This file provides operating instructions for AI coding agents working in the Traffic Processing Platform repository. 

## 1. Repository Layout (Monorepo Boundaries)
This is a monorepo. Do not run global commands that affect the whole repo unless explicitly intended. Respect component boundaries:
- `traffic-processor/`: Python/FPGA telemetry engine.
- `communication-node/`: Python local forwarding node.
- `cnss/`: Python (FastAPI) backend server.
- `mui/`: TypeScript/React frontend.
- `docs/` & `reports/`: Documentation and course artifacts.

## 2. Core Commands
Always run commands from the specific component directory.
- **CnSS (Backend):** 
  - Install: `pip install -r requirements.txt`
  - Test: `pytest tests/`
  - Coverage: `pytest --cov=app --cov-report=term-missing tests/`
- **MUI (Frontend):**
  - Install: `npm install`
  - Lint/Typecheck: `npm run lint` and `npx tsc --noEmit`
  - Build: `npm run build`
- **Traffic Processor / Comm Node:**
  - Lint: `flake8 .` / `black .`
  - Test: `pytest` (if applicable)

## 3. Strict Git & Workflow Rules
**CRITICAL:** The repository has strict branch protection and history rules.
- **Target Branch:** Always branch from `develop` and open PRs against `develop`.
- **Branch Naming:** `<type>/<issue-number>-<short-desc>` (e.g., `feature/42-add-udp-ingestion`).
- **NO SQUASH / NO REBASE:** Squash and Rebase merges are disabled. You must instruct the user to use a **standard Merge commit**.
- **Commit Format:** Use Conventional Commits (`feat:`, `fix:`, `docs:`, `ci:`, `chore:`).

## 4. Security & Safety Cautions
- **NEVER commit `.env` files**, JWT secrets, API keys, or real IP addresses. 
- Always use `.env.example` as a template. 
- Do not commit large binaries, `.pcap` files, or raw network recordings. Add them to `.gitignore`.
- When writing code, ensure logs sanitize sensitive data (e.g., mask JWT tokens in URL query parameters).

## 5. Changelog & Documentation
- If you make a user-visible change, you MUST add an entry to the root `CHANGELOG.md` under the `## [Unreleased]` section, linking the relevant GitHub issue.
- If you update architecture or workflows, update the corresponding files in `docs/` (e.g., `docs/system-documentation.md`, `docs/development-process.md`).
