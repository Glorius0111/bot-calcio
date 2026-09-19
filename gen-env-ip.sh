#!/usr/bin/env bash
set -euo pipefail
# Genera .env per chi NON ha dominio, usando sslip.io (HTTPS gratis)
# Uso: ./gen-env-ip.sh 91.189.1.10 tuamail@example.com
IP="${1:-}"
EMAIL="${2:-}"
if [ -z "$IP" ] || [ -z "$EMAIL" ]; then
  echo "Uso: ./gen-env-ip.sh IP_VPS EMAIL"
  echo "Es: ./gen-env-ip.sh 91.189.1.10 tuamail@example.com"
  exit 1
fi
DASHIP=$(echo "$IP" | tr '.' '-')
STREAM="stream.${DASHIP}.sslip.io"
PANEL="panel.${DASHIP}.sslip.io"
PASS=$(openssl rand -base64 32 | tr -d '/+=' | cut -c1-32)
cat > .env <<EOF
STREAM_DOMAIN=${STREAM}
PANEL_DOMAIN=${PANEL}
ACME_EMAIL=${EMAIL}
PANEL_USER=admin
# Genera hash dopo con: docker run --rm caddy:2.9-alpine caddy hash-password
# poi sostituisci la riga sotto
PANEL_HASH=\$2a\$14\$CAMBIAQUESTOHASHCONUNOHASHVERO
API_PASSWORD=${PASS}
PORT=8888
EOF
echo "Creato .env:"
cat .env
echo ""
echo "Verifica DNS (devono rispondere con $IP):"
getent hosts "$STREAM" || nslookup "$STREAM" || dig +short "$STREAM" || true
echo ""
echo "Prossimo: genera PANEL_HASH con:"
echo "  docker run --rm caddy:2.9-alpine caddy hash-password"
echo "e mettilo in .env, poi aggiorna tuliprox/config/api-proxy.yml host: $STREAM"
