# Action Extraction Quick Reference

Quick reference guide for implementing the 6 proposed composite actions from the workflow reorganization.

---

## Summary Table

| # | Action | Phase | Lines Saved | Effort | Priority | Status |
|---|--------|-------|-------------|--------|----------|--------|
| 1 | [check-branch-and-pr-status](./action-extraction-reports/phase1-high-priority/01-check-branch-and-pr-status.md) | 1 | ~40 | 2-3h | 🔴 High | ⬜ Not Started |
| 2 | [fetch-base-file](./action-extraction-reports/phase1-high-priority/02-fetch-base-file.md) | 1 | ~80 | 2-3h | 🔴 High | ⬜ Not Started |
| 3 | [generate-platform-diff-report](./action-extraction-reports/phase1-high-priority/03-generate-platform-diff-report.md) | 1 | ~200 | 4-6h | 🔴 Very High | ⬜ Not Started |
| 4 | [calculate-version-increment](./action-extraction-reports/phase2-medium-priority/04-calculate-version-increment.md) | 2 | ~30 | 1-2h | 🟡 Medium | ⬜ Not Started |
| 5 | [generate-package-diff-report](./action-extraction-reports/phase2-medium-priority/05-generate-package-diff-report.md) | 2 | ~80 | 3-4h | 🟡 Medium | ⬜ Not Started |
| 6 | [build-pr-body](./action-extraction-reports/phase2-medium-priority/06-build-pr-body.md) | 2 | ~40 | 1-2h | 🟢 Low | ⬜ Not Started |

**Total Impact:** ~470 lines reduced, 14-20 hours estimated effort

---

## Implementation Checklist

### Phase 1: High Priority (Week 1-2)

- [ ] **Action #1: check-branch-and-pr-status**
  - [ ] Create `.github/actions/check-branch-and-pr-status/`
  - [ ] Create `action.yml` and `README.md`
  - [ ] Test action independently
  - [ ] Update `determine-source-branch` job in workflow
  - [ ] Verify outputs match previous behavior
  - [ ] Tag/document action

- [ ] **Action #2: fetch-base-file**
  - [ ] Create `.github/actions/fetch-base-file/`
  - [ ] Create `action.yml` and `README.md`
  - [ ] Test with various file types
  - [ ] Update `update-platform-descriptor` job (descriptor fetch)
  - [ ] Update `update-package-json` job (package.json fetch)
  - [ ] Verify both instances work correctly
  - [ ] Tag/document action

- [ ] **Action #3: generate-platform-diff-report**
  - [ ] Create `.github/actions/generate-platform-diff-report/`
  - [ ] Create `action.yml`, `scripts/generate-diff.sh`, `README.md`
  - [ ] Make script executable (`chmod +x`)
  - [ ] Test with sample descriptors
  - [ ] Update `generate-reports` job
  - [ ] Verify markdown output format
  - [ ] Tag/document action

- [ ] **Phase 1 Integration Testing**
  - [ ] Run workflow with `dry_run: true`
  - [ ] Compare outputs with previous runs
  - [ ] Fix any integration issues
  - [ ] Production test run

### Phase 2: Medium Priority (Week 3-4)

- [ ] **Action #4: calculate-version-increment**
  - [ ] Create `.github/actions/calculate-version-increment/`
  - [ ] Create `action.yml` and `README.md`
  - [ ] Test version pattern matching
  - [ ] Update `update-platform-descriptor` job
  - [ ] Verify version calculation
  - [ ] Tag/document action

- [ ] **Action #5: generate-package-diff-report**
  - [ ] Create `.github/actions/generate-package-diff-report/`
  - [ ] Create `action.yml`, `scripts/generate-package-diff.sh`, `README.md`
  - [ ] Make script executable
  - [ ] Test with sample package.json files
  - [ ] Update `generate-reports` job
  - [ ] Verify markdown output
  - [ ] Tag/document action

- [ ] **Action #6: build-pr-body**
  - [ ] Create `.github/actions/build-pr-body/`
  - [ ] Create `action.yml` and `README.md`
  - [ ] Test PR body formatting
  - [ ] Update `manage-pr` job
  - [ ] Verify PR descriptions
  - [ ] Tag/document action

- [ ] **Phase 2 Integration Testing**
  - [ ] Run full workflow with `dry_run: true`
  - [ ] Validate all outputs and PR bodies
  - [ ] Production test run
  - [ ] Monitor for issues

### Final Phase: Documentation & Review (Week 5)

- [ ] **Documentation**
  - [ ] Update main workflow README
  - [ ] Document action usage examples
  - [ ] Create architecture diagram
  - [ ] Write migration guide

- [ ] **Code Review**
  - [ ] Review all action implementations
  - [ ] Verify FOLIO standards compliance
  - [ ] Check error handling
  - [ ] Validate shell safety

- [ ] **Testing & Validation**
  - [ ] Run comprehensive test suite
  - [ ] Test error scenarios
  - [ ] Validate dry-run mode
  - [ ] Production validation

- [ ] **Deployment**
  - [ ] Merge to main branch
  - [ ] Tag stable versions
  - [ ] Update dependent workflows
  - [ ] Announce changes to team

---

## Quick Commands

### Create Action Template

```bash
ACTION_NAME="your-action-name"
mkdir -p ".github/actions/$ACTION_NAME/scripts"
cd ".github/actions/$ACTION_NAME"
touch action.yml README.md
[ -d scripts ] && touch scripts/main.sh && chmod +x scripts/main.sh
```

### Test Action Locally

```bash
# Set required environment variables
export INPUT_PARAM1="value1"
export INPUT_PARAM2="value2"

# Run action script
cd .github/actions/your-action-name
bash scripts/main.sh
```

### Validate YAML Syntax

```bash
# Validate action.yml
yq eval '.inputs' .github/actions/your-action-name/action.yml

# Validate workflow
yq eval '.jobs' .github/workflows/release-update-flow.yml
```

### Test Workflow with Act

```bash
# Install act (if not already)
brew install act  # macOS
# or
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Run workflow locally
act workflow_dispatch -W .github/workflows/release-update-flow.yml
```

---

## Common Patterns

### Action Structure

```
.github/actions/action-name/
├── action.yml           # Action metadata and interface
├── README.md           # Documentation
└── scripts/            # Optional: for complex logic
    └── main.sh        # Main script (must be executable)
```

### Action YML Template

```yaml
name: 'Action Name'
description: 'Action description'
author: 'FOLIO DevOps'

inputs:
  param_name:
    description: 'Parameter description'
    required: true
    default: 'default_value'

outputs:
  output_name:
    description: 'Output description'
    value: ${{ steps.step_id.outputs.output_name }}

runs:
  using: 'composite'
  steps:
    - name: 'Step name'
      id: step_id
      shell: bash
      env:
        PARAM: ${{ inputs.param_name }}
      run: |
        # Script inline or:
        # run: ${{ github.action_path }}/scripts/main.sh
```

### Script Template

```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# Validate inputs
if [ -z "${REQUIRED_INPUT:-}" ]; then
  echo "::error::Required input not provided"
  exit 1
fi

# Main logic
echo "::notice::Processing..."

# Output results
echo "output_name=value" >> "$GITHUB_OUTPUT"
```

---

## Troubleshooting

### Common Issues

**Issue:** Action not found  
**Solution:** Check branch reference in `uses:` matches where action exists

**Issue:** Outputs not available  
**Solution:** Verify step `id` matches output reference `${{ steps.id.outputs.name }}`

**Issue:** Script permission denied  
**Solution:** Run `chmod +x scripts/your-script.sh`

**Issue:** Environment variable not set  
**Solution:** Check `env:` section maps inputs correctly

---

## Resources

- [Main Reorganization Report](./workflow-reorganization-report.md)
- [Action Extraction Reports Index](./action-extraction-reports/README.md)
- [FOLIO Coding Instructions](../copilot-instructions.md)
- [Release Update Flow Workflow](../workflows/release-update-flow.yml)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

---

**Last Updated:** October 29, 2025  
**Version:** 1.0  
**Status:** Ready for Implementation

