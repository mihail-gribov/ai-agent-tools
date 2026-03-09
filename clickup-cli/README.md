# clickup-cli

ClickUp CLI for AI agents. JSON output by default, no interactive prompts, clean structured commands.

Part of the [Universal CLI API](../API.md) for project trackers.

## Concept Mapping

| CLI Term | ClickUp Entity | API Path |
|----------|---------------|----------|
| workspace | Workspace (Team in v2) | `/team` |
| project | Space | `/team/{id}/space` |
| section | List | `/space/{id}/list`, `/folder/{id}/list` |
| folder | Folder (ClickUp-specific) | `/space/{id}/folder` |
| task | Task | `/list/{id}/task`, `/task/{id}` |
| subtask | Task with parent | `/list/{id}/task` with `parent` |
| comment | Comment | `/task/{id}/comment` |
| tag | Tag | `/space/{id}/tag` |
| custom-field | Custom Field | `/list/{id}/field`, `/task/{id}/field/{fid}` |

## Development

```bash
uv sync              # install dependencies
uv run pytest -v     # run tests
```

## Environment

| Variable | Flag | Description |
|----------|------|-------------|
| `CLICKUP_TOKEN` | `--token` | ClickUp API token (personal: `pk_...`) **(required)** |
| `CLICKUP_WORKSPACE` | `--workspace` | Workspace (team) ID |
| `CLICKUP_PROJECT` | | Default project (space) ID (used by `task next`, `comment check`, tags) |

CLI flags take priority over environment variables.

## Global Flags

| Flag | Description |
|------|-------------|
| `--token TEXT` | ClickUp API token |
| `--workspace TEXT` | Workspace (team) ID |
| `--pretty` | Pretty-print JSON output |
| `--fields TEXT` | Fields filter (reserved, client-side) |
| `--no-paginate` | Disable auto-pagination |

Global flags go **before** the subcommand: `ait-clickup --pretty task list --section <id>`

## Output

- **Success**: raw ClickUp JSON objects to stdout, exit code `0`
- **Error**: `{"error": "..."}` to stdout, exit code `1`
- Compact JSON by default, `--pretty` for indented

## Commands

### config

```bash
ait-clickup config show
```

### workspace

```bash
ait-clickup workspace list
```

### project (ClickUp Space)

```bash
ait-clickup project list [--archived]
ait-clickup project create --name "My Space" [--color "#7B68EE"] [--public]
ait-clickup project get <id>
```

### section (ClickUp List)

```bash
ait-clickup section list --project <id>      # all lists: folderless + inside folders
ait-clickup section create --project <id> --name "Sprint 1" [--folder <id>]
ait-clickup section get <id>
```

### folder (ClickUp-specific)

```bash
ait-clickup folder list --project <id> [--archived]
ait-clickup folder create --project <id> --name "Q1"
ait-clickup folder get <id>
```

### task list

```bash
ait-clickup task list --section <id>         # tasks in list
ait-clickup task list --project <id>         # tasks across space
ait-clickup task list --assignee <id>
```

| Flag | Description |
|------|-------------|
| `--project TEXT` | Project (space) ID |
| `--section TEXT` | Section (list) ID |
| `--assignee TEXT` | User ID |
| `--completed` | Include closed tasks |
| `--limit INT` | Max results |

### task search

```bash
ait-clickup task search --status "to do"
ait-clickup task search --text "bug"                        # client-side name filter
ait-clickup task search --assignee <id> --due-before 2026-04-01
ait-clickup task search --custom-field <field_id>=<value>
```

| Flag | Description |
|------|-------------|
| `--text TEXT` | Filter by task name (client-side) |
| `--assignee TEXT` | User ID |
| `--project TEXT` | Project (space) ID |
| `--section TEXT` | Section (list) ID |
| `--tag TEXT` | Tag name |
| `--status TEXT` | Status name (native ClickUp status) |
| `--completed` | Include closed tasks |
| `--due-before TEXT` | Due date before (`YYYY-MM-DD`) |
| `--due-after TEXT` | Due date after (`YYYY-MM-DD`) |
| `--modified-after TEXT` | Modified after (`YYYY-MM-DD`) |
| `--sort-by` | `due_date`, `created`, or `updated` |
| `--custom-field TEXT` | Filter: `field_id=value` (repeatable, JSON operator `=`) |

### task get

```bash
ait-clickup task get <id>                    # full task details (includes subtasks)
ait-clickup task get <id> --history          # accepted but no-op (ClickUp has no story stream)
```

### task create

```bash
ait-clickup task create --name "Fix bug" --section <id>
ait-clickup task create --name "Subtask" --parent <id>
ait-clickup task create --name "Task" --section <id> --status "in progress" --assignee <id>
```

| Flag | Description |
|------|-------------|
| `--name TEXT` | Task name **(required)** |
| `--notes TEXT` | Description in Markdown (use `-` for stdin) |
| `--assignee TEXT` | User ID |
| `--project TEXT` | Project (space) ID (informational; `--section` is required) |
| `--section TEXT` | Section (list) ID **(required unless `--parent`)** |
| `--parent TEXT` | Parent task ID (creates subtask) |
| `--due-on TEXT` | Due date (`YYYY-MM-DD`) |
| `--start-on TEXT` | Start date (`YYYY-MM-DD`) |
| `--tags TEXT` | Comma-separated tag names |
| `--status TEXT` | Task status name |
| `--custom-field TEXT` | `field_id=value` (repeatable) |

### task update

```bash
ait-clickup task update <id> --name "New name"
ait-clickup task update <id> --status "in progress"
ait-clickup task update <id> --completed
ait-clickup task update <id> --custom-field <field_id>=<value>
```

| Flag | Description |
|------|-------------|
| `--name TEXT` | New name |
| `--notes TEXT` | New description (use `-` for stdin) |
| `--assignee TEXT` | User ID |
| `--due-on TEXT` | Due date (`YYYY-MM-DD`) |
| `--start-on TEXT` | Start date (`YYYY-MM-DD`) |
| `--completed / --no-completed` | Set status to closed / open |
| `--status TEXT` | Status name |
| `--custom-field TEXT` | `field_id=value` (repeatable, separate API calls) |
| `--archive-notes` | Save current description as comment before replacing |

### task complete / delete

```bash
ait-clickup task complete <id>               # sets status to "complete"
ait-clickup task delete <id>
```

### task subtasks

```bash
ait-clickup task subtasks <id>               # list subtasks from task detail
```

### task organization

```bash
ait-clickup task add-project <id> --project <id> --section <id>   # move to list
ait-clickup task remove-project <id> --project <id>               # not supported (error)
ait-clickup task move <id> --section <id>                         # move to list
```

### task next

```bash
ait-clickup task next                        # find next "to do" unblocked task
ait-clickup task next --project <id>
ait-clickup task next --status "new"
ait-clickup task next --assignee <id>
```

Returns first matching task or `null`.

### task dependencies / dependents

```bash
ait-clickup task dependencies <id>
ait-clickup task dependents <id>

ait-clickup task add-dependency <id> --dependency <other_id>
ait-clickup task remove-dependency <id> --dependency <other_id>

ait-clickup task add-dependent <id> --dependent <other_id>
ait-clickup task remove-dependent <id> --dependent <other_id>
```

### comment

```bash
ait-clickup comment list <task_id>
ait-clickup comment add <task_id> --text "Done"
echo "Multiline" | ait-clickup comment add <task_id> --text -
```

### comment check

```bash
ait-clickup comment check                    # status "need info"
ait-clickup comment check --status "blocked"
```

### tag

```bash
ait-clickup tag list [--project <id>]
ait-clickup tag create --name "urgent" [--color "#FF0000"] [--project <id>]
ait-clickup tag get <name> [--project <id>]  # ClickUp tags are identified by name
```

### custom-field

```bash
ait-clickup custom-field get <field_id> --section <list_id>
ait-clickup custom-field list-options <field_id> --section <list_id>
ait-clickup custom-field set <task_id> --field <field_id> --value <value>
ait-clickup custom-field remove <task_id> --field <field_id>
```

Note: ClickUp API does not support creating or modifying custom field definitions or dropdown options. `add-option` and `update-option` are not available — manage field definitions in the ClickUp UI.

## ClickUp-Specific Details

- **Status** is a native task property, not a custom field. `--status` passes directly to the API.
- **Rich text**: `--notes` sends Markdown via `markdown_description` (no conversion needed).
- **Pagination**: page-based (zero-indexed), 100 tasks per page.
- **Rate limit**: 100 req/min (free plan), 429 + `X-RateLimit-Reset` Unix timestamp.
- **Auth**: Personal token (`pk_...`) in `Authorization` header (no `Bearer` prefix).
- **Dates**: `YYYY-MM-DD` in CLI flags, converted to Unix ms for the API.
- **Task IDs**: strings (e.g. `"9hz"`), not integers.
- **Hierarchy**: Workspace → Space → Folder (optional) → List → Task.
- **Custom fields on update**: require separate API calls (`POST /task/{id}/field/{field_id}`), handled automatically by `--custom-field`.
- **`team_id`** in ClickUp v2 API = workspace ID.

## Examples

```bash
# Full CRUD cycle
ait-clickup task create --name "Test" --section 12345 --status "to do"
ait-clickup task get abc123
ait-clickup task update abc123 --status "in progress" --assignee 67890
ait-clickup task complete abc123
ait-clickup task delete abc123

# Search
ait-clickup task search --status "to do" --project 11111
ait-clickup task search --text "deploy" --sort-by due_date

# Dependencies
ait-clickup task add-dependency abc123 --dependency def456

# Pipe multiline notes
cat notes.md | ait-clickup task create --name "With notes" --section 12345 --notes -

# Custom fields
ait-clickup custom-field set abc123 --field cf_uuid --value "option_uuid"

# Folders (ClickUp-specific)
ait-clickup folder list --project 11111
ait-clickup folder create --project 11111 --name "Sprint 3"
ait-clickup section create --project 11111 --name "Tasks" --folder 22222
```
