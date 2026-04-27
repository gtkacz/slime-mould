#!/usr/bin/env bash
set -euo pipefail

SSH_CIDR="${SSH_CIDR:-}"

sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing

if [[ -n "$SSH_CIDR" ]]; then
  sudo ufw allow from "$SSH_CIDR" to any port 22 proto tcp
else
  echo "SSH_CIDR is empty; not adding an SSH allow rule." >&2
  echo "Run with SSH_CIDR=x.x.x.x/32 to keep SSH access through UFW." >&2
fi

while read -r cidr; do
  [[ -z "$cidr" ]] && continue
  sudo ufw allow from "$cidr" to any port 80 proto tcp
  sudo ufw allow from "$cidr" to any port 443 proto tcp
done < <(curl -fsSL https://www.cloudflare.com/ips-v4)

while read -r cidr; do
  [[ -z "$cidr" ]] && continue
  sudo ufw allow from "$cidr" to any port 80 proto tcp
  sudo ufw allow from "$cidr" to any port 443 proto tcp
done < <(curl -fsSL https://www.cloudflare.com/ips-v6)

sudo ufw --force enable
sudo ufw status verbose
