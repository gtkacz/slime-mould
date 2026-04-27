#!/usr/bin/env bash
set -euo pipefail

API_DOMAIN="${API_DOMAIN:-}"
FRONTEND_ORIGIN="${FRONTEND_ORIGIN:-}"
REPO_URL="${REPO_URL:-}"
BRANCH="${BRANCH:-main}"
REPO_DIR="${REPO_DIR:-/opt/zipmould/slime-mould}"
DEPLOY_PUBLIC_KEY="${DEPLOY_PUBLIC_KEY:-}"

if [[ -z "$API_DOMAIN" || -z "$FRONTEND_ORIGIN" || -z "$REPO_URL" ]]; then
  cat >&2 <<'USAGE'
Required environment variables:
  API_DOMAIN=https host without scheme, for example api.example.com
  FRONTEND_ORIGIN=frontend origin with scheme, for example https://app.example.com
  REPO_URL=git clone URL, for example https://github.com/you/slime-mould.git

Optional:
  BRANCH=main
  REPO_DIR=/opt/zipmould/slime-mould
  DEPLOY_PUBLIC_KEY='ssh-ed25519 ...' to allow GitHub Actions SSH deploys
USAGE
  exit 1
fi

if [[ "$API_DOMAIN" == http*://* ]]; then
  echo "API_DOMAIN must not include http:// or https://." >&2
  exit 1
fi

sudo apt update
sudo apt install -y git curl build-essential pkg-config caddy

if ! id zipmould >/dev/null 2>&1; then
  sudo useradd --create-home --shell /bin/bash zipmould
fi

sudo install -d -m 700 -o zipmould -g zipmould /home/zipmould/.ssh
if [[ -n "$DEPLOY_PUBLIC_KEY" ]]; then
  echo "$DEPLOY_PUBLIC_KEY" | sudo tee /home/zipmould/.ssh/authorized_keys >/dev/null
elif [[ -f "$HOME/.ssh/authorized_keys" ]]; then
  sudo cp "$HOME/.ssh/authorized_keys" /home/zipmould/.ssh/authorized_keys
fi
if [[ -f /home/zipmould/.ssh/authorized_keys ]]; then
  sudo chown zipmould:zipmould /home/zipmould/.ssh/authorized_keys
  sudo chmod 600 /home/zipmould/.ssh/authorized_keys
fi

sudo install -d -o zipmould -g zipmould "$(dirname "$REPO_DIR")"

if [[ ! -d "$REPO_DIR/.git" ]]; then
  sudo -u zipmould git clone --branch "$BRANCH" "$REPO_URL" "$REPO_DIR"
else
  sudo -u zipmould git -C "$REPO_DIR" fetch origin "$BRANCH"
  sudo -u zipmould git -C "$REPO_DIR" reset --hard "origin/$BRANCH"
fi

if [[ ! -x /home/zipmould/.local/bin/uv ]]; then
  sudo -u zipmould bash -lc 'curl -LsSf https://astral.sh/uv/install.sh | sh'
fi

sudo tee /etc/zipmould-viz.env >/dev/null <<EOF
ZIPMOULD_REPO_DIR=$REPO_DIR
ZIPMOULD_BRANCH=$BRANCH
ZIPMOULD_ALLOWED_ORIGINS=$FRONTEND_ORIGIN
UV_LINK_MODE=copy
EOF

sudo cp "$REPO_DIR/deploy/oci/zipmould-viz.service" /etc/systemd/system/zipmould-viz.service
sudo cp "$REPO_DIR/deploy/oci/zipmould-deploy.sudoers" /etc/sudoers.d/zipmould-deploy
sudo chmod 0440 /etc/sudoers.d/zipmould-deploy
sudo visudo -cf /etc/sudoers.d/zipmould-deploy

sudo sed \
  -e "s|__ZIPMOULD_API_DOMAIN__|$API_DOMAIN|g" \
  -e "s|__ZIPMOULD_ALLOWED_ORIGIN__|$FRONTEND_ORIGIN|g" \
  "$REPO_DIR/deploy/oci/Caddyfile.template" | sudo tee /etc/caddy/Caddyfile >/dev/null
sudo caddy fmt --overwrite /etc/caddy/Caddyfile

sudo -u zipmould bash -lc "cd '$REPO_DIR' && /home/zipmould/.local/bin/uv sync --extra viz"

sudo systemctl daemon-reload
sudo systemctl enable --now zipmould-viz
sudo systemctl enable --now caddy
sudo systemctl reload caddy

sudo systemctl status zipmould-viz --no-pager
sudo systemctl status caddy --no-pager
