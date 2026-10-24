#!/usr/bin/env bash
# Run on the staging droplet as deploy. Replaces every generated secret in .env
# and applies it wherever it is used: host DB users, LimeSurvey and WordPress
# accounts, and the containers. Logs every admin out, then takes a fresh backup
# so the newest secrets backup matches. Secrets are never printed.
# --encryption-keys also replaces LimeSurvey's encryption keys; refused while
# any data is encrypted with them (it would become unreadable).
# Usage: rotate-secrets.sh [--encryption-keys]
set -euo pipefail
cd "$(dirname "$0")/../.."
set -a; . ./.env; set +a

rotate_keys=0
[[ "${1:-}" == "--encryption-keys" ]] && rotate_keys=1

rand() { openssl rand -base64 32 | tr -d '/+=' | cut -c1-32; }
set_var() { grep -q "^$1=" .env && sed -i "s#^$1=.*#$1=$2#" .env; }
sql() { sudo mariadb -N "$LS_DB_NAME" -e "$1"; }

if (( rotate_keys )); then
  encrypted=$(sql "SELECT (SELECT COUNT(*) FROM lime_questions WHERE encrypted = 'Y')
    + (SELECT COUNT(*) FROM lime_participants)
    + (SELECT COUNT(*) FROM information_schema.tables
       WHERE table_schema = DATABASE() AND table_name LIKE 'lime_tokens%')")
  if (( encrypted > 0 )); then
    echo "Refusing to rotate encryption keys: $encrypted encrypted item(s) would become unreadable." >&2
    exit 1
  fi
fi

umask 077
cp -p .env .env.pre-rotation
trap '[[ -f .env.pre-rotation ]] && echo "Rotation incomplete: previous .env kept in .env.pre-rotation" >&2' EXIT

for var in WP_DB_PASSWORD WP_DB_ROOT_PASSWORD WP_ADMIN_PASSWORD LS_DB_PASSWORD \
           LS_DB_ROOT_PASSWORD LS_ADMIN_PASSWORD ITV_LS_PASSWORD ITV_GATE_SECRET; do
  set_var "$var" "$(rand)"
done
if (( rotate_keys )); then
  keys=$(docker compose run --rm --no-deps -T --entrypoint php limesurvey -r '
    $kp = sodium_crypto_box_keypair();
    echo "LS_ENCRYPT_KEYPAIR=", bin2hex($kp), "\n";
    echo "LS_ENCRYPT_PUBLIC_KEY=", bin2hex(sodium_crypto_box_publickey($kp)), "\n";
    echo "LS_ENCRYPT_SECRET_KEY=", bin2hex(sodium_crypto_box_secretkey($kp)), "\n";
    echo "LS_ENCRYPT_NONCE=", bin2hex(random_bytes(SODIUM_CRYPTO_SECRETBOX_NONCEBYTES)), "\n";
    echo "LS_ENCRYPT_SECRET_BOX_KEY=", bin2hex(sodium_crypto_secretbox_keygen()), "\n";' 2>/dev/null)
  while IFS='=' read -r var value; do set_var "$var" "$value"; done <<<"$keys"
fi
set -a; . ./.env; set +a
echo "New secrets written to .env$( (( rotate_keys )) && echo ', including LimeSurvey encryption keys')."

echo "Applying to the host databases…"
sudo ./infra/staging/setup-host-db.sh >/dev/null

echo "Recreating containers (LimeSurvey regenerates config.php and security.php)…"
docker compose up -d --force-recreate --quiet-pull 2>&1 | grep -vE 'Container .* (Recreate|Recreated|Starting|Started|Running|Waiting|Healthy)' || true
for _ in $(seq 1 60); do curl -fs -o /dev/null http://127.0.0.1:8081/ && break; sleep 5; done

echo "Updating LimeSurvey account passwords and ending all sessions…"
hash() { docker compose exec -T limesurvey php -r 'echo password_hash(stream_get_contents(STDIN), PASSWORD_DEFAULT);'; }
for pair in "$LS_ADMIN_USER:LS_ADMIN_PASSWORD" "$ITV_LS_USER:ITV_LS_PASSWORD"; do
  user=${pair%%:*}; var=${pair#*:}
  updated=$(sql "UPDATE lime_users SET password = '$(printf '%s' "${!var}" | hash)' WHERE users_name = '$user'; SELECT ROW_COUNT();")
  [[ "$updated" == "1" ]] || { echo "LimeSurvey user $user not found" >&2; exit 1; }
done
sql "DELETE FROM lime_sessions"

echo "Updating the WordPress admin password and ending all sessions…"
docker compose run --rm -T wpcli wp user update "$WP_ADMIN_USER" --prompt=user_pass <<<"$WP_ADMIN_PASSWORD" >/dev/null 2>&1
docker compose run --rm -T wpcli wp user session destroy "$WP_ADMIN_USER" --all >/dev/null 2>&1

echo "Checking the aggregator can still export from LimeSurvey…"
out=$(docker compose run --rm aggregator 2>&1) || { echo "$out" | tail -5 >&2; exit 1; }
grep -E "INFO rows" <<<"$out" | sed 's/.*INFO //'

echo "Taking a fresh backup (secrets backup now matches)…"
sudo ./infra/staging/backup-db.sh | tail -1

shred -u .env.pre-rotation 2>/dev/null || rm -f .env.pre-rotation
echo "Rotation complete. New admin passwords are in /opt/itv/.env (WP_ADMIN_PASSWORD, LS_ADMIN_PASSWORD)."
