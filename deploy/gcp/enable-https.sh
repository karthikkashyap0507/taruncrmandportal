#!/usr/bin/env bash
# Turn on HTTPS once DNS for jobsnexgen.com, www and crm points at this server.
# Usage, from the repo root on the VM:  bash deploy/gcp/enable-https.sh you@example.com
set -euo pipefail

EMAIL="${1:?Usage: bash deploy/gcp/enable-https.sh <your-email>}"
DOMAINS=(jobsnexgen.com www.jobsnexgen.com crm.jobsnexgen.com)
IP=$(curl -s -H "Metadata-Flavor: Google" \
  http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip)

echo "This server's IP: $IP"
echo "What the internet sees (asking Google DNS):"
ready=1
for d in "${DOMAINS[@]}"; do
  a=$(dig +short A "$d" @8.8.8.8 | grep -E '^[0-9.]+$' | sort -u | tr '\n' ' ' | sed 's/ $//' || true)
  aaaa=$(dig +short AAAA "$d" @8.8.8.8 | grep ':' || true)
  if [ "$a" = "$IP" ] && [ -z "$aaaa" ]; then
    echo "  ok       $d -> $a"
  else
    ready=0
    echo "  NOT YET  $d -> ${a:-no A record}"
    [ -z "$aaaa" ] || echo "           also has an IPv6 (AAAA) record: delete it at Hostinger"
  fi
done

if [ "$ready" != 1 ]; then
  echo
  echo "DNS doesn't point here for every domain yet. Check the records at Hostinger,"
  echo "wait 5-10 minutes and run this again. (Old records can take up to a few hours to expire.)"
  exit 1
fi

args=()
for d in "${DOMAINS[@]}"; do args+=(-d "$d"); done
sudo certbot --nginx --non-interactive --agree-tos --redirect -m "$EMAIL" "${args[@]}"

echo
echo "HTTPS is on:"
echo "  Job portal: https://www.jobsnexgen.com"
echo "  CRM:        https://crm.jobsnexgen.com"
