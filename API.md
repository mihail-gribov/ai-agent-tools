# Universal CLI API for Project Trackers

A unified set of CLI commands that work identically across different project management systems. AI agents use the same commands regardless of the backend — only the environment variables change.

## Supported Backends

| Backend | CLI Binary | Token Env Var | Workspace Env Var | Project Env Var |
|---------|-----------|---------------|-------------------|-----------------|
| Asana | `ait-asana` | `ASANA_TOKEN` | `ASANA_WORKSPACE` | `ASANA_PROJECT` |
| ClickUp | `ait-clickup` | `CLICKUP_TOKEN` | `CLICKUP_WORKSPACE` | `CLICKUP_PROJECT` |

## Concept Mapping

The CLI normalizes different systems into a shared hierarchy:

| Universal Term | Asana | ClickUp |
|----------------|-------|---------|
| **workspace** | Workspace | Workspace (Team in v2 API) |
| **project** | Project | Space |
| **section** | Section | List |
| **task** | Task | Task |
| **subtask** | Task with parent | Task with parent |
| **comment** | Story (type=comment) | Comment |
| **tag** | Tag | Tag |
| **custom-field** | Custom Field | Custom Field |

ClickUp has an extra organizational layer — **folder** (groups lists inside a space). This is available via `ait-clickup folder` commands.

## Global Flags

All flags go **before** the subcommand.

| Flag | Description |
|------|-------------|
| `--token TEXT` | API token (overrides env var) |
| `--workspace TEXT` | Workspace ID (overrides env var) |
| `--pretty` | Pretty-print JSON output |
| `--fields TEXT` | Limit returned fields (Asana: `opt_fields`, ClickUp: client-side filter) |
| `--no-paginate` | Disable auto-pagination (single page) |

## Output Format

- **Success**: JSON to stdout, exit code `0`
- **Error**: `{"error": "..."}` to stdout, exit code `1`
- Compact JSON by default; `--pretty` for indented

## Commands

### config

```
config show                             # show internal config cache
```

### workspace

```
workspace list                          # list accessible workspaces
```

### project

```
project list [--archived]               # list projects in workspace
project create --name TEXT [--color TEXT] [--layout board|list] [--public]
project get <id>                        # project details
```

### section

```
section list --project <id>             # list sections in a project
section create --project <id> --name TEXT
section get <id>                        # section details
```

### tag

```
tag list                                # list tags
tag create --name TEXT [--color TEXT]
tag get <id>                            # tag details
```

### task list

```
task list --project <id>                # tasks in project
task list --section <id>                # tasks in section
task list --assignee <id>               # tasks assigned to user
```

| Flag | Description |
|------|-------------|
| `--project TEXT` | Project ID |
| `--section TEXT` | Section ID |
| `--assignee TEXT` | User ID (Asana: GID or `me`) |
| `--completed` | Include completed tasks |
| `--limit INT` | Max results |

### task search

```
task search --text "bug"
task search --status "New" --project <id>
task search --assignee <id> --due-before 2026-04-01
task search --custom-field <field_id>=<value>
```

| Flag | Description |
|------|-------------|
| `--text TEXT` | Full-text search (Asana: server-side; ClickUp: client-side name filter) |
| `--assignee TEXT` | User ID |
| `--project TEXT` | Project ID |
| `--section TEXT` | Section ID |
| `--tag TEXT` | Tag ID/name |
| `--status TEXT` | Status name (Asana: auto-resolved to custom field; ClickUp: native status) |
| `--completed` | Include completed tasks |
| `--due-before TEXT` | Due date before (`YYYY-MM-DD`) |
| `--due-after TEXT` | Due date after (`YYYY-MM-DD`) |
| `--modified-after TEXT` | Modified after (ISO datetime / `YYYY-MM-DD`) |
| `--sort-by TEXT` | Sort field |
| `--custom-field TEXT` | Filter: `field_id=value` (repeatable) |

### task get

```
task get <id>                           # full task details
task get <id> --history                 # include status change history (Asana only)
```

### task create

```
task create --name "Fix bug" --section <id>
task create --name "Subtask" --parent <id>
task create --name "Task" --project <id> --status "New" --assignee <id>
```

| Flag | Description |
|------|-------------|
| `--name TEXT` | Task name **(required)** |
| `--notes TEXT` | Description (use `-` for stdin) |
| `--assignee TEXT` | User ID |
| `--project TEXT` | Project ID |
| `--section TEXT` | Section ID (ClickUp: required unless `--parent`) |
| `--parent TEXT` | Parent task ID (creates subtask) |
| `--due-on TEXT` | Due date (`YYYY-MM-DD`) |
| `--start-on TEXT` | Start date (`YYYY-MM-DD`) |
| `--tags TEXT` | Comma-separated tag IDs/names |
| `--status TEXT` | Status name |
| `--custom-field TEXT` | `field_id=value` (repeatable) |

### task update

```
task update <id> --name "New name"
task update <id> --status "In progress"
task update <id> --completed
task update <id> --custom-field <field_id>=<value>
```

| Flag | Description |
|------|-------------|
| `--name TEXT` | New name |
| `--notes TEXT` | New description (use `-` for stdin) |
| `--assignee TEXT` | User ID |
| `--due-on TEXT` | Due date (`YYYY-MM-DD`) |
| `--start-on TEXT` | Start date (`YYYY-MM-DD`) |
| `--completed / --no-completed` | Mark completed or incomplete |
| `--status TEXT` | Status name |
| `--custom-field TEXT` | `field_id=value` (repeatable) |
| `--archive-notes` | Save current description as comment before replacing |

### task complete

```
task complete <id>                      # shortcut for marking complete
```

### task delete

```
task delete <id>
```

### task subtasks

```
task subtasks <id>                      # list subtasks of a task
```

### task add-project / remove-project

```
task add-project <id> --project <id> [--section <id>]
task remove-project <id> --project <id>
```

### task move

```
task move <id> --section <id>           # move task to a section
```

### task next

Find the next actionable task: matching status, not blocked by incomplete dependencies.

```
task next                               # find next unblocked task (default status)
task next --project <id>                # in specific project
task next --status "Planning"           # look for a different status
task next --assignee <id>               # filter by assignee
```

Returns the first matching task as JSON, or `null` if nothing is actionable.

### Dependencies

Two sides of the same relationship:
- **dependency** = this task is **waiting on** another
- **dependent** = another task is **blocked by** this one

```
task dependencies <id>                              # list what this task waits on
task dependents <id>                                # list what this task blocks

task add-dependency <id> --dependency <other_id>    # this task waits on other
task remove-dependency <id> --dependency <other_id>

task add-dependent <id> --dependent <other_id>      # other task is blocked by this
task remove-dependent <id> --dependent <other_id>
```

### comment

```
comment list <task_id>                  # list comments on a task
comment add <task_id> --text "Done"     # add a comment
comment add <task_id> --text -          # read from stdin
```

### comment check

Find tasks needing a comment response (status filter + last comment not from current user).

```
comment check                           # default status: "Need info" / "need info"
comment check --status "Planning"
```

### custom-field

```
custom-field get <field_id>             # field details with options
custom-field list-options <field_id>    # list enum/dropdown options
custom-field set <task_id> --field <field_id> --value <value>
custom-field remove <task_id> --field <field_id>
```

Asana-only (ClickUp API does not support field definition management):

```
custom-field add-option <field_id> --name TEXT [--color TEXT]
custom-field update-option <option_id> [--name TEXT] [--color TEXT] [--enabled/--disabled]
```

## Backend-Specific Differences

| Feature | Asana | ClickUp |
|---------|-------|---------|
| Status | Custom field enum (auto-discovered by name "Status"/"Статус") | Native task status |
| `--status` on task commands | Resolves to custom field GID internally | Passes directly to API |
| Text search | Server-side | Client-side name filter |
| `--history` on task get | Parses status transitions from stories | Not supported |
| Rich text | Markdown → Asana HTML conversion | Markdown sent directly |
| Dates | `YYYY-MM-DD` strings | Unix ms internally, `YYYY-MM-DD` in CLI |
| Pagination | Offset-based | Page-based (zero-indexed) |
| Rate limiting | 429 + `Retry-After` header | 429 + `X-RateLimit-Reset` timestamp |
| Custom field definitions | Full CRUD via API | Read-only (manage in UI) |
| `custom-field get/list-options` | Direct by field GID | Requires `--section` (list ID) |
| `folder` commands | N/A | ClickUp-specific (groups lists in a space) |
| `task remove-project` | Supported | Not supported (tasks must belong to a list) |

## Quick Start

```bash
# Asana
export ASANA_TOKEN=<pat>
export ASANA_WORKSPACE=<gid>
export ASANA_PROJECT=<gid>
ait-asana task search --status "New"

# ClickUp
export CLICKUP_TOKEN=pk_...
export CLICKUP_WORKSPACE=<team_id>
export CLICKUP_PROJECT=<space_id>
ait-clickup task search --status "to do"

# Same workflow, any backend:
$TRACKER task create --name "Fix bug" --section $SECTION_ID --status "New"
$TRACKER task update $TASK_ID --status "In progress"
$TRACKER comment add $TASK_ID --text "Working on it"
$TRACKER task complete $TASK_ID
```
