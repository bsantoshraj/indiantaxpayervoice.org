#!/usr/bin/env bash
# Local-only TLS: a private CA plus a server certificate for this machine's
# LAN IP and localhost. Browsers need HTTPS ("secure context") for the
# survey's bot check. Import var/certs/itv-local-ca.crt into your browser/OS
# trust store to avoid warnings. Never use these certificates in production.
set -euo pipefail
cd "$(dirname "$0")/.."
ip="${1:?usage: make-local-certs.sh <lan-ip>}"
dir=var/certs
mkdir -p "$dir"
umask 077
if [[ ! -f $dir/itv-local-ca.key ]]; then
  openssl req -x509 -newkey rsa:2048 -nodes -days 825 -subj "/CN=ITV local development CA" \
    -keyout "$dir/itv-local-ca.key" -out "$dir/itv-local-ca.crt" 2>/dev/null
fi
openssl req -newkey rsa:2048 -nodes -subj "/CN=$ip" -keyout "$dir/server.key" -out "$dir/server.csr" 2>/dev/null
printf 'subjectAltName=IP:%s,IP:127.0.0.1,DNS:localhost\nextendedKeyUsage=serverAuth\nbasicConstraints=CA:FALSE\n' "$ip" > "$dir/server.ext"
openssl x509 -req -in "$dir/server.csr" -CA "$dir/itv-local-ca.crt" -CAkey "$dir/itv-local-ca.key" \
  -CAcreateserial -days 397 -extfile "$dir/server.ext" -out "$dir/server.crt" 2>/dev/null
chmod 644 "$dir/itv-local-ca.crt" "$dir/server.crt"
chmod 600 "$dir/server.key"   # read by nginx's root master process
rm -f "$dir/server.csr" "$dir/server.ext"
echo "Certificates written to $dir (keys not printed)."
