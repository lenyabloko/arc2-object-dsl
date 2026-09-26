#!/usr/bin/env bash
# One-time setup in WSL (no sudo): GitHub CLI, public repo, clone, 5-minute sync timer.
set -euo pipefail
REPO_NAME="${1:-arc2-object-dsl}"
OUTBOX=/mnt/c/Users/lenya/arc_extended_arga/cloud_outbox
mkdir -p "$HOME/.local/bin" "$HOME/arc"
export PATH="$HOME/.local/bin:$PATH"
if ! command -v gh >/dev/null; then
  ver=$(curl -fsSL https://api.github.com/repos/cli/cli/releases/latest | python3 -c "import json,sys;print(json.load(sys.stdin)['tag_name'].lstrip('v'))")
  curl -fsSL "https://github.com/cli/cli/releases/download/v${ver}/gh_${ver}_linux_amd64.tar.gz" | tar -xz -C /tmp
  cp "/tmp/gh_${ver}_linux_amd64/bin/gh" "$HOME/.local/bin/gh"
fi
gh auth status >/dev/null 2>&1 || gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git
USER=$(gh api user -q .login)
[ -n "$(git config --global user.name || true)" ] || git config --global user.name "$USER"
[ -n "$(git config --global user.email || true)" ] || git config --global user.email "$USER@users.noreply.github.com"
gh repo view "$USER/$REPO_NAME" >/dev/null 2>&1 || gh repo create "$USER/$REPO_NAME" --public \
  --description "Symbolic ARC-AGI-2 solver: program induction over ARCGraph abstract objects"
if [ ! -d "$HOME/arc/$REPO_NAME/.git" ]; then
  gh repo clone "$USER/$REPO_NAME" "$HOME/arc/$REPO_NAME"
  git -C "$HOME/arc/$REPO_NAME" checkout -B main
fi
mkdir -p "$OUTBOX"
mkdir -p "$HOME/arc/$REPO_NAME/tools/wsl"; cp "$(dirname "$0")"/*.sh "$HOME/arc/$REPO_NAME/tools/wsl/"
cp "$(dirname "$0")/sync_outbox.sh" "$HOME/arc/sync_outbox.sh"; chmod +x "$HOME/arc/sync_outbox.sh"
if systemctl --user status >/dev/null 2>&1; then
  mkdir -p "$HOME/.config/systemd/user"
  cat > "$HOME/.config/systemd/user/arc-sync.service" <<UNIT
[Unit]
Description=Publish cloud Claude outbox to GitHub
[Service]
Type=oneshot
Environment=REPO=$HOME/arc/$REPO_NAME
ExecStart=$HOME/arc/sync_outbox.sh
UNIT
  cat > "$HOME/.config/systemd/user/arc-sync.timer" <<UNIT
[Unit]
Description=Run arc-sync every 5 minutes
[Timer]
OnBootSec=1min
OnUnitActiveSec=5min
[Install]
WantedBy=timers.target
UNIT
  systemctl --user daemon-reload
  systemctl --user enable --now arc-sync.timer
  echo "systemd user timer enabled (systemctl --user list-timers)"
else
  echo "systemd --user unavailable: run  while true; do REPO=$HOME/arc/$REPO_NAME ~/arc/sync_outbox.sh; sleep 300; done  in a spare WSL window"
fi
REPO="$HOME/arc/$REPO_NAME" "$HOME/arc/sync_outbox.sh"
echo "Setup done: https://github.com/$USER/$REPO_NAME  outbox: $OUTBOX  log: ~/arc/sync_outbox.log  pause: touch ~/arc/SYNC_PAUSED"
