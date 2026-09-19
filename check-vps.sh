#!/usr/bin/env bash
# Diagnosi unica VPS - incolla tutto sul server ed esegui, poi mandami l'output
set -u
echo "===== 1 SSH ====="
sshd -t; echo "sshd-t-exit:$?"
grep -E '^PasswordAuthentication|^PermitRootLogin' /etc/ssh/sshd_config
echo ""
echo "===== 2 UFW ====="
ufw status verbose
grep FORWARD_POLICY /etc/default/ufw
echo ""
echo "===== 3 DOCKER ====="
docker ps --format 'table {{.Names}} {{.Status}}'
echo ""
echo "===== 4 ENV (controllo placeholder) ====="
grep -E 'DOMAIN|EMAIL|USER|HASH|PASSWORD|PORT' /opt/stream/.env 2>/dev/null || grep -E 'DOMAIN|EMAIL|USER|HASH|PASSWORD|PORT' .env
echo ""
echo "===== 5 CADDY LOG ====="
docker logs --tail 15 caddy
echo ""
echo "===== 6 TEST RETE DA CADDY ====="
timeout 15 docker exec caddy wget -T 10 -qO- https://acme-v02.api.letsencrypt.org/directory -O /dev/null && echo "CADDY-INTERNET: OK" || echo "CADDY-INTERNET: FAIL"
echo ""
echo "FINE - copia tutto l'output e mandamelo"
