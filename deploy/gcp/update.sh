#!/usr/bin/env bash
# Rebuild and restart JobsNexGen on the VM.
# Usage, from the repo root:  bash deploy/gcp/update.sh
# Pulls the latest code first; setup.sh passes --no-pull for the first build.
set -euo pipefail

# Everything runs inside main() so bash has read the whole file before
# `git pull` can change it.
main() {
  local repo ecosystem
  repo="$(cd "$(dirname "$0")/../.." && pwd)"
  ecosystem="$HOME/.jobsnexgen/ecosystem.config.js"
  [ -f "$ecosystem" ] || { echo "Run deploy/gcp/setup.sh first."; exit 1; }

  if [ "${1:-}" != "--no-pull" ]; then
    echo "==> Pulling latest code"
    git -C "$repo" pull --ff-only
  fi

  echo "==> Backend dependencies"
  for app in backend crm/backend; do
    "$repo/$app/venv/bin/pip" install -q --upgrade pip
    "$repo/$app/venv/bin/pip" install -q -r "$repo/$app/requirements.txt"
  done

  # NEXT_PUBLIC_* values are baked in at build time and override the committed .env files
  echo "==> Job portal frontend"
  cd "$repo/frontend"
  npm ci --no-audit --no-fund
  NEXT_PUBLIC_API_URL=https://www.jobsnexgen.com/api/v1 \
  NEXT_PUBLIC_SITE_URL=https://www.jobsnexgen.com \
    npm run build

  echo "==> CRM frontend"
  cd "$repo/crm/frontend"
  npm ci --no-audit --no-fund
  NEXT_PUBLIC_CRM_API_URL=https://crm.jobsnexgen.com npm run build

  echo "==> Restarting apps"
  pm2 startOrReload "$ecosystem" --update-env
  pm2 save
}

main "$@"
