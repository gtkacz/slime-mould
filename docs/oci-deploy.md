# OCI Backend Deployment

This repo includes the files needed to run the FastAPI backend on an Oracle
Cloud Always Free VM and redeploy it from GitHub Actions on every push to
`main`.

## Domains

Use two domains:

- Frontend: `https://app.example.com`
- Backend: `https://api.example.com`

Build the frontend with:

```bash
cp viz-web/.env.production.example viz-web/.env.production
# edit VITE_API_BASE_URL=https://api.example.com/api
cd viz-web
bun run build
```

## First VM Setup

Create an OCI Ubuntu VM, SSH into it, and run:

```bash
ssh-keygen -t ed25519 -f "$HOME/zipmould_oci_deploy" -C zipmould-oci-deploy

git clone https://github.com/YOUR_USER/slime-mould.git /tmp/slime-mould
cd /tmp/slime-mould
API_DOMAIN=api.example.com \
FRONTEND_ORIGIN=https://app.example.com \
REPO_URL=https://github.com/YOUR_USER/slime-mould.git \
BRANCH=main \
DEPLOY_PUBLIC_KEY="$(cat "$HOME/zipmould_oci_deploy.pub")" \
./deploy/oci/setup-vm.sh
```

The script:

- installs OS packages, Caddy, and `uv`
- creates a `zipmould` service user
- clones the repo to `/opt/zipmould/slime-mould`
- writes `/etc/zipmould-viz.env`
- installs the `zipmould-viz` systemd service
- installs a Caddy reverse proxy for `api.example.com`
- restricts `/api/*` requests, except `/api/health`, to the configured
  frontend `Origin` header

Check services:

```bash
systemctl status zipmould-viz --no-pager
systemctl status caddy --no-pager
curl http://127.0.0.1:8000/api/health
```

## Cloudflare DNS

Create a proxied DNS record for the API:

```text
Type: A
Name: api
Content: YOUR_OCI_PUBLIC_IP
Proxy status: Proxied
```

Create a DNS record for the frontend GitHub Pages site:

```text
Type: CNAME
Name: app
Content: YOUR_GITHUB_USER.github.io
Proxy status: DNS only
```

Use `SSL/TLS > Overview > Full (strict)`.

## GitHub Pages Frontend Deploy

The workflow is `.github/workflows/deploy-frontend-pages.yml`.

In repository settings, set `Pages > Build and deployment > Source` to
`GitHub Actions`. The built artifact includes `viz-web/public/CNAME`, so Pages
serves it at `https://app.slime-mould.tkacz.dev.br`.

By default the frontend is built with:

```text
VITE_API_BASE_URL=https://api.slime-mould.tkacz.dev.br/api
```

Set a repository variable named `VITE_API_BASE_URL` to override that URL.

## Firewall

In OCI Security Lists or Network Security Groups, allow:

```text
TCP 22   from your IP only
TCP 80   from Cloudflare IP ranges
TCP 443  from Cloudflare IP ranges
```

On the VM, you can sync UFW rules for Cloudflare:

```bash
SSH_CIDR=YOUR_PUBLIC_IP/32 /opt/zipmould/slime-mould/deploy/oci/sync-cloudflare-ufw.sh
```

This resets UFW, so set `SSH_CIDR` correctly.

## GitHub Actions Auto Deploy

The workflow is `.github/workflows/deploy-backend-oci.yml`.

Add repository secrets:

```text
OCI_HOST      api.example.com or the VM public IP
OCI_USER      zipmould
OCI_SSH_KEY   contents of $HOME/zipmould_oci_deploy
```

The deploy job runs `uv run pytest tests/viz`, then SSHes into the VM and runs:

```bash
/opt/zipmould/slime-mould/deploy/oci/deploy.sh
```

## Runtime Config

Backend runtime config lives in `/etc/zipmould-viz.env`:

```bash
ZIPMOULD_REPO_DIR=/opt/zipmould/slime-mould
ZIPMOULD_BRANCH=main
ZIPMOULD_ALLOWED_ORIGINS=https://app.example.com
UV_LINK_MODE=copy
```

After editing it:

```bash
sudo systemctl restart zipmould-viz
```

## Notes

CORS and origin-header checks restrict normal browser traffic. They are not
authentication, because non-browser clients can forge headers. Add auth or
signed request tokens if the solver endpoint needs real access control.
