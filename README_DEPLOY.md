# Deploy VPS — Tuliprox + MediaFlow + Caddy (sicuro)

## Architettura
```
Provider M3U
   |
   v  (solo rete interna docker, con API_PASSWORD)
MediaFlow :8888  -- decodifica / proxy HLS, DRM, headers
   |
   v  http://mediaflow:8888/...
Tuliprox :8901 -- filtra, crea target "clienti", gestisce user/scadenze/max_conn
   |
   v  (solo via Caddy, HTTPS automatico)
Caddy :80/:443
   |-- https://stream.tuodominio.com  -> clienti (M3U/Xtream, senza auth admin)
   +-- https://panel.tuodominio.com   -> solo TU (BasicAuth Caddy + login Tuliprox)
```
- Porte esposte fuori: SOLO 80,443 (Caddy) + 22 (SSH key-only).
- 8901 e 8888 MAI esposti: `expose`, non `ports`.
- Clienti finali vedono solo `stream.*`, mai IP VPS, mai provider, mai panel.

## SENZA DOMINIO (il tuo caso: solo VPS)

Non serve comprare dominio. Usa `sslip.io` = DNS gratis che punta al tuo IP + HTTPS vero Let's Encrypt.

```bash
# sul tuo PC o VPS:
./gen-env-ip.sh IP_VPS tuamail@example.com
# es: ./gen-env-ip.sh 91.189.1.10 mario@gmail.com
# crea .env con:
# STREAM_DOMAIN=stream.91-189-1-10.sslip.io
# PANEL_DOMAIN=panel.91-189-1-10.sslip.io
```

Clienti useranno:
```
https://stream.91-189-1-10.sslip.io/get.php?username=cliente01&password=XXX
```
Pannello solo tu:
```
https://panel.91-189-1-10.sslip.io
```
Limite: l'IP resta visibile (inevitabile senza dominio + Cloudflare). Ma provider nascosto, password per cliente, HTTPS cifrato e porte 8901/8888 chiuse restano garantiti. Quando vuoi il massimo anonimato, compra un dominio da 10€/anno e mettilo dietro Cloudflare proxy.

## Installazione sul VPS (Ubuntu 22.04/24.04, root)

1. Carica i file:
```bash
scp -r . root@IP_VPS:/opt/stream
ssh root@IP_VPS
cd /opt/stream
```

2. Configura:
```bash
cp .env.example .env
nano .env
# STREAM_DOMAIN, PANEL_DOMAIN, ACME_EMAIL,
# API_PASSWORD=$(openssl rand -base64 32 | tr -d '/+=' | cut -c1-32)
# PANEL_HASH=$(docker run --rm caddy:2.9-alpine caddy hash-password)
```

3. Hardening + avvio:
```bash
bash install.sh
# oppure manuale:
# ufw allow 22,80,443 && ufw enable
# docker compose up -d
```

4. Tuliprox:
- `tuliprox/config/source.yml`: metti URL MediaFlow codificato
  Come codificare M3U provider per MediaFlow:
  ```bash
  echo -n 'http://provider/link.m3u' | base64 -w0
  # URL finale: http://mediaflow:8888/proxy/m3u?api_password=XXX&d=BASE64
  ```
  Test dall'interno: `docker exec tuliprox wget -qO- 'http://mediaflow:8888/...' | head`
- `tuliprox/config/api-proxy.yml`: host = tuo STREAM_DOMAIN, 1 credential per cliente
- Apri `https://panel.tuodominio.com` -> completa setup Tuliprox -> Update playlist

5. Clienti:
```
M3U:  https://stream.tuodominio.com/get.php?username=cliente01&password=XXX
Xtream API:
  Server: https://stream.tuodominio.com
  User: cliente01
  Pass: XXX
EPG: https://stream.tuodominio.com/xmltv.php?username=cliente01&password=XXX
```
Alias corti anti-blocco: `/m3u`, `/xtream`, `/epg` al posto di `/get.php`, `/player_api.php`, `/xmltv.php`.

## Sicurezza inclusa
- UFW deny-all tranne 22/80/443, Fail2ban SSH, upgrade automatici
- SSH: root con chiave, no password
- Caddy: TLS auto Let's Encrypt, HSTS, nosniff, admin off
- Panel: BasicAuth + IP tua se vuoi (`ADMIN_IP`), mai dato ai clienti
- Tuliprox: `user_access_control: true`, `sanitize_sensitive_info`, 1 user per cliente, `max_connections:1`, `exp_date`, `ui_enabled:false`
- MediaFlow: `DISABLE_DOCS/HOME/SPEEDTEST=true`, `API_PASSWORD` lunga, `FORWARDED_ALLOW_IPS` solo docker
- Backup: `/opt/stream/tuliprox/backup` + `docker compose` backup `caddy_data`. Cifra backup con password prima di scaricarli.

## Comandi utili
```bash
docker logs -f caddy
docker logs -f tuliprox
docker logs -f mediaflow
docker compose up -d --pull always && docker image prune -f
caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
ufw status verbose; fail2ban-client status sshd
```

## Non fare mai
- Non dare ai clienti: panel URL, IP VPS, link provider originale, API_PASSWORD MediaFlow
- Non esporre 8901/8888 con `ports:` su internet
- Non usare stesso user/pass per più clienti (non puoi bannarne uno solo)
- Non disattivare `user_access_control`
