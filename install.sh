#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/mihail-gribov/ai-agent-tools.git"
RAW_URL="https://raw.githubusercontent.com/mihail-gribov/ai-agent-tools/main"
INSTALL_DIR="${AI_AGENT_TOOLS_DIR:-$HOME/.ai-agent-tools}"

# Fetch tools manifest (name + description)
fetch_tools() {
    curl -sSL "$RAW_URL/tools.txt"
}

tool_names() {
    fetch_tools | awk '{print $1}'
}

show_list() {
    echo "Available tools:"
    while IFS= read -r line; do
        local name="${line%%  *}"
        local desc="${line#*  }"
        echo "  $name — $desc"
    done < <(fetch_tools)
}

install_tool() {
    local tool="$1"
    echo "Installing $tool..."
    uv tool install --reinstall "$INSTALL_DIR/$tool"
    echo "Done: $tool"
}

# Clone repo with sparse checkout for selected tools
clone_sparse() {
    local tools=("$@")

    if [[ -d "$INSTALL_DIR/.git" ]]; then
        echo "Updating $INSTALL_DIR..."
        git -C "$INSTALL_DIR" sparse-checkout set "${tools[@]}"
        git -C "$INSTALL_DIR" pull --ff-only -q
    else
        echo "Cloning into $INSTALL_DIR..."
        git clone --filter=blob:none --no-checkout -q "$REPO_URL" "$INSTALL_DIR"
        git -C "$INSTALL_DIR" sparse-checkout init --cone
        git -C "$INSTALL_DIR" sparse-checkout set "${tools[@]}"
        git -C "$INSTALL_DIR" checkout -q
    fi
}

select_with_gum() {
    local tools=("$@")
    gum choose --no-limit --header "Select tools to install:" "${tools[@]}"
}

select_with_bash() {
    local tools=("$@")
    local selected=()

    echo "Select tools to install (space-separated numbers, or 'a' for all):"
    echo ""
    while IFS= read -r line; do
        local name="${line%%  *}"
        local desc="${line#*  }"
        echo "  $((${#selected[@]} + 1))) $name — $desc"
        selected+=("$name")
    done < <(fetch_tools)
    echo ""
    read -rp "> " choices

    if [[ "$choices" == "a" ]]; then
        echo "${selected[@]}"
        return
    fi

    local picked=()
    for num in $choices; do
        local idx=$((num - 1))
        if [[ $idx -ge 0 && $idx -lt ${#selected[@]} ]]; then
            picked+=("${selected[$idx]}")
        fi
    done
    echo "${picked[@]}"
}

interactive_select() {
    local names=($(tool_names))

    if [[ ${#names[@]} -eq 0 ]]; then
        echo "No tools found"
        exit 1
    fi

    local selected
    if command -v gum &>/dev/null; then
        selected=$(select_with_gum "${names[@]}")
    else
        selected=$(select_with_bash)
    fi

    if [[ -z "$selected" ]]; then
        echo "Nothing selected"
        exit 0
    fi

    local tools=($selected)
    clone_sparse "${tools[@]}"
    for tool in "${tools[@]}"; do
        install_tool "$tool"
    done
}

install_all() {
    local tools=($(tool_names))
    clone_sparse "${tools[@]}"
    for tool in "${tools[@]}"; do
        install_tool "$tool"
    done
}

# --- Main ---

case "${1:-}" in
    --help|-h)
        echo "Usage: install.sh [--list | tool1 tool2 ...]"
        echo ""
        echo "  No arguments    Install all (piped) or interactive select (local)"
        echo "  --list          List available tools"
        echo "  tool1 tool2     Install specific tools"
        ;;
    --list)
        show_list
        ;;
    "")
        if [[ -t 0 ]]; then
            interactive_select
        else
            install_all
        fi
        ;;
    *)
        clone_sparse "$@"
        for tool in "$@"; do
            install_tool "$tool"
        done
        ;;
esac
