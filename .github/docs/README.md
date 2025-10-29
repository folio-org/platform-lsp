# GitHub Actions Documentation

This directory contains comprehensive documentation for FOLIO platform LSP GitHub Actions workflows and CI/CD automation.

---

## 📁 Directory Contents

### Workflow Documentation
- [Release Flow](./release-flow.md) - Main release workflow documentation
- [Release Package Flow](./release-package-flow.md) - Package release workflow
- [Snapshot Flow](./snapshot-flow.md) - Snapshot build workflow
- [Release Preparation](./release-preparation.md) - Release preparation guide

### Workflow Reorganization Project
- [**Implementation Summary**](./IMPLEMENTATION-SUMMARY.md) - **Start here!** Overview of the reorganization project
- [Workflow Reorganization Report](./workflow-reorganization-report.md) - Comprehensive analysis with diagrams
- [Action Extraction Quick Reference](./action-extraction-quick-reference.md) - Fast implementation guide
- [Action Extraction Reports](./action-extraction-reports/README.md) - Detailed action-by-action guides

---

## 🎯 Workflow Reorganization Project

### Overview
The workflow reorganization project aims to refactor the `release-update-flow.yml` workflow by extracting inline logic into reusable composite actions. This improves maintainability, reusability, and testability.

### Key Metrics
- **Complexity Reduction:** 89% (560 lines → 60 lines of inline scripts)
- **New Actions:** 6 reusable composite actions
- **Estimated Effort:** 14-20 hours development + 8-16 hours testing
- **Implementation Phases:** 2 phases over 4 weeks

### Getting Started

#### For Project Managers
1. Read [Implementation Summary](./IMPLEMENTATION-SUMMARY.md)
2. Review [Main Report](./workflow-reorganization-report.md) for detailed analysis
3. Use [Quick Reference](./action-extraction-quick-reference.md) for tracking

#### For Developers
1. Start with [Action Reports Index](./action-extraction-reports/README.md)
2. Pick an action from [Phase 1](./action-extraction-reports/phase1-high-priority/) or [Phase 2](./action-extraction-reports/phase2-medium-priority/)
3. Follow the step-by-step guide in the individual report
4. Test and validate using provided scenarios

---

## 📋 Proposed Actions

### Phase 1: High Priority
1. [check-branch-and-pr-status](./action-extraction-reports/phase1-high-priority/01-check-branch-and-pr-status.md) - 40 lines, 2-3h
2. [fetch-base-file](./action-extraction-reports/phase1-high-priority/02-fetch-base-file.md) - 80 lines, 2-3h
3. [generate-platform-diff-report](./action-extraction-reports/phase1-high-priority/03-generate-platform-diff-report.md) - 200 lines, 4-6h

### Phase 2: Medium Priority
4. [calculate-version-increment](./action-extraction-reports/phase2-medium-priority/04-calculate-version-increment.md) - 30 lines, 1-2h
5. [generate-package-diff-report](./action-extraction-reports/phase2-medium-priority/05-generate-package-diff-report.md) - 80 lines, 3-4h
6. [build-pr-body](./action-extraction-reports/phase2-medium-priority/06-build-pr-body.md) - 40 lines, 1-2h

---

## 🔗 Quick Links

### Essential Reading
- 🎯 [Implementation Summary](./IMPLEMENTATION-SUMMARY.md) - Project overview
- 📊 [Main Analysis Report](./workflow-reorganization-report.md) - Complete technical analysis
- ⚡ [Quick Reference](./action-extraction-quick-reference.md) - Implementation checklists

### Visualizations
- [Release Package Flow Diagram](./release-package-flow.svg) - SVG visualization
- [Release Package Flow Mermaid](./release-package-flow.mmd) - Mermaid source

### Related Documentation
- [FOLIO Coding Instructions](../copilot-instructions.md) - Coding standards
- [Release Update Flow Workflow](../workflows/release-update-flow.yml) - Source workflow
- [Actions Directory](../actions/) - Existing composite actions

---

## 🚀 Implementation Status

| Phase | Actions | Status | Progress |
|-------|---------|--------|----------|
| Planning | 9 reports | ✅ Complete | 100% |
| Phase 1 | 3 actions | ⬜ Not Started | 0% |
| Phase 2 | 3 actions | ⬜ Not Started | 0% |
| Final | Docs & Review | ⬜ Not Started | 0% |

**Last Updated:** October 29, 2025

---

## 📖 Additional Resources

### GitHub Actions
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Composite Actions Guide](https://docs.github.com/en/actions/creating-actions/creating-a-composite-action)
- [Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)

### FOLIO Resources
- [FOLIO Developer Documentation](https://dev.folio.org/)
- [Platform LSP Repository](https://github.com/folio-org/platform-lsp)
- [Kitfox GitHub Actions](https://github.com/folio-org/kitfox-github)

---

## 🤝 Contributing

When implementing actions from the reorganization project:

1. Follow the implementation guide in the specific action report
2. Ensure all code follows [FOLIO coding instructions](../copilot-instructions.md)
3. Test thoroughly using the provided test scenarios
4. Update the success criteria checklist
5. Submit PR with clear description referencing the action report

---

## 📞 Support

For questions or issues:
- Review the individual action report for troubleshooting guidance
- Check [Quick Reference](./action-extraction-quick-reference.md) for common issues
- Consult [FOLIO coding instructions](../copilot-instructions.md) for standards
- Open an issue in the repository with clear details

---

**Documentation Version:** 1.0  
**Last Updated:** October 29, 2025  
**Maintained by:** FOLIO DevOps Team

