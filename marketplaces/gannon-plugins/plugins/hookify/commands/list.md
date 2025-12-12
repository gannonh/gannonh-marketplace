---
description: List all configured hookify rules
allowed-tools: ["Glob", "Read", "Skill"]
---

# List Hookify Rules

**Load hookify:writing-rules skill first** to understand rule format.

Show all configured hookify rules from both user-level (~/.claude/) and project-level (.claude/).

## Steps

1. Search for hookify rule files in both locations:

   **User-level rules** (apply to all projects):
   ```
   pattern: "~/.claude/hookify.*.local.md"
   ```

   **Project-level rules** (apply to current project only):
   ```
   pattern: ".claude/hookify.*.local.md"
   ```

2. For each file found:
   - Use Read tool to read the file
   - Extract frontmatter fields: name, enabled, event, pattern
   - Extract message preview (first 100 chars)
   - Note the source (user or project)

3. Present results in tables by source:

```
## User-Level Rules (apply to all projects)
Location: ~/.claude/

| Name | Enabled | Event | Pattern | File |
|------|---------|-------|---------|------|
| block-force-push | ✅ Yes | bash | git push --force | hookify.block-force-push.local.md |

**Total**: 1 rule (1 enabled)

## Project-Level Rules (this project only)
Location: .claude/

| Name | Enabled | Event | Pattern | File |
|------|---------|-------|---------|------|
| warn-dangerous-rm | ✅ Yes | bash | rm\s+-rf | hookify.dangerous-rm.local.md |
| warn-console-log | ✅ Yes | file | console\.log\( | hookify.console-log.local.md |
| check-tests | ❌ No | stop | .* | hookify.require-tests.local.md |

**Total**: 3 rules (2 enabled, 1 disabled)
```

4. For each rule, show a brief preview:
```
### warn-dangerous-rm
**Source**: Project
**Event**: bash
**Pattern**: `rm\s+-rf`
**Message**: "Dangerous rm command detected! This command could delete..."

**Status**: Active
**File**: .claude/hookify.dangerous-rm.local.md
```

5. Add helpful footer:
```
---

## Rule Precedence
- Project rules override user rules with the same name
- User rules apply across all projects where no project rule exists

## Managing Rules
- To modify a rule: Edit the .local.md file directly
- To disable a rule: Set `enabled: false` in frontmatter
- To enable a rule: Set `enabled: true` in frontmatter
- To delete a rule: Remove the .local.md file
- To create a rule: Use `/hookify` command

## Rule Locations
- **User rules**: ~/.claude/hookify.{name}.local.md (global)
- **Project rules**: .claude/hookify.{name}.local.md (project-specific)

**Remember**: Changes take effect immediately - no restart needed
```

## If No Rules Found

If no hookify rules exist:

```
## No Hookify Rules Configured

You haven't created any hookify rules yet.

To get started:
1. Use `/hookify` to analyze conversation and create rules
2. Or manually create rule files:
   - User-level: `~/.claude/hookify.my-rule.local.md` (applies everywhere)
   - Project-level: `.claude/hookify.my-rule.local.md` (this project only)
3. See `/hookify:help` for documentation

Example:
```
/hookify Warn me when I use console.log
```

Check `${CLAUDE_PLUGIN_ROOT}/examples/` for example rule files.
```
