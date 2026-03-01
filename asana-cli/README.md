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

Global flags go **before** the subcommand: `asana --pretty task list --project <gid>`

## Output

- **Success**: raw Asana JSON objects to stdout, exit code `0`
- **Error**: `{"error": "..."}` to stdout, exit code `1`
- Compact JSON by default, `--pretty` for indented

## Commands

### config

```bash
asana config show                        # show internal config (field cache)
```

### workspace

```bash
asana workspace list                     # list accessible workspaces
```

### project

```bash
asana project list [--archived]          # list projects in workspace
asana project get <gid>                  # project details
```

| Flag | Description |
|------|-------------|
| `--archived` | Include archived projects |

### section

```bash
asana section list --project <gid>       # list sections in a project
asana section get <gid>                  # section details
```

### task list

```bash
asana task list --project <gid>          # list tasks in project
asana task list --section <gid>          # list tasks in section
asana task list --assignee me            # list tasks assigned to me
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
asana task search --text "bug"
asana task search --assignee me --completed
asana task search --project <gid> --due-before 2026-04-01
asana task search --custom-field 111111=AAA           # filter by custom field (e.g. status)
asana task search --section <gid>                     # filter by section
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
asana task get <gid>                     # full task details
```

### task create

```bash
asana task create --name "Fix login bug" --project <gid>
asana task create --name "Subtask" --parent <gid>
asana task create --name "Task" --project <gid> --section <gid> --assignee me --due-on 2026-03-15
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
asana task update <gid> --name "New name"
asana task update <gid> --assignee me --due-on 2026-04-01
asana task update <gid> --completed
asana task update <gid> --custom-field 12345=High --custom-field 67890=42
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
asana task complete <gid>                # shortcut for marking complete
```

### task delete

```bash
asana task delete <gid>
```

### task subtasks

```bash
asana task subtasks <gid>               # list subtasks of a task
```

### task add-project

```bash
asana task add-project <gid> --project <gid>
asana task add-project <gid> --project <gid> --section <gid>
```

### task remove-project

```bash
asana task remove-project <gid> --project <gid>
```

### task move

```bash
asana task move <gid> --section <gid>   # move task to a section
```

### task next

Find the next actionable task: status = "New" and not blocked by any incomplete dependency.

```bash
asana task next                          # find next "New" unblocked task
asana task next --project <gid>          # override project
asana task next --status "Planning"      # look for a different status
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
asana task dependencies <gid>                       # list tasks this task is waiting on
asana task dependents <gid>                         # list tasks blocked by this task

asana task add-dependency <gid> --dependency <gid>  # this task waits on another
asana task remove-dependency <gid> --dependency <gid>

asana task add-dependent <gid> --dependent <gid>    # another task is blocked by this one
asana task remove-dependent <gid> --dependent <gid>
```

Example — task B is blocked by task A:

```bash
# Either direction works, same result:
asana task add-dependency B --dependency A   # B waits on A
asana task add-dependent A --dependent B     # A blocks B
```

### comment

```bash
asana comment list <task_gid>            # list comments on a task
asana comment add <task_gid> --text "Looks good"
echo "Multiline note" | asana comment add <task_gid> --text -
```

| Flag | Description |
|------|-------------|
| `--text TEXT` | Comment text **(required)**, use `-` for stdin |

### comment check

Find tasks that need a comment response from the agent. Searches the configured
project for tasks with a given status and returns those where the last comment
is not from the current user.

```bash
asana comment check                          # tasks with status "Need info"
asana comment check --status "Planning"      # use a different status
```

| Flag | Description |
|------|-------------|
| `--status TEXT` | Status to filter tasks by (default: `Need info`) |

Returns a JSON list of `{"task": {...}, "comment": {...}}` objects, or `[]` if
there is nothing to respond to. Uses the project from config
(`asana config set --project <gid>`).

### tag

```bash
asana tag list                           # list tags in workspace
asana tag get <gid>                      # tag details
```

## Examples

```bash
# Full CRUD cycle
asana task create --name "Test" --project 123456
asana task get 789012
asana task update 789012 --assignee me --due-on 2026-03-15
asana task complete 789012
asana task delete 789012

# Search and filter
asana task search --text "deploy" --sort-by due_date
asana task list --assignee me --completed

# Organization
asana task move 789012 --section 345678
asana task add-project 789012 --project 111111 --section 222222

# Dependencies
asana task add-dependency 789012 --dependency 111111  # 789012 waits on 111111
asana task dependencies 789012                        # list what 789012 waits on
asana task dependents 111111                          # list what 111111 blocks

# Pipe multiline notes
cat notes.md | asana task create --name "With notes" --project 123456 --notes -

# Check for comments needing a response
asana comment check                          # "Need info" tasks with unresponded comments
asana comment check --status "Planning"      # same, but for "Planning" status
```
