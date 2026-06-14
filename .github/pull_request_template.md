# Pull Request

**Related Issue:** Closes #`<issue-number>`
*(Replace `<issue-number>` with the actual issue number this PR resolves)*

## Summary of Changes
<!-- Briefly explain what was changed and why. Mention the specific monorepo component(s) affected (e.g., mui/, cnss/, traffic-processor/). -->

## Acceptance Criteria Verification
<!-- Verify that the acceptance/completion criteria from the linked issue have been met. -->
- [ ] All acceptance criteria defined in the linked issue are satisfied.
- [ ] Integration validation performed (e.g., adjacent components in the monorepo still work as expected).

## Testing Performed
<!-- Document the automated and/or manual testing performed -->
- [ ] Local build/lint passed (e.g., `black .`, `flake8 .`, `npm run lint`, `npm run build`, or `pytest`)
- [ ] Manual testing steps:
  <!-- e.g., 1. Started CnSS, 2. Sent mock telemetry from TP, 3. Verified MUI updated correctly -->

## Changelog
<!-- ⚠️ CRITICAL: Check EXACTLY ONE of the following boxes. -->
- [ ] Added or updated a user-visible entry in `CHANGELOG.md` (under `[Unreleased]`)
- [ ] Not applicable because the change is not user-visible (e.g., internal refactoring, CI config, documentation)

## Reviewer Checklist

- [ ] Code follows the project's style guidelines and Conventional Commits format.
- [ ] No sensitive data, PII, real names, or private recording links are included (Sanitization Check passed).
- [ ] All required CI checks (including Lychee Link Check) are passing.
- [ ] Branch is up to date with `develop`.
