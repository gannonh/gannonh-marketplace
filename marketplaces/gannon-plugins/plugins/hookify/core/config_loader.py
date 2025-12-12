#!/usr/bin/env python3
"""Configuration loader for hookify plugin.

Loads and parses hookify.*.local.md files from both:
- Project level: .claude/hookify.*.local.md (in current working directory)
- User level: ~/.claude/hookify.*.local.md (in user's home directory)

User-level rules apply across all projects, while project-level rules
are specific to the current project. Project rules take precedence
if there are naming conflicts.
"""

import os
import sys
import glob
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field


# Rule source levels
SOURCE_USER = "user"
SOURCE_PROJECT = "project"


@dataclass
class Condition:
    """A single condition for matching."""
    field: str  # "command", "new_text", "old_text", "file_path", etc.
    operator: str  # "regex_match", "contains", "equals", etc.
    pattern: str  # Pattern to match

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Condition':
        """Create Condition from dict."""
        return cls(
            field=data.get('field', ''),
            operator=data.get('operator', 'regex_match'),
            pattern=data.get('pattern', '')
        )


@dataclass
class Rule:
    """A hookify rule."""
    name: str
    enabled: bool
    event: str  # "bash", "file", "stop", "all", etc.
    pattern: Optional[str] = None  # Simple pattern (legacy)
    conditions: List[Condition] = field(default_factory=list)
    action: str = "warn"  # "warn" or "block" (future)
    tool_matcher: Optional[str] = None  # Override tool matching
    message: str = ""  # Message body from markdown
    source: str = SOURCE_PROJECT  # "user" or "project" - where the rule was loaded from
    source_path: str = ""  # Full path to the rule file

    @classmethod
    def from_dict(cls, frontmatter: Dict[str, Any], message: str,
                  source: str = SOURCE_PROJECT, source_path: str = "") -> 'Rule':
        """Create Rule from frontmatter dict and message body."""
        # Handle both simple pattern and complex conditions
        conditions = []

        # New style: explicit conditions list
        if 'conditions' in frontmatter:
            cond_list = frontmatter['conditions']
            if isinstance(cond_list, list):
                conditions = [Condition.from_dict(c) for c in cond_list]

        # Legacy style: simple pattern field
        simple_pattern = frontmatter.get('pattern')
        if simple_pattern and not conditions:
            # Convert simple pattern to condition
            # Infer field from event
            event = frontmatter.get('event', 'all')
            if event == 'bash':
                field = 'command'
            elif event == 'file':
                field = 'new_text'
            else:
                field = 'content'

            conditions = [Condition(
                field=field,
                operator='regex_match',
                pattern=simple_pattern
            )]

        return cls(
            name=frontmatter.get('name', 'unnamed'),
            enabled=frontmatter.get('enabled', True),
            event=frontmatter.get('event', 'all'),
            pattern=simple_pattern,
            conditions=conditions,
            action=frontmatter.get('action', 'warn'),
            tool_matcher=frontmatter.get('tool_matcher'),
            message=message.strip(),
            source=source,
            source_path=source_path
        )


def extract_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    """Extract YAML frontmatter and message body from markdown.

    Returns (frontmatter_dict, message_body).

    Supports multi-line dictionary items in lists by preserving indentation.
    """
    if not content.startswith('---'):
        return {}, content

    # Split on --- markers
    parts = content.split('---', 2)
    if len(parts) < 3:
        return {}, content

    frontmatter_text = parts[1]
    message = parts[2].strip()

    # Simple YAML parser that handles indented list items
    frontmatter = {}
    lines = frontmatter_text.split('\n')

    current_key = None
    current_list = []
    current_dict = {}
    in_list = False
    in_dict_item = False

    for line in lines:
        # Skip empty lines and comments
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue

        # Check indentation level
        indent = len(line) - len(line.lstrip())

        # Top-level key (no indentation or minimal)
        if indent == 0 and ':' in line and not line.strip().startswith('-'):
            # Save previous list/dict if any
            if in_list and current_key:
                if in_dict_item and current_dict:
                    current_list.append(current_dict)
                    current_dict = {}
                frontmatter[current_key] = current_list
                in_list = False
                in_dict_item = False
                current_list = []

            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()

            if not value:
                # Empty value - list or nested structure follows
                current_key = key
                in_list = True
                current_list = []
            else:
                # Simple key-value pair
                value = value.strip('"').strip("'")
                if value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                frontmatter[key] = value

        # List item (starts with -)
        elif stripped.startswith('-') and in_list:
            # Save previous dict item if any
            if in_dict_item and current_dict:
                current_list.append(current_dict)
                current_dict = {}

            item_text = stripped[1:].strip()

            # Check if this is an inline dict (key: value on same line)
            if ':' in item_text and ',' in item_text:
                # Inline comma-separated dict: "- field: command, operator: regex_match"
                item_dict = {}
                for part in item_text.split(','):
                    if ':' in part:
                        k, v = part.split(':', 1)
                        item_dict[k.strip()] = v.strip().strip('"').strip("'")
                current_list.append(item_dict)
                in_dict_item = False
            elif ':' in item_text:
                # Start of multi-line dict item: "- field: command"
                in_dict_item = True
                k, v = item_text.split(':', 1)
                current_dict = {k.strip(): v.strip().strip('"').strip("'")}
            else:
                # Simple list item
                current_list.append(item_text.strip('"').strip("'"))
                in_dict_item = False

        # Continuation of dict item (indented under list item)
        elif indent > 2 and in_dict_item and ':' in line:
            # This is a field of the current dict item
            k, v = stripped.split(':', 1)
            current_dict[k.strip()] = v.strip().strip('"').strip("'")

    # Save final list/dict if any
    if in_list and current_key:
        if in_dict_item and current_dict:
            current_list.append(current_dict)
        frontmatter[current_key] = current_list

    return frontmatter, message


def get_user_rules_dir() -> Optional[Path]:
    """Get the user-level hookify rules directory.

    Returns:
        Path to ~/.claude if it exists, None otherwise.
    """
    home = Path.home()
    user_claude_dir = home / '.claude'
    if user_claude_dir.exists() and user_claude_dir.is_dir():
        return user_claude_dir
    return None


def get_project_rules_dir() -> Optional[Path]:
    """Get the project-level hookify rules directory.

    Returns:
        Path to .claude in current working directory if it exists, None otherwise.
    """
    project_claude_dir = Path('.claude')
    if project_claude_dir.exists() and project_claude_dir.is_dir():
        return project_claude_dir
    return None


def load_rules(event: Optional[str] = None) -> List[Rule]:
    """Load all hookify rules from both user and project .claude directories.

    Rules are loaded from two locations:
    1. User level: ~/.claude/hookify.*.local.md (global rules for all projects)
    2. Project level: .claude/hookify.*.local.md (project-specific rules)

    Project-level rules take precedence over user-level rules if they have
    the same name.

    Args:
        event: Optional event filter ("bash", "file", "stop", etc.)

    Returns:
        List of enabled Rule objects matching the event.
    """
    rules_by_name: Dict[str, Rule] = {}

    # Load user-level rules first (lower priority)
    user_dir = get_user_rules_dir()
    if user_dir:
        user_rules = _load_rules_from_dir(user_dir, SOURCE_USER, event)
        for rule in user_rules:
            rules_by_name[rule.name] = rule

    # Load project-level rules (higher priority - overwrites user rules)
    project_dir = get_project_rules_dir()
    if project_dir:
        project_rules = _load_rules_from_dir(project_dir, SOURCE_PROJECT, event)
        for rule in project_rules:
            rules_by_name[rule.name] = rule

    return list(rules_by_name.values())


def _load_rules_from_dir(rules_dir: Path, source: str,
                         event: Optional[str] = None) -> List[Rule]:
    """Load all hookify rules from a specific directory.

    Args:
        rules_dir: Directory to search for rule files
        source: Source identifier ("user" or "project")
        event: Optional event filter

    Returns:
        List of enabled Rule objects matching the event.
    """
    rules = []

    # Find all hookify.*.local.md files
    pattern = str(rules_dir / 'hookify.*.local.md')
    files = glob.glob(pattern)

    for file_path in files:
        try:
            rule = load_rule_file(file_path, source=source)
            if not rule:
                continue

            # Filter by event if specified
            if event:
                if rule.event != 'all' and rule.event != event:
                    continue

            # Only include enabled rules
            if rule.enabled:
                rules.append(rule)

        except (IOError, OSError, PermissionError) as e:
            # File I/O errors - log and continue
            print(f"Warning: Failed to read {file_path}: {e}", file=sys.stderr)
            continue
        except (ValueError, KeyError, AttributeError, TypeError) as e:
            # Parsing errors - log and continue
            print(f"Warning: Failed to parse {file_path}: {e}", file=sys.stderr)
            continue
        except Exception as e:
            # Unexpected errors - log with type details
            print(f"Warning: Unexpected error loading {file_path} ({type(e).__name__}): {e}", file=sys.stderr)
            continue

    return rules


def load_rule_file(file_path: str, source: str = SOURCE_PROJECT) -> Optional[Rule]:
    """Load a single rule file.

    Args:
        file_path: Path to the rule file
        source: Source identifier ("user" or "project")

    Returns:
        Rule object or None if file is invalid.
    """
    try:
        with open(file_path, 'r') as f:
            content = f.read()

        frontmatter, message = extract_frontmatter(content)

        if not frontmatter:
            print(f"Warning: {file_path} missing YAML frontmatter (must start with ---)", file=sys.stderr)
            return None

        rule = Rule.from_dict(frontmatter, message, source=source, source_path=file_path)
        return rule

    except (IOError, OSError, PermissionError) as e:
        print(f"Error: Cannot read {file_path}: {e}", file=sys.stderr)
        return None
    except (ValueError, KeyError, AttributeError, TypeError) as e:
        print(f"Error: Malformed rule file {file_path}: {e}", file=sys.stderr)
        return None
    except UnicodeDecodeError as e:
        print(f"Error: Invalid encoding in {file_path}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error: Unexpected error parsing {file_path} ({type(e).__name__}): {e}", file=sys.stderr)
        return None


def list_all_rules() -> Dict[str, List[Rule]]:
    """List all rules organized by source.

    Returns:
        Dict with 'user' and 'project' keys containing lists of rules.
    """
    result = {
        SOURCE_USER: [],
        SOURCE_PROJECT: []
    }

    # Load user-level rules
    user_dir = get_user_rules_dir()
    if user_dir:
        result[SOURCE_USER] = _load_rules_from_dir(user_dir, SOURCE_USER)

    # Load project-level rules
    project_dir = get_project_rules_dir()
    if project_dir:
        result[SOURCE_PROJECT] = _load_rules_from_dir(project_dir, SOURCE_PROJECT)

    return result


# For testing
if __name__ == '__main__':
    import sys

    # Test frontmatter parsing
    test_content = """---
name: test-rule
enabled: true
event: bash
pattern: "rm -rf"
---

Dangerous command detected!
"""

    fm, msg = extract_frontmatter(test_content)
    print("Frontmatter:", fm)
    print("Message:", msg)

    rule = Rule.from_dict(fm, msg)
    print("Rule:", rule)

    # Test loading rules from both locations
    print("\n--- Loading rules from all locations ---")
    all_rules = list_all_rules()
    print(f"User rules: {len(all_rules[SOURCE_USER])}")
    for r in all_rules[SOURCE_USER]:
        print(f"  - {r.name} ({r.source_path})")
    print(f"Project rules: {len(all_rules[SOURCE_PROJECT])}")
    for r in all_rules[SOURCE_PROJECT]:
        print(f"  - {r.name} ({r.source_path})")
