# Merge Queue Check Workflow

## Purpose

Validates a merge group of a platform release branch and reports the result as the check run
`eureka-ci/release-platform-validation`, the same context [Release PR Check](./release-pr-check.md) reports on the
pull request. The ruleset of the branch requires this one context, so GitHub merges the group when the check
succeeds and removes the pull request from the queue when it fails.

## Triggers

- **workflow_dispatch**: the only declared trigger.
- Automated in practice via the Eureka CI GitHub App webhook listener, which dispatches this workflow for
  `merge_group` `checks_requested` events on `folio-org/platform-lsp`. The mapping lives in
  `kitfox-github/gh-app-webhook-listener/terraform/environments/github_events_config.json`.

## Workflow Inputs

| Input | Type | Default | Required | Description |
|-------|------|---------|----------|-------------|
| `repo_owner` | string | - | Yes | Repository owner |
| `repo_name` | string | - | Yes | Repository name |
| `head_sha` | string | - | Yes | Head commit SHA of the merge group |
| `base_branch` | string | - | Yes | Target branch of the merge group |
| `head_branch` | string | `''` | No | Merge group ref without `refs/heads/`, e.g. `gh-readonly-queue/R1-2026/pr-123-<base sha>`; the pull request number is taken from it |

## Job Flow

```mermaid
flowchart TD
    A[create-check-run] --> B[pre-check]
    B --> C[validate-platform]
    C --> D[build-stripes]
    A --> E[finalize-check-run]
    B --> E
    C --> E
    D --> E
    E --> F[notify]
    E --> G[summarize]
    F --> G

    style A fill:#e1f5ff
    style B fill:#e1f5ff
    style C fill:#ffe1f5
    style D fill:#ffe1f5
    style E fill:#fff4e1
    style F fill:#e1ffe1
    style G fill:#f0f0f0
```

## Jobs

### create-check-run
**Responsibility**: Create the check run `eureka-ci/release-platform-validation` on `head_sha` with status
`in_progress`, before any configuration is read.

**Outputs**:
- `check_run_id`: ID of the created check run
- `pr_number`: Pull request number parsed from `head_branch`, empty if it does not match

---

### pre-check
**Responsibility**: Read the update configuration and decide whether the target branch is validated through the
merge queue.

**Outputs**:
- `status`: `success` or `not_configured`
- `message`: Validation message
- `branch_entry`: The target branch's entry from `get-update-config` `branch_config`, as compact JSON

**Not configured** (the check run concludes as `failure`):
- Configuration file (`.github/update-config.yml`) not found on `master`
- Updates disabled in configuration
- Target branch not listed under `branches`, or disabled
- Target branch has `need_pr` other than `true`

On `success` the job checks out `head_sha` and uploads `platform-descriptor.json` as the `platform-descriptor`
artifact.

**Composite Actions**:
- `folio-org/kitfox-github/.github/actions/get-update-config@master`

---

### validate-platform
**Responsibility**: Validate the platform descriptor and the dependencies of its applications against FAR.

**Runs**: When `pre-check` reports `success`

**Outputs**:
- `validation_passed`: `true` when validation passed
- `failure_reason`: Error message on failure

**Composite Actions**:
- `folio-org/platform-lsp/.github/actions/validate-platform@master`

---

### build-stripes
**Responsibility**: Install the UI dependencies of the merge group commit with Node 22 and the FOLIO npm registry
(`yarn install --frozen-lockfile` when `yarn.lock` exists). A `yarn.lock` that does not match `package.json`
fails the install.

**Runs**: When `validate-platform` passed

---

### finalize-check-run
**Responsibility**: Complete the check run. Runs whenever the check run was created.

**Conclusion**:

| Outcome | Conclusion |
|---------|------------|
| Validation and Stripes build passed | `success` |
| Target branch not configured | `failure` |
| Configuration could not be read | `failure` |
| Validation failed | `failure` |
| Stripes build failed or did not complete | `failure` |
| A job was cancelled | `cancelled` |

The check never concludes as `neutral` or `skipped`: GitHub treats both as passing a required check.

**Outputs**:
- `conclusion`: Conclusion of the check run
- `summary`: Summary of the check run

---

### notify
**Responsibility**: Send Slack notifications to configured channels.

**Runs**: Always, unless the run was cancelled

**Channels**:
- **Team Channel**: Repository variable `SLACK_NOTIF_CHANNEL` _(optional)_
- **General Channel**: Repository variable `GENERAL_SLACK_NOTIF_CHANNEL` _(optional)_

**Message Content**:
- Target branch, pull request and commit
- Failure reason (if applicable)

**Required Secret**: `EUREKA_CI_SLACK_BOT_TOKEN`

---

### summarize
**Responsibility**: Generate workflow summary in GitHub Actions UI.

**Runs**: Always (regardless of previous job failures)

**Summary Sections**:
- Target branch, merge group, pull request and commit
- Check run conclusion
- Pre-check, platform validation and Stripes build status
- Notification status

## Configuration Requirements

### Repository File
**`.github/update-config.yml`** on `master`. The merge queue of a branch comes from its `ruleset` settings:

```yaml
update_config:
  enabled: true
  ruleset:
    enabled: true
    required_checks:
      - context: "eureka-ci/release-platform-validation"
    merge_queue:
      enabled: true

branches:
  - R1-2026:
      enabled: true
      need_pr: true
      ruleset:
        enabled: true
```

### Repository Variables
| Variable | Purpose | Required |
|----------|---------|----------|
| `EUREKA_CI_APP_ID` | Eureka CI GitHub App ID | Yes |
| `FAR_URL` | FAR API base URL | Yes |
| `SLACK_NOTIF_CHANNEL` | Team Slack channel ID | No |
| `GENERAL_SLACK_NOTIF_CHANNEL` | General Slack channel ID | No |

### Repository Secrets
| Secret | Purpose | Required |
|--------|---------|----------|
| `EUREKA_CI_APP_KEY` | Eureka CI GitHub App private key | Yes |
| `EUREKA_CI_SLACK_BOT_TOKEN` | Slack bot OAuth token | Only if notifications enabled |

## Permissions

```yaml
permissions:
  contents: read
```

Check runs are created and updated with an Eureka CI GitHub App installation token: the Checks API accepts only
GitHub App tokens, and the ruleset resolves the required check to that App. Everything else uses `GITHUB_TOKEN`.

## Usage Example

### Manual Trigger
```bash
gh workflow run merge-queue-check.yml \
  --repo folio-org/platform-lsp \
  -f repo_owner=folio-org \
  -f repo_name=platform-lsp \
  -f head_sha=abc123def456 \
  -f base_branch=R1-2026
```

A manual run reports the check run on `head_sha` like an automated one.

### Automated Trigger
The webhook listener dispatches the same workflow with the same inputs, plus `head_branch`, for every merge group.

## Related Documentation

- [Release PR Check](./release-pr-check.md) — reports the same check on the pull request
- [Post-Merge Flow](./post-merge-flow.md) — cleans up the update branch after the merge
- [Repository configuration](../update-config.yml) — this repository's `update-config.yml`
- [Branch Ruleset Automation](https://github.com/folio-org/kitfox-github/blob/master/.github/docs/branch-ruleset-automation.md) — provisions the rulesets and merge queues from that file
