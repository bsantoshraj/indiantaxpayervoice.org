#!/usr/bin/env bash
# Run on the staging droplet (sudo), daily from /etc/cron.d/itv-backup. Dumps
# each host database as one consistent snapshot, compresses it and encrypts it
# to the age public key in backup-recipient.txt. The private key is kept off the
# droplet, so this host can write backups but never read them back.
# .env (which holds LimeSurvey's encryption keys) goes to a separate file: a
# database backup is useless without those keys.
set -euo pipefail
cd "$(dirname "$0")/../.."
set -a; . ./.env; set +a

dest=${ITV_BACKUP_DIR:-/var/backups/itv}
keep_days=${ITV_BACKUP_KEEP_DAYS:-14}
recipients=infra/staging/backup-recipient.txt
ts=$(date -u +%Y%m%dT%H%M%SZ)

umask 077
install -d -m 700 "$dest"
trap 'rm -f "$dest"/*.part' EXIT

for db in "$WP_DB_NAME" "$LS_DB_NAME"; do
  out="$dest/$db-$ts.sql.gz.age"
  mariadb-dump --single-transaction --routines --triggers --events --hex-blob --skip-dump-date "$db" \
    | gzip -9 | age -R "$recipients" > "$out.part"
  mv "$out.part" "$out"
done
age -R "$recipients" < .env > "$dest/env-$ts.age.part"
mv "$dest/env-$ts.age.part" "$dest/env-$ts.age"

find "$dest" -name '*.age' -mtime +"$keep_days" -delete
echo "$(date -u +%FT%TZ) backup $ts ok: $(cd "$dest" && ls -s --block-size=K ./*-"$ts"* | tr '\n' ' ')"
