# Hookify Plugin

Easily create custom hooks to prevent unwanted behaviors by analyzing conversation patterns or from explicit instructions.

> **Fork Note**: This is a fork of the original [hookify plugin](https://github.com/anthropics/claude-code) by Anthropic, with added support for user-level rules that apply across all projects.

## Overview

The hookify plugin makes it simple to create hooks without editing complex `hooks.json` files. Instead, you create lightweight markdown configuration files that define patterns to watch for and messages to show when those patterns match.

**Key features:**
- Analyze conversations to find unwanted behaviors automatically
- Simple markdown configuration files with YAML frontmatter
- Regex pattern matching for powerful rules
- No coding required - just describe the behavior
- Easy enable/disable without restarting
- **User-level rules** that apply across all projects
- **Project-level rules** for project-specific behavior

## Quick Start

### 1. Create Your First Rule

```bash
/hookify Warn me when I use rm -rf commands
```

This analyzes your request and creates `.claude/hookify.warn-rm.local.md`.

### 2. Test It Immediately

**No restart needed!** Rules take effect on the very next tool use.

Ask Claude to run a command that should trigger the rule:
```
Run rm -rf /tmp/test
```

You should see the warning message immediately!

## Rule Locations

Hookify supports two levels of rules:

### User-Level Rules (Global)

Location: `~/.claude/hookify.*.local.md`

These rules apply to **all projects** and are ideal for:
- Personal coding standards
- Global safety rules (e.g., block force push)
- Company-wide best practices

### Project-Level Rules (Local)

Location: `.claude/hookify.*.local.md` (in project root)

These rules apply to the **current project only** and are ideal for:
- Project-specific conventions
- Framework-specific warnings
- Team agreements for this codebase

### Precedence

If a user-level rule and project-level rule have the same name:
- **Project rules take precedence** over user rules
- This allows projects to override global defaults when needed

## Usage

### Main Command: /hookify

**With arguments:**
```
/hookify Don't use console.log in TypeScript files
```
Creates a rule from your explicit instructions.

**Without arguments:**
```
/hookify
```
Analyzes recent conversation to find behaviors you've corrected or been frustrated by.

### Helper Commands

**List all rules:**
```
/hookify:list
```

**Configure rules interactively:**
```
/hookify:configure
```
Enable/disable existing rules through an interactive interface.

**Get help:**
```
/hookify:help
```

## Rule Configuration Format

### Simple Rule (Single Pattern)

`.claude/hookify.dangerous-rm.local.md`:
```markdown
---
name: block-dangerous-rm
enabled: true
event: bash
pattern: rm\s+-rf
action: block
---

**Dangerous rm command detected!**

This command could delete important files. Please:
- Verify the path is correct
- Consider using a safer approach
- Make sure you have backups
```

**Action field:**
- `warn`: Shows warning but allows operation (default)
- `block`: Prevents operation from executing (PreToolUse) or stops session (Stop events)

### Advanced Rule (Multiple Conditions)

`.claude/hookify.sensitive-files.local.md`:
```markdown
---
name: warn-sensitive-files
enabled: true
event: file
action: warn
conditions:
  - field: file_path
    operator: regex_match
    pattern: \.env$|credentials|secrets
  - field: new_text
    operator: contains
    pattern: KEY
---

**Sensitive file edit detected!**

Ensure credentials are not hardcoded and file is in .gitignore.
```

**All conditions must match** for the rule to trigger.

## Event Types

- **`bash`**: Triggers on Bash tool commands
- **`file`**: Triggers on Edit, Write, MultiEdit tools
- **`stop`**: Triggers when Claude wants to stop (for completion checks)
- **`prompt`**: Triggers on user prompt submission
- **`all`**: Triggers on all events

## Pattern Syntax

Use Python regex syntax:

| Pattern | Matches | Example |
|---------|---------|---------|
| `rm\s+-rf` | rm -rf | rm -rf /tmp |
| `console\.log\(` | console.log( | console.log("test") |
| `(eval\|exec)\(` | eval( or exec( | eval("code") |
| `\.env$` | files ending in .env | .env, .env.local |
| `chmod\s+777` | chmod 777 | chmod 777 file.txt |

**Tips:**
- Use `\s` for whitespace
- Escape special chars: `\.` for literal dot
- Use `|` for OR: `(foo|bar)`
- Use `.*` to match anything
- Set `action: block` for dangerous operations
- Set `action: warn` (or omit) for informational warnings

## Examples

### Example 1: User-Level Safety Rule

`~/.claude/hookify.block-force-push.local.md`:
```markdown
---
name: block-force-push
enabled: true
event: bash
pattern: git\s+push\s+.*--force|git\s+push\s+-f
action: block
---

**Force push blocked!**

Force pushing can destroy commit history. Please:
- Use `--force-with-lease` instead
- Or ask for explicit permission if you really need --force
```

This rule blocks force pushes across **all projects**.

### Example 2: Project-Level Debug Warning

`.claude/hookify.warn-debug-code.local.md`:
```markdown
---
name: warn-debug-code
enabled: true
event: file
pattern: console\.log\(|debugger;|print\(
action: warn
---

**Debug code detected**

Remember to remove debugging statements before committing.
```

### Example 3: Require Tests Before Stopping

```markdown
---
name: require-tests-run
enabled: false
event: stop
action: block
conditions:
  - field: transcript
    operator: not_contains
    pattern: npm test|pytest|cargo test
---

**Tests not detected in transcript!**

Before stopping, please run tests to verify your changes work correctly.
```

## Advanced Usage

### Multiple Conditions

Check multiple fields simultaneously:

```markdown
---
name: api-key-in-typescript
enabled: true
event: file
conditions:
  - field: file_path
    operator: regex_match
    pattern: \.tsx?$
  - field: new_text
    operator: regex_match
    pattern: (API_KEY|SECRET|TOKEN)\s*=\s*["']
---

**Hardcoded credential in TypeScript!**

Use environment variables instead of hardcoded values.
```

### Operators Reference

- `regex_match`: Pattern must match (most common)
- `contains`: String must contain pattern
- `equals`: Exact string match
- `not_contains`: String must NOT contain pattern
- `starts_with`: String starts with pattern
- `ends_with`: String ends with pattern

### Field Reference

**For bash events:**
- `command`: The bash command string

**For file events:**
- `file_path`: Path to file being edited
- `new_text`: New content being added (Edit, Write)
- `old_text`: Old content being replaced (Edit only)
- `content`: File content (Write only)

**For prompt events:**
- `user_prompt`: The user's submitted prompt text

**For stop events:**
- Use general matching on session state

## Management

### Enable/Disable Rules

**Temporarily disable:**
Edit the `.local.md` file and set `enabled: false`

**Re-enable:**
Set `enabled: true`

**Or use interactive tool:**
```
/hookify:configure
```

### Delete Rules

Simply delete the `.local.md` file:
```bash
# Delete project rule
rm .claude/hookify.my-rule.local.md

# Delete user rule
rm ~/.claude/hookify.my-rule.local.md
```

### View All Rules

```
/hookify:list
```

## Installation

This plugin is part of the gannon-plugins marketplace.

**Add the marketplace:**
```bash
/plugin marketplace add ~/plugins/marketplaces/gannon-plugins
```

**Install the plugin:**
```bash
/plugin install hookify@gannon-plugins
```

## Requirements

- Python 3.7+
- No external dependencies (uses stdlib only)

## Troubleshooting

**Rule not triggering:**
1. Check rule file exists in correct directory:
   - User: `~/.claude/hookify.*.local.md`
   - Project: `.claude/hookify.*.local.md`
2. Verify `enabled: true` in frontmatter
3. Test regex pattern separately
4. Rules should work immediately - no restart needed
5. Try `/hookify:list` to see if rule is loaded

**Import errors:**
- Ensure Python 3 is available: `python3 --version`
- Check hookify plugin is installed

**Pattern not matching:**
- Test regex: `python3 -c "import re; print(re.search(r'pattern', 'text'))"`
- Use unquoted patterns in YAML to avoid escaping issues
- Start simple, then add complexity

**Hook seems slow:**
- Keep patterns simple (avoid complex regex)
- Use specific event types (bash, file) instead of "all"
- Limit number of active rules

## Contributing

Found a useful rule pattern? Consider sharing example files via PR!

## Future Enhancements

- Severity levels (error/warning/info distinctions)
- Rule templates library
- Interactive pattern builder
- Hook testing utilities
- JSON format support (in addition to markdown)

## License

MIT License

## Credits

Original hookify plugin by Daisy Hollman at Anthropic.
Fork with user-level support by Gannon Hall.
