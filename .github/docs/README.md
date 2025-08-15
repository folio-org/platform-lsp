# Documentation Index

This directory contains comprehensive documentation for the FOLIO platform CI/CD workflows and release management processes.

## 📋 Table of Contents

### Release Management

| Document | Description | Type |
|----------|-------------|------|
| [Release Flow](./release-flow.md) | Production of final release artifacts from prepared release branches | Architecture Guide |
| [Release Preparation](./release-preparation.md) | Orchestrated preparation of release branches across the entire FOLIO ecosystem | Architecture Guide |
| [Release Package Flow](./release-package-flow.md) | Workflow for validating, packaging, and uploading platform release artifacts | Workflow Documentation |
| [Release PR Check](./release-pr-check.md) | Validation of platform release pull requests including descriptors and dependencies | Workflow Documentation |

### Release Update Workflows

| Document | Description | Type |
|----------|-------------|------|
| [Release Scan](./release-scan.md) | Automated discovery and update orchestration for platform release branches | Workflow Documentation |
| [Release Update](./release-update.md) | Reusable workflow for updating individual platform release branches | Workflow Documentation |
| [Release Update Flow](./release-update-flow.md) | Core execution workflow for automated platform release updates | Architecture Guide |

### Continuous Integration

| Document | Description | Type |
|----------|-------------|------|
| [Snapshot Flow](./snapshot-flow.md) | Automated continuous integration for ongoing FOLIO development | Architecture Guide |

### Diagrams

| File | Description | Format |
|------|-------------|--------|
| [release-package-flow.mmd](./release-package-flow.mmd) | Release package workflow diagram source | Mermaid |
| [release-package-flow.svg](./release-package-flow.svg) | Release package workflow diagram | SVG |

---

## 🎯 Documentation by Purpose

### For Understanding the Release Process

1. **[Release Preparation](./release-preparation.md)** - Start here to understand how FOLIO releases are prepared across 31+ repositories
2. **[Release Flow](./release-flow.md)** - Learn how prepared release branches become production-ready artifacts
3. **[Release Package Flow](./release-package-flow.md)** - Understand the packaging and upload process for release artifacts

### For Working with Release Updates

1. **[Release Scan](./release-scan.md)** - Understand how release branches are discovered and update workflows are orchestrated
2. **[Release Update](./release-update.md)** - Learn about the reusable interface for triggering release updates
3. **[Release Update Flow](./release-update-flow.md)** - Deep dive into the execution engine for platform updates

### For Continuous Integration

1. **[Snapshot Flow](./snapshot-flow.md)** - Understand daily development integration and snapshot builds

### For Release Quality Assurance

1. **[Release PR Check](./release-pr-check.md)** - Learn about automated validation for release pull requests

---

## 📚 Document Types

### Architecture Guides
Comprehensive documentation covering the design, purpose, and implementation of major CI/CD components. These documents include:
- Purpose and scope
- Architecture overview with diagrams
- Detailed workflow descriptions
- Integration points
- Security considerations
- Best practices

### Workflow Documentation
Technical documentation for specific GitHub Actions workflows, including:
- Triggers and inputs
- Job definitions and steps
- Output specifications
- Configuration examples
- Usage instructions

---

## 🔄 Related Documentation

- **[CI Overview](../CI.md)** - Overview of the continuous integration setup

---

## 📝 Document Maintenance

All documentation in this directory follows FOLIO's documentation standards:

- Use clear, descriptive headings
- Include architecture diagrams where applicable
- Provide examples for workflows and configurations
- Keep technical details up to date with workflow changes
- Use emoji icons for visual navigation (🎯 Purpose, 🏗️ Architecture, etc.)

For questions or improvements to this documentation, please open an issue or submit a pull request.

