# ai-agent-tools

CLI tools that let AI agents work in the same services as your team — project trackers, messengers, and more. Make human-agent collaboration seamless to scale your team without changing existing workflows.

All project tracker CLIs share a [Universal CLI API](API.md) — same commands, same flags, same JSON output. Agents switch backends by changing environment variables, not code.

## Tools

| Tool | Description |
|------|-------------|
| [asana-cli](asana-cli/) | Manage Asana tasks, track statuses, and respond to comments |
| [clickup-cli](clickup-cli/) | Manage ClickUp tasks, track statuses, and respond to comments |

See [API.md](API.md) for the unified command reference.

## Install

```bash
curl -sSL https://raw.githubusercontent.com/mihail-gribov/ai-agent-tools/main/install.sh | bash
```

Requires [git](https://git-scm.com/) and [uv](https://docs.astral.sh/uv/).

Verify:

```bash
ait-asana --version
ait-clickup --version
```

## Uninstall

```bash
uv tool uninstall asana-cli
uv tool uninstall clickup-cli
rm -rf ~/.ai-agent-tools
```

## License

Apache 2.0 — see [LICENSE](LICENSE). Attribution is required.
