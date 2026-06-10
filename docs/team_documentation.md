# Team Documentation

## Repository Structure

This is a monorepo containing four distinct components and supporting infrastructure.

```text
traffic-processing-platform/
├── .github/               # CI/CD workflows, issue templates, PR templates
├── cnss/                  # Control and Status Server (Backend)
├── communication-node/    # Communication Node (Local data forwarding)
├── docs/                  # Architecture diagrams, interview transcripts, reports
├── mui/                   # Management User Interface (Frontend)
├── scripts/               # DevOps, setup, and deployment scripts
├── traffic-processor/     # Traffic Processor (Core packet counting/telemetry)
├── .gitignore             # Global ignore rules
├── LICENSE                # MIT License
└── README.md              # Project overview and quick start guide
```

## Git Workflow (Gitflow)

All development follows the Gitflow branching model.

* **`general`**: Production-ready code. Protected. No direct commits.
* **`develop`**: Integration branch for features. Protected. No direct commits.
* **`feature/<name>`**: Branches from `develop`. Merges back into `develop`.
* **`release/<version>`**: Branches from `develop` when feature-complete. Merges into `general` and `develop`.
* **`hotfix/<name>`**: Branches from `general` for critical production bugs. Merges into `general` and `develop`.

## Team Roles and Task Instructions

### arinamnova (Technical Writer, Translator)

**Responsibilities:** Documentation management, translation, and content coordination.

**Task Instructions:**

1. **Documentation:** Maintain the `docs/` directory. Upload and format the interview transcript, AI usage report, and architecture diagrams.
2. **Repository Docs:** Maintain the root `README.md` and `CONTRIBUTING.md`. Ensure they accurately reflect the current project state and team standards.
3. **Workflow:** Create branches named `docs/<topic>` from `develop`. Open Pull Requests targeting `develop` for all documentation updates.

### jinseisieko (Backend Lead, DevOps Engineer, Project Manager)

**Responsibilities:** CnSS development, Communication Node (CN) development, CI/CD pipeline, repository administration, and project tracking.

**Task Instructions:**

1. **Project Tracking:** Manage the GitHub Project Board. Create issues for all MVP requirements identified in the interview transcript. Move issues through the Kanban columns (`Backlog`, `To Do`, `In Progress`, `In Review`, `Done`).
2. **DevOps:** Manage repository settings, branch protection rules, and GitHub Actions. Maintain the `.github/workflows/` directory. Replace CI stub checks with actual linting and testing commands once the technology stack is finalized.
3. **CnSS Development:** Work inside the `cnss/` directory. Build the server to accept incoming data streams from the CN. Implement in-memory storage for the latest traffic counter values. Expose an API or WebSocket endpoint to serve near real-time data to the MUI.
4. **CN Development:** Work inside the `communication-node/` directory. Establish a local connection with the TP. Receive telemetry streams and forward them to the remote CnSS using HTTP or WebSockets.
5. **Workflow:** Create branches named `feature/cnss-<name>` or `feature/cn-<name>` from `develop`. Review and merge Pull Requests from other team members into `develop`. Create `release/` branches for MVP deployment.

### Rena-ln (Core Systems Engineer, Business Analyst)

**Responsibilities:** Traffic Processor (TP) development, business requirements analysis, and system architecture.

**Task Instructions:**

1. **TP Development:** Work inside the `traffic-processor/` directory. Implement the TP as a transparent inline bridge that passes network packets in both directions.
2. **Telemetry Logic:** Implement basic channel activity checks. Write the logic to count packets and bytes per second.
3. **Data Push:** Configure the TP to push aggregated telemetry data to the Communication Node (CN) at a fixed frequency (e.g., 2, 5, or 10 Hz). Ensure this processing adds no noticeable latency to the network channel.
4. **Workflow:** Create branches named `feature/tp-<name>` from `develop`. Ensure all code passes the `TP Check` CI status before requesting a review.

### Minnezing (Frontend Lead, UI/UX Designer)

**Responsibilities:** Management User Interface (MUI) development and UI/UX design.

**Task Instructions:**

1. **MUI Development:** Work inside the `mui/` directory. Build a web-based interface accessible to authorized users over the internet.
2. **UI Components:** Implement a binary visual cue (Red/Green light) to show channel activity status. Implement two distinct counters or real-time graphs displaying data/packet volume for Direction A and Direction B.
3. **Integration:** Connect the frontend to the CnSS API or WebSocket endpoint. Configure the interface to automatically refresh and update displayed values upon receiving new data.
4. **Workflow:** Create branches named `feature/mui-<name>` from `develop`. Ensure the frontend builds successfully and passes the `MUI Check` CI status before requesting a review.

## Development Guidelines

### Commit Messages

Use Conventional Commits for all commit messages.
Format: `<type>: <description>`

* `feat`: A new feature (e.g., `feat: add packet counter to TP`)
* `fix`: A bug fix (e.g., `fix: resolve websocket timeout in CnSS`)
* `docs`: Documentation only changes (e.g., `docs: update README with MVP goals`)
* `ci`: CI/CD configuration changes (e.g., `ci: add placeholder workflow`)
* `chore`: Maintenance tasks (e.g., `chore: add .gitkeep to empty directories`)

### Pull Requests

1. Ensure your branch is up to date with `develop` before opening a PR.
2. All PRs targeting `develop` or `general` require at least one approving review.
3. All PRs must pass the required CI status checks (`TP Check`, `CN Check`, `CnSS Check`, `MUI Check`) before merging.
4. Use descriptive titles and link the PR to the relevant GitHub Issue.

### Developer Working Script: Standard Operating Procedure

> Follow this sequence for every new task.

#### Task Pickup and Branching

1. **Select a Task**: Go to the GitHub Project Board. Move an issue from `Backlog` or `To Do` to `In Progress`. Assign it to yourself.
2. **Sync Local Repository**: Ensure your local `develop` branch is up to date with the remote repository.

   ```bash
   git checkout develop
   git pull origin develop
   ```

3. **Create Feature Branch**: Create a new branch specifically for this task, branching from `develop`. Use the naming convention `feature/<component>-<description>`.

   ```bash
   # Example for Traffic Processor
   git checkout -b feature/tp-packet-counter
   
   # Example for MUI
   git checkout -b feature/mui-activity-light
   ```

#### Local Development

1. **Navigate to Component Directory**: Work strictly within your assigned directory to maintain monorepo boundaries.

   ```bash
   cd traffic-processor/  # or mui/, cnss/, communication-node/
   ```

2. **Write Code**: Implement the feature according to the issue requirements and integration points defined in the documentation.
3. **Commit Changes**: Use Conventional Commits. Keep commits small and focused on a single logical change.

   ```bash
   git add .
   git commit -m "feat: implement bidirectional byte counter logic"
   ```

   *Allowed types: `feat`, `fix`, `docs`, `ci`, `chore`.*

#### Pre-Push Verification

Before pushing, run local checks to prevent failing the remote CI pipeline.

1. **Format and Lint**: Run the linter/formatter for your specific stack.
   * *Python (TP/CN/CnSS)*: `black .` then `flake8 .`
   * *Node/React (MUI)*: `npm run lint`
2. **Local Build/Test**: Ensure the component compiles or passes basic unit tests.
   * *MUI*: `npm run build`
   * *Python*: `pytest` (if tests exist)
3. **Commit Fixes**: If the linter or build fails, fix the issues and amend or create a new commit.

#### Push and Pull Request

1. **Push Branch**: Push your local feature branch to the remote repository.

   ```bash
   git push -u origin feature/tp-packet-counter
   ```

2. **Open Pull Request**: Go to GitHub and create a new Pull Request.
   * **Base branch**: `develop`
   * **Compare branch**: Your `feature/...` branch.
3. **Fill PR Template**:
   * Title: Use Conventional Commit format (e.g., `feat(tp): add packet counter logic`).
   * Description: Briefly explain what was changed and why.
   * Link the Issue: Add `Closes #<issue-number>` in the description to automatically close the task upon merge.
4. **Update Project Board**: Move the issue to the `In Review` column.

#### Review and Merge

1. **Wait for CI Checks**: Monitor the "Checks" section at the bottom of the PR. The PR cannot be merged until the specific component check passes (e.g., `TP Check`, `MUI Check`).
2. **Request Review**: Assign a reviewer based on component ownership:
   * Rena-ln's TP code -> Reviewed by jinseisieko.
   * Dmitrii's MUI code -> Reviewed by jinseisieko (for API integration) or Rena-ln (for logic alignment).
   * Arina's docs -> Reviewed by jinseisieko or any team member.
3. **Address Feedback**: If the reviewer requests changes, make the updates locally, commit, and push. GitHub will automatically update the PR.
4. **Merge**: Once approved and all CI checks are green, the reviewer (or the author, if permitted) clicks **Squash and Merge**. This keeps the `develop` history clean.
5. **Cleanup**:
   * Delete the remote feature branch (GitHub prompts this after merge).
   * Delete the local branch: `git branch -d feature/tp-packet-counter`
   * Move the issue on the Project Board to `Done`.

#### Integration Validation (Post-Merge)

Because this is a tightly coupled monorepo, after merging a feature into `develop`, verify that it does not break adjacent components:

* If TP telemetry format changed, verify CN can still parse it.
* If CnSS API changed, verify MUI still receives and renders the data correctly.
* If a breaking change is found, immediately create a `fix/<component>-<description>` branch from `develop` and repeat Phases 2-5.
