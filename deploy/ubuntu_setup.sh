#!/usr/bin/env bash
set -euo pipefail

# Run as a regular user with sudo on Ubuntu 24.04 or newer.
sudo apt-get update
sudo apt-get install -y git curl ca-certificates python3 python3-venv tmux
python3 -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ required"'
if ! command -v npm >/dev/null || ! node -e 'process.exit(+process.versions.node.split(".")[0] < 22)'; then
    curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi
npm install --global --prefix "$HOME/.local" @anthropic-ai/claude-code @openai/codex @google/gemini-cli
export PATH="$HOME/.local/bin:$PATH"

repo="$HOME/hidden-senses-lab"
if [[ ! -d "$repo/.git" ]]; then
    git clone https://github.com/Chulabush/hidden-senses-lab "$repo"
else
    git -C "$repo" pull --ff-only origin main
fi
mkdir -p "$repo/runs"
if ! tmux has-session -t '=hidden-senses-lab' 2>/dev/null; then
    tmux new-session -d -s hidden-senses-lab -c "$repo" -e "PATH=$PATH" \
        'python3 -m lab --config lab.cli.toml doctor --ping && python3 -m lab --config lab.cli.toml scout --count 1000 --concurrency 25 --promote-top 10; echo "Exit: $?"; exec bash'
fi
echo 'Inspect progress with tmux attach -t hidden-senses-lab.'
