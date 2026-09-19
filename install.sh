#!/usr/bin/env bash
set -euo pipefail
# Installazione blindata: Ubuntu 22.04/24.04 + Docker + UFW + Fail2ban + Caddy/Tuliprox/MediaFlow
# Esegui come root sul VPS: bash install.sh

if [ "$(id -u)" -ne 0 ]; then echo "Esegui come root: sudo bash install.sh"; exit 1; fi

echo "=== [1/7] Sistema + Docker ==="
apt-get update -y
apt-get install -y ca-certificates curl gnupg ufw fail2ban unattended-upgrades openssl
install -m 0755 -d /etc/apt/keyrings
if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
fi
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker

echo "=== [2/7] Hardening SSH ==="
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak.$(date +%F) || true
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#\?X11Forwarding.*/X11Forwarding no/' /etc/ssh/sshd_config
systemctl reload ssh || systemctl reload sshd || true
echo "ATTENZIONE: assicurati di avere una chiave SSH configurata prima di chiudere la sessione!"

echo "=== [3/7] Firewall UFW: solo 22,80,443 ==="
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 443/udp
yes | ufw enable
ufw status verbose

echo "=== [4/7] Fail2ban + aggiornamenti automatici ==="
cat > /etc/fail2ban/jail.local <<'EOF'
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5
[sshd]
enabled = true
EOF
systemctl enable --now fail2ban
echo 'Unattended-Upgrade::Automatic-Reboot "false";' > /etc/apt/apt.conf.d/52unattended-no-reboot

echo "=== [5/7] Cartelle progetto ==="
mkdir -p /opt/stream/tuliprox/config /opt/stream/tuliprox/data /opt/stream/tuliprox/backup /opt/stream/tuliprox/cache
echo "Copia qui docker-compose.yml, Caddyfile, .env e tuliprox/config/*.yml"
ls -la /opt/stream || true

echo "=== [6/7] .env sicura (se manca) ==="
if [ ! -f /opt/stream/.env ] && [ -f .env.example ]; then
  cp .env.example /opt/stream/.env
  PASS=$(openssl rand -base64 32 | tr -d '/+=' | cut -c1-32)
  sed -i "s/CAMBIA_con_password_lunga_32caratteri_random/$PASS/g" /opt/stream/.env || true
  echo "Generata API_PASSWORD random in /opt/stream/.env — cambiala anche in source.yml"
fi

echo "=== [7/7] Avvio stack ==="
if [ -f /opt/stream/docker-compose.yml ] || [ -f docker-compose.yml ]; then
  DIR="/opt/stream"
  [ -f docker-compose.yml ] && DIR="."
  docker compose --project-directory "$DIR" up -d
  sleep 5
  docker ps
  echo ""
  echo "Caddy logs (CTRL+C per uscire): docker logs -f caddy"
else
  echo "Copia i file del progetto in /opt/stream poi: cd /opt/stream && docker compose up -d"
fi

echo ""
echo "FATTO. Prossimi passi:"
echo "1. DNS: stream.tuodominio.com e panel.tuodominio.com -> IP VPS (record A)"
echo "2. .env: compila STREAM_DOMAIN, PANEL_DOMAIN, ACME_EMAIL, PANEL_HASH (caddy hash-password)"
echo "3. source.yml: incolla URL MediaFlow codificato del provider"
echo "4. api-proxy.yml: crea 1 user per cliente con password diverse + exp_date"
echo "5. Test: https://panel... (admin) e https://stream.../get.php?username=cliente01&password=XXX"
