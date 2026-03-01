# ai-agent-tools

CLI tools that let AI agents work in the same services as your team — project trackers, messengers, and more. Make human-agent collaboration seamless to scale your team without changing existing workflows.

## Tools

| Tool | Description |
|------|-------------|
| [asana-cli](asana-cli/) | Manage Asana tasks, track statuses, and respond to comments — all as JSON |

## Install

Install all tools:

```bash
curl -sSL https://raw.githubusercontent.com/mihail-gribov/ai-agent-tools/main/install.sh | bash
```

Or pick specific tools:

```bash
curl -sSL https://raw.githubusercontent.com/mihail-gribov/ai-agent-tools/main/install.sh | bash -s -- asana-cli
```

Requires [git](https://git-scm.com/) and [uv](https://docs.astral.sh/uv/).

## License

Apache 2.0 — see [LICENSE](LICENSE). Attribution is required.
