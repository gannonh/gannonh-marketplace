---
name: block-force-push
enabled: true
event: bash
pattern: git\s+push\s+.*--force|git\s+push\s+-f
action: block
---

**Force push blocked!**

Force pushing can destroy commit history for other collaborators.

**Safer alternatives:**
- Use `git push --force-with-lease` which checks for upstream changes first
- Use `git push --force-with-lease=origin/main` to be even more specific
- Coordinate with your team before force pushing

**If you really need to force push:**
1. Ensure no one else is working on this branch
2. Communicate with your team
3. Consider if rebasing is actually necessary

This is a user-level rule and applies to ALL projects. If you need to allow
force push for a specific project, create a project-level rule with the same
name but `action: warn` or `enabled: false`.
