# Workflow Setup Documentation

## CI Hourly Check and Update Workflow

### Branch Strategy

The `ci-hourly-check.yaml` workflow is designed to work exclusively with the **snapshot branch**:

- ✅ **Workflow file location**: Only exists on `snapshot` branch
- ✅ **Execution context**: Always runs from `snapshot` branch  
- ✅ **Target branch**: Always works with `snapshot` branch content
- ❌ **Master branch**: Workflow file removed to prevent confusion

### Why This Setup?

1. **Single Source of Truth**: Workflow exists only on snapshot branch
2. **Consistent Execution**: All scheduled and manual runs work with snapshot content
3. **No Branch Confusion**: Prevents GitHub Actions from running workflow from master branch
4. **Proper Updates**: All application updates are committed to snapshot branch

### Workflow Behavior

**Scheduled Runs (Hourly Cron)**:
- Executes from `snapshot` branch
- Checks out `snapshot` branch content  
- Updates `platform-descriptor.json` if needed
- Commits and pushes to `snapshot` branch

**Manual Runs (Workflow Dispatch)**:
- Executes from `snapshot` branch
- Allows branch override (defaults to `snapshot`)
- Commits and pushes to the specified branch

### Important Notes

- The workflow file should **never** be added back to the master branch
- All application version updates happen on the snapshot branch
- Success/failure notifications properly reflect actual processing results