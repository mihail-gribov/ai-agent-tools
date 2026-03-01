# asana-cli

Asana CLI for AI agents. JSON output by default, no interactive prompts, clean structured commands.

## Development

```bash
uv sync              # install dependencies
uv run pytest -v     # run tests
```

## Environment

All credentials and project context come from environment variables or CLI flags (not from the config file):

| Variable | Flag | Description |
|----------|------|-------------|
| `ASANA_TOKEN` | `--token` | Asana Personal Access Token **(required)** |
| `ASANA_WORKSPACE` | `--workspace` | Workspace GID |
| `ASANA_PROJECT` | | Default project GID (used by `task next`, `comment check`) |

CLI flags take priority over environment variables.

## Global Flags

| Flag | Description |
|------|-------------|
| `--token TEXT` | Asana Personal Access Token |
| `--workspace TEXT` | Workspace GID (overrides saved default) |
| `--pretty` | Pretty-print JSON output (indented) |
| `--fields TEXT` | Comma-separated `opt_fields` override |
| `--no-paginate` | Disable automatic pagination |

Global flags go **before** the subcommand: `ait-asana --pretty task list --project <gid>`

## Output

- **Success**: raw Asana JSON objects to stdout, exit code `0`
- **Error**: `{"error": "..."}` to stdout, exit code `1`
- Compact JSON by default, `--pretty` for indented

## Commands

### config

```bash
ait-asana config show                        # show internal config (field cache)
```

### workspace

```bash
ait-asana workspace list                     # list accessible workspaces
```

### project

```bash
ait-asana project list [--archived]          # list projects in workspace
ait-asana project get <gid>                  # project details
```

| Flag | Description |
|------|-------------|
| `--archived` | Include archived projects |

### section

```bash
ait-asana section list --project <gid>       # list sections in a project
ait-asana section get <gid>                  # section details
```

### task list

```bash
ait-asana task list --project <gid>          # list tasks in project
ait-asana task list --section <gid>          # list tasks in section
ait-asana task list --assignee me            # list tasks assigned to me
```

| Flag | Description |
|------|-------------|
| `--project TEXT` | Project GID |
| `--section TEXT` | Section GID |
| `--assignee TEXT` | Assignee GID or `me` |
| `--completed` | Include completed tasks |
| `--limit INT` | Max number of results |

### task search

```bash
ait-asana task search --text "bug"
ait-asana task search --assignee me --completed
ait-asana task search --project <gid> --due-before 2026-04-01
ait-asana task search --custom-field 111111=AAA           # filter by custom field (e.g. status)
ait-asana task search --section <gid>                     # filter by section
```

| Flag | Description |
|------|-------------|
| `--text TEXT` | Full-text search query |
| `--assignee TEXT` | Assignee GID or `me` |
| `--project TEXT` | Project GID |
| `--section TEXT` | Section GID |
| `--tag TEXT` | Tag GID |
| `--completed` | Include completed tasks |
| `--due-before TEXT` | Due date before (`YYYY-MM-DD`) |
| `--due-after TEXT` | Due date after (`YYYY-MM-DD`) |
| `--modified-after TEXT` | Modified after (ISO datetime) |
| `--sort-by` | `due_date`, `created_at`, `completed_at`, or `modified_at` |
| `--custom-field TEXT` | Filter by custom field: `gid=value` (repeatable). For enum fields use the option GID as value. |

### task get

```bash
ait-asana task get <gid>                     # full task details
```

### task create

```bash
ait-asana task create --name "Fix login bug" --project <gid>
ait-asana task create --name "Subtask" --parent <gid>
ait-asana task create --name "Task" --project <gid> --section <gid> --assignee me --due-on 2026-03-15
```

| Flag | Description |
|------|-------------|
| `--name TEXT` | Task name **(required)** |
| `--notes TEXT` | Task description (use `-` to read from stdin) |
| `--assignee TEXT` | Assignee GID or `me` |
| `--project TEXT` | Project GID |
| `--section TEXT` | Section GID |
| `--parent TEXT` | Parent task GID (creates subtask) |
| `--due-on TEXT` | Due date (`YYYY-MM-DD`) |
| `--start-on TEXT` | Start date (`YYYY-MM-DD`) |
| `--tags TEXT` | Comma-separated tag GIDs |
| `--custom-field TEXT` | `gid=value` pair (repeatable) |

### task update

```bash
ait-asana task update <gid> --name "New name"
ait-asana task update <gid> --assignee me --due-on 2026-04-01
ait-asana task update <gid> --completed
ait-asana task update <gid> --custom-field 12345=High --custom-field 67890=42
```

| Flag | Description |
|------|-------------|
| `--name TEXT` | New name |
| `--notes TEXT` | New description (use `-` for stdin) |
| `--assignee TEXT` | Assignee GID or `me` |
| `--due-on TEXT` | Due date (`YYYY-MM-DD`) |
| `--start-on TEXT` | Start date (`YYYY-MM-DD`) |
| `--completed / --no-completed` | Mark completed or incomplete |
| `--custom-field TEXT` | `gid=value` pair (repeatable) |

### task complete

```bash
ait-asana task complete <gid>                # shortcut for marking complete
```

### task delete

```bash
ait-asana task delete <gid>
```

### task subtasks

```bash
ait-asana task subtasks <gid>               # list subtasks of a task
```

### task add-project

```bash
ait-asana task add-project <gid> --project <gid>
ait-asana task add-project <gid> --project <gid> --section <gid>
```

### task remove-project

```bash
ait-asana task remove-project <gid> --project <gid>
```

### task move

```bash
ait-asana task move <gid> --section <gid>   # move task to a section
```

### task next

Find the next actionable task: status = "New" and not blocked by any incomplete dependency.

```bash
ait-asana task next                          # find next "New" unblocked task
ait-asana task next --project <gid>          # override project
ait-asana task next --status "Planning"      # look for a different status
```

Auto-discovers the status custom field from the project and caches it in
`~/.config/asana-cli/config.json` (per project, no manual GID setup needed).

Returns the first matching task as JSON, or `null` if nothing is actionable.
A dependency is considered resolved if the blocking task is completed in Asana.

### task dependencies / dependents

Two sides of the same relationship:
- **dependency** = this task is **waiting on** another task
- **dependent** = another task is **blocked by** this task

```bash
ait-asana task dependencies <gid>                       # list tasks this task is waiting on
ait-asana task dependents <gid>                         # list tasks blocked by this task

ait-asana task add-dependency <gid> --dependency <gid>  # this task waits on another
ait-asana task remove-dependency <gid> --dependency <gid>

ait-asana task add-dependent <gid> --dependent <gid>    # another task is blocked by this one
ait-asana task remove-dependent <gid> --dependent <gid>
```

Example — task B is blocked by task A:

```bash
# Either direction works, same result:
ait-asana task add-dependency B --dependency A   # B waits on A
ait-asana task add-dependent A --dependent B     # A blocks B
```

### comment

```bash
ait-asana comment list <task_gid>            # list comments on a task
ait-asana comment add <task_gid> --text "Looks good"
echo "Multiline note" | ait-asana comment add <task_gid> --text -
```

| Flag | Description |
|------|-------------|
| `--text TEXT` | Comment text **(required)**, use `-` for stdin |

### comment check

Find tasks that need a comment response from the agent. Searches the configured
project for tasks with a given status and returns those where the last comment
is not from the current user.

```bash
ait-asana comment check                          # tasks with status "Need info"
ait-asana comment check --status "Planning"      # use a different status
```

| Flag | Description |
|------|-------------|
| `--status TEXT` | Status to filter tasks by (default: `Need info`) |

Returns a JSON list of `{"task": {...}, "comment": {...}}` objects, or `[]` if
there is nothing to respond to. Uses the project from `ASANA_PROJECT` env var.

### tag

```bash
ait-asana tag list                           # list tags in workspace
ait-asana tag get <gid>                      # tag details
```

## Examples

```bash
# Full CRUD cycle
ait-asana task create --name "Test" --project 123456
ait-asana task get 789012
ait-asana task update 789012 --assignee me --due-on 2026-03-15
ait-asana task complete 789012
ait-asana task delete 789012

# Search and filter
ait-asana task search --text "deploy" --sort-by due_date
ait-asana task list --assignee me --completed

# Organization
ait-asana task move 789012 --section 345678
ait-asana task add-project 789012 --project 111111 --section 222222

# Dependencies
ait-asana task add-dependency 789012 --dependency 111111  # 789012 waits on 111111
ait-asana task dependencies 789012                        # list what 789012 waits on
ait-asana task dependents 111111                          # list what 111111 blocks

# Pipe multiline notes
cat notes.md | ait-asana task create --name "With notes" --project 123456 --notes -

# Check for comments needing a response
ait-asana comment check                          # "Need info" tasks with unresponded comments
ait-asana comment check --status "Planning"      # same, but for "Planning" status
```
