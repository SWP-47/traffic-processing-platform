# Team Documentation

## Repository Structure

This is a monorepo containing four distinct components and supporting infrastructure.

```text
traffic-processing-platform/
├── .github/               # CI/CD workflows, issue templates, PR templates
├── cnss/                  # Control and Status Server (Backend)
├── communication-node/    # Communication Node (Local data forwarding)
├── docs/                  # Architecture diagrams, sanitized reports, setup instructions
├── reports/               # All reports
├── mui/                   # Management User Interface (Frontend)
├── scripts/               # DevOps, setup, and deployment scripts
├── traffic-processor/     # Traffic Processor (Core packet counting/telemetry)
├── .gitignore             # Global ignore rules (includes .env, *.pcap, *.mp4, etc.)
├── LICENSE                # MIT License
├── CHANGELOG.md           # Project changelog following Keep a Changelog format
├── ATTRIBUTION.md         # Third-party/customer asset attribution (if applicable)
└── README.md              # Project overview, local setup, and deployment links
```

## Git Workflow (Gitflow)

All development follows the Gitflow branching model, adapted to meet course requirements.

* **`general`**: Production-ready code. Protected. No direct commits.
* **`develop`**: Integration branch for features. Protected. No direct commits.
* **`feature/<issue-number>-<short-description>`**: Branches from `develop`. Merges back into `develop`.
  * *Examples:* `feature/42-tp-packet-counter`, `docs/15-update-readme`, `feature/8-websocket-timeout`
* **`release/<version>`**: Branches from `develop` when feature-complete. Merges into `general` and `develop`.
* **`hotfix/<issue-number>-<short-description>`**: Branches from `general` for critical production bugs. Merges into `general` and `develop`.

> **⚠️ CRITICAL COURSE REQUIREMENT:** Squash and Rebase merging are **disabled** in repository settings. All merges must use **Merge commits** to preserve history.

## Team Roles and Task Instructions

### @arinamnova (Technical Writer, Translator)

**Responsibilities:** Documentation management, translation, and content coordination.

**Task Instructions:**

1. **Documentation:** Maintain the `docs/` and `reports/` directory. Ensure all transcripts and reports are **sanitized** (no real names, no private recording links).
2. **Repository Docs:** Maintain the root `README.md`, `CHANGELOG.md`, and `CONTRIBUTING.md`. Ensure they accurately reflect the current project state.
3. **Workflow:** Create branches named `docs/<issue-number>-<topic>` from `develop`. Open Pull Requests targeting `develop` for all documentation updates.

### @jinseisieko (Backend Lead, DevOps Engineer, Project Manager)

**Responsibilities:** CnSS development, Communication Node (CN) development, CI/CD pipeline, repository administration, and project tracking.

**Task Instructions:**

1. **Project Tracking:** Manage the GitHub Project Board. Create issues for all requirements. Move issues through Kanban columns (`Backlog`, `To Do`, `In Progress`, `In Review`, `Done`).
2. **DevOps:** Manage repository settings, branch protection rules, and GitHub Actions (including Lychee link checking). Maintain the `.github/workflows/` directory.
3. **CnSS Development:** Work inside the `cnss/` directory. Build the server to accept incoming data streams from the CN. Implement in-memory storage for traffic counters. Expose an API/WebSocket endpoint for the MUI.
4. **CN Development:** Work inside the `communication-node/` directory. Establish local connection with the TP, receive telemetry, and forward to remote CnSS.
5. **Workflow:** Create branches named `feature/<issue-number>-<name>` from `develop`. Review and merge PRs. Create `release/` branches for MVP deployment.

### @Rena-ln (Core Systems Engineer, Business Analyst)

**Responsibilities:** Traffic Processor (TP) development, business requirements analysis, and system architecture.

**Task Instructions:**

1. **TP Development:** Work inside the `traffic-processor/` directory. Implement the TP as a transparent inline bridge.
2. **Telemetry Logic:** Implement basic channel activity checks and logic to count packets/bytes per second.
3. **Data Push:** Configure the TP to push aggregated telemetry to the CN at a fixed frequency (e.g., 2, 5, or 10 Hz) without adding noticeable latency.
4. **Workflow:** Create branches named `feature/<issue-number>-<name>` from `develop`. Ensure all code passes CI checks before requesting a review.

### @Minnezing (Frontend Lead, UI/UX Designer)

**Responsibilities:** Management User Interface (MUI) development and UI/UX design.

**Task Instructions:**

1. **MUI Development:** Work inside the `mui/` directory. Build a web-based interface accessible to authorized users.
2. **UI Components:** Implement a binary visual cue (Red/Green light) for channel activity. Implement two distinct counters/graphs for Direction A and Direction B packet volume.
3. **Integration:** Connect the frontend to the CnSS API/WebSocket. Configure auto-refresh upon receiving new data.
4. **Workflow:** Create branches named `feature/<issue-number>-<name>` from `develop`. Ensure the frontend builds successfully and passes CI before requesting a review.

## Development Guidelines

### Commit Messages

Use Conventional Commits for all commit messages.
Format: `<type>: <description>`

* `feat`: A new feature (e.g., `feat: add bidirectional byte counter to TP`)
* `fix`: A bug fix (e.g., `fix: resolve websocket timeout in CnSS`)
* `docs`: Documentation only changes (e.g., `docs: update README with MVP goals`)
* `ci`: CI/CD configuration changes (e.g., `ci: configure lychee link checker`)
* `chore`: Maintenance tasks (e.g., `chore: update .gitignore for .env files`)

### Pull Requests

1. Ensure your branch is up to date with `develop` before opening a PR.
2. All PRs targeting `develop` or `general` require **at least one approving review** from another team member. Authors cannot approve their own PRs.
3. All PRs must pass required CI status checks (including **Lychee Link Check**) before merging.
4. Use descriptive titles and link the PR to the relevant GitHub Issue using `Closes #<issue-number>`.

### Developer Working Script: Standard Operating Procedure

> Follow this sequence for every new task.

#### 1. Task Pickup and Branching

1. **Select a Task:** Go to the GitHub Project Board. Move an issue from `Backlog` or `To Do` to `In Progress`. Assign it to yourself.
2. **Sync Local Repository:** Ensure your local `develop` branch is up to date.

   ```bash
   git checkout develop
   git pull origin develop
   ```

3. **Create Feature Branch:** Create a new branch from `develop`. **The branch name MUST start with the issue number**, followed by the prefix and description.

   ```bash
   # Example for Traffic Processor (Issue #42)
   git checkout -b feature/42-tp-packet-counter
   
   # Example for Documentation (Issue #15)
   git checkout -b docs/15-update-readme
   ```

#### 2. Local Development

1. **Navigate to Component Directory:** Work strictly within your assigned directory to maintain monorepo boundaries.

   ```bash
   cd traffic-processor/  # or mui/, cnss/, communication-node/
   ```

2. **Write Code:** Implement the feature according to the issue requirements.
3. **Commit Changes:** Use Conventional Commits. Keep commits small and focused.

   ```bash
   git add .
   git commit -m "feat: implement bidirectional byte counter logic"
   ```

   *Allowed types: `feat`, `fix`, `docs`, `ci`, `chore`. `refactor`*

#### 3. Pre-Push Verification & Sanitization Check

Before pushing, run local checks and verify no sensitive data is included:

1. **Format and Lint:**
   * *Python (TP/CN/CnSS)*: `black .` then `flake8 .`
   * *Node/React (MUI)*: `npm run lint`
2. **Sanitization Check:** Ensure NO `.env` files, NO real names (use roles/usernames), and NO private recording links are being committed.
3. **Local Build/Test:** Ensure the component compiles (`npm run build` or `pytest`).

#### 4. Push and Pull Request

1. **Push Branch:** Push your local feature branch to the remote repository.

   ```bash
   git push -u origin feature/42-tp-packet-counter
   ```

2. **Open Pull Request:** Go to GitHub and create a new PR.
   * **Base branch:** `develop`
   * **Compare branch:** Your `feature/<issue-number>-...` branch.
3. **Fill PR Template:**
   * Title: Use Conventional Commit format.
   * Description: Briefly explain changes, link issue (`Closes #42`).
   * **Changelog:** Check exactly one box: either "Added/updated user-visible entry in CHANGELOG.md" OR "Not applicable (internal change)".
   * **Testing:** Document automated/manual testing performed.
4. **Update Project Board:** Move the issue to the `In Review` column.

#### 5. Review and Merge

1. **Wait for CI Checks:** Monitor the "Checks" section. The PR cannot be merged until all checks (including Lychee) are green.
2. **Request Review:** Assign a reviewer based on component ownership:
   * @Rena-ln's TP code -> Reviewed by @jinseisieko.
   * @Minnezing's MUI code -> Reviewed by @jinseisieko (API) or @Rena-ln (logic).
   * @arinamnova's docs -> Reviewed by @jinseisieko or any team member.
3. **Address Feedback:** If changes are requested, update locally, commit, and push.
4. **Merge:** Once approved and CI is green, the reviewer clicks **Merge pull request** (Create a merge commit).
   > ⚠️ **DO NOT use Squash and Merge or Rebase and Merge.** Course requirements strictly mandate using Merge commits to preserve history.
5. **Cleanup:**
   * Delete the remote feature branch (GitHub prompts this after merge).
   * Delete the local branch: `git branch -d feature/42-tp-packet-counter`
   * Move the issue on the Project Board to `Done`.

#### 6. Integration Validation (Post-Merge)

Because this is a tightly coupled monorepo, after merging into `develop`, verify adjacent components:

* If TP telemetry format changed, verify CN can still parse it.
* If CnSS API changed, verify MUI still receives and renders data correctly.
* If a breaking change is found, immediately create a `fix/<issue-number>-<description>` branch from `develop` and repeat Phases 2-5.
