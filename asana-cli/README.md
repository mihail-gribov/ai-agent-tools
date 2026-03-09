# asana-cli

Asana CLI for AI agents. JSON output by default, no interactive prompts, clean structured commands.

Part of the [Universal CLI API](../API.md) for project trackers.

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
| `ASANA_PROJECT` | | Default project GID (used by `task next`, `comment check`, `--status` resolution) |

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
ait-asana project create --name "My Project" [--color light-green] [--layout board] [--public]
ait-asana project get <gid>                  # project details
```

### section

```bash
ait-asana section list --project <gid>       # list sections in a project
ait-asana section create --project <gid> --name "Backlog"
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
ait-asana task search --status "New" --project <gid>
ait-asana task search --assignee me --completed
ait-asana task search --project <gid> --due-before 2026-04-01
ait-asana task search --custom-field 111111=AAA
ait-asana task search --section <gid>
```

| Flag | Description |
|------|-------------|
| `--text TEXT` | Full-text search query |
| `--assignee TEXT` | Assignee GID or `me` |
| `--project TEXT` | Project GID |
| `--section TEXT` | Section GID |
| `--tag TEXT` | Tag GID |
| `--status TEXT` | Status name (auto-resolves to custom field filter) |
| `--completed` | Include completed tasks |
| `--due-before TEXT` | Due date before (`YYYY-MM-DD`) |
| `--due-after TEXT` | Due date after (`YYYY-MM-DD`) |
| `--modified-after TEXT` | Modified after (ISO datetime) |
| `--sort-by` | `due_date`, `created_at`, `completed_at`, or `modified_at` |
| `--custom-field TEXT` | Filter by custom field: `gid=value` (repeatable). For enum fields use the option GID as value. |

### task get

```bash
ait-asana task get <gid>                     # full task details
ait-asana task get <gid> --history           # include status change history
```

`--history` fetches task stories and extracts status transitions as `status_history` array:
```json
[{"from": "New", "to": "In progress", "at": "2026-03-09T...", "by": "12345"}]
```

### task create

```bash
ait-asana task create --name "Fix bug" --project <gid>
ait-asana task create --name "Subtask" --parent <gid>
ait-asana task create --name "Task" --project <gid> --section <gid> --status "New" --assignee me
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
| `--status TEXT` | Status name (auto-resolves to custom field enum value) |
| `--custom-field TEXT` | `gid=value` pair (repeatable) |

### task update

```bash
ait-asana task update <gid> --name "New name"
ait-asana task update <gid> --status "In progress"
ait-asana task update <gid> --assignee me --due-on 2026-04-01
ait-asana task update <gid> --completed
ait-asana task update <gid> --custom-field 12345=High
```

| Flag | Description |
|------|-------------|
| `--name TEXT` | New name |
| `--notes TEXT` | New description (use `-` for stdin) |
| `--assignee TEXT` | Assignee GID or `me` |
| `--due-on TEXT` | Due date (`YYYY-MM-DD`) |
| `--start-on TEXT` | Start date (`YYYY-MM-DD`) |
| `--completed / --no-completed` | Mark completed or incomplete |
| `--status TEXT` | Status name (auto-resolves to custom field) |
| `--custom-field TEXT` | `gid=value` pair (repeatable) |
| `--archive-notes` | Save current description as comment before replacing |

### task complete / delete

```bash
ait-asana task complete <gid>
ait-asana task delete <gid>
```

### task subtasks

```bash
ait-asana task subtasks <gid>
```

### task organization

```bash
ait-asana task add-project <gid> --project <gid> [--section <gid>]
ait-asana task remove-project <gid> --project <gid>
ait-asana task move <gid> --section <gid>
```

### task next

Find the next actionable task: matching status, not blocked by incomplete dependencies.

```bash
ait-asana task next                          # find next "New" unblocked task
ait-asana task next --project <gid>
ait-asana task next --status "Planning"
ait-asana task next --assignee me
```

Auto-discovers the status custom field from the project (by name "Status"/"Статус") and caches it in `~/.config/asana-cli/config.json`. Returns first matching task or `null`.

### task dependencies / dependents

```bash
ait-asana task dependencies <gid>                       # tasks this task waits on
ait-asana task dependents <gid>                         # tasks blocked by this task

ait-asana task add-dependency <gid> --dependency <gid>
ait-asana task remove-dependency <gid> --dependency <gid>

ait-asana task add-dependent <gid> --dependent <gid>
ait-asana task remove-dependent <gid> --dependent <gid>
```

### comment

```bash
ait-asana comment list <task_gid>
ait-asana comment add <task_gid> --text "Looks good"
echo "Multiline" | ait-asana comment add <task_gid> --text -
```

### comment check

Find tasks needing a comment response (status filter + last comment not from current user).

```bash
ait-asana comment check                          # status "Need info"
ait-asana comment check --status "Planning"
```

Returns `[{"task": {...}, "comment": {...}}]` or `[]`. Uses `ASANA_PROJECT`.

### tag

```bash
ait-asana tag list
ait-asana tag create --name "urgent" [--color dark-red]
ait-asana tag get <gid>
```

### custom-field

```bash
ait-asana custom-field get <gid>                                # field details + options
ait-asana custom-field list-options <gid>                       # enum options only
ait-asana custom-field set <task_gid> --field <gid> --value <v> # set value on task
ait-asana custom-field remove <task_gid> --field <gid>          # clear value (set null)
ait-asana custom-field add-option <gid> --name "New" [--color cool-gray]
ait-asana custom-field update-option <option_gid> [--name X] [--color X] [--enabled/--disabled]
```

## Asana-Specific Details

- **Status** is a custom field enum, not a native concept. The `--status` flag auto-discovers and resolves it.
- **Rich text**: `--notes` and `--text` convert Markdown to Asana HTML internally.
- **Pagination**: offset-based, handled by `get_all()`.
- **Rate limit**: 429 + `Retry-After` header, up to 3 retries.
- **Auth**: Bearer token (Personal Access Token).
- **Config cache**: `~/.config/asana-cli/config.json` stores discovered custom field mappings per project.

## Examples

```bash
# Full CRUD cycle
ait-asana task create --name "Test" --project 123456 --status "New"
ait-asana task get 789012
ait-asana task update 789012 --status "In progress" --assignee me
ait-asana task complete 789012
ait-asana task delete 789012

# Search and filter
ait-asana task search --text "deploy" --sort-by due_date
ait-asana task search --status "New" --project 123456

# Dependencies
ait-asana task add-dependency 789012 --dependency 111111

# Pipe multiline notes
cat notes.md | ait-asana task create --name "With notes" --project 123456 --notes -

# Custom fields
ait-asana custom-field set 789012 --field 12345 --value 67890
```
