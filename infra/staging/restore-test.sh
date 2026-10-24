#!/usr/bin/env bash
# Run on the staging droplet (sudo). Restores the newest complete backup set
# (both databases and .env from one run) into scratch databases, proves each
# is a faithful copy (re-dumped and
# compared with the backup), runs basic application checks, then drops the
# scratch databases. Decrypted data and the key stay in memory (/dev/shm).
# Usage: restore-test.sh <age-identity-file>   (/dev/stdin to stream it over SSH)
set -euo pipefail
cd "$(dirname "$0")/../.."
set -a; . ./.env; set +a

identity_src=${1:?usage: restore-test.sh <age-identity-file>}
dest=${ITV_BACKUP_DIR:-/var/backups/itv}
dump_opts=(--single-transaction --routines --triggers --events --hex-blob --skip-dump-date)

work=$(mktemp -d /dev/shm/itv-restore.XXXXXX)
scratch=()
cleanup() {
  for db in "${scratch[@]}"; do mariadb -e "DROP DATABASE IF EXISTS \`$db\`"; done
  rm -rf "$work"
}
trap cleanup EXIT
umask 077
cat "$identity_src" > "$work/identity"

# "-- Host: … Database: <name>" is the only line that legitimately differs.
normalise() { grep -v '^-- '; }
decrypt() { age -d -i "$work/identity" "$1"; }
q() { mariadb -N -B "$1" -e "$2"; }

# Newest run that produced all three files; never mix files from different runs.
set_ts=""
shopt -s nullglob
env_files=("$dest"/env-*.age)   # timestamps sort lexically; walk newest first
for (( i = ${#env_files[@]} - 1; i >= 0; i-- )); do
  ts=$(basename "${env_files[i]}" .age); ts=${ts#env-}
  if [[ -f "$dest/$WP_DB_NAME-$ts.sql.gz.age" && -f "$dest/$LS_DB_NAME-$ts.sql.gz.age" ]]; then set_ts=$ts; break; fi
done
[[ -n "$set_ts" ]] || { echo "FAIL: no complete backup set in $dest"; exit 1; }
echo "Backup set $set_ts"

start=$(date +%s)
for db in "$WP_DB_NAME" "$LS_DB_NAME"; do
  backup="$dest/$db-$set_ts.sql.gz.age"
  target="restoretest_$db"
  scratch+=("$target")
  mariadb -e "DROP DATABASE IF EXISTS \`$target\`; CREATE DATABASE \`$target\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"

  t0=$(date +%s)
  decrypt "$backup" | gunzip | mariadb "$target"
  t1=$(date +%s)

  decrypt "$backup" | gunzip | normalise > "$work/original.sql"
  mariadb-dump "${dump_opts[@]}" "$target" | normalise > "$work/restored.sql"
  if ! cmp -s "$work/original.sql" "$work/restored.sql"; then
    echo "FAIL: $db restored copy differs from backup $(basename "$backup")"
    diff "$work/original.sql" "$work/restored.sql" | head -20
    exit 1
  fi
  tables=$(q "$target" "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE()")
  rows=$(q "$target" "SELECT COALESCE(SUM(table_rows),0) FROM information_schema.tables WHERE table_schema = DATABASE()")
  echo "OK  $db: $(basename "$backup") ($(du -k "$backup" | cut -f1) KB) -> $target: $tables tables, ~$rows rows, identical re-dump, load $((t1 - t0))s"
done

# Application-level checks on the restored copies.
wp="restoretest_$WP_DB_NAME"; ls="restoretest_$LS_DB_NAME"; sid="$ITV_LS_SURVEY_ID"
echo "OK  WordPress: siteurl=$(q "$wp" "SELECT option_value FROM wp_options WHERE option_name='siteurl'"), users=$(q "$wp" "SELECT COUNT(*) FROM wp_users"), published pages=$(q "$wp" "SELECT COUNT(*) FROM wp_posts WHERE post_type='page' AND post_status='publish'")"
active=$(q "$ls" "SELECT active FROM lime_surveys WHERE sid=$sid")
[[ "$active" == "Y" ]] || { echo "FAIL: survey $sid not active in restored LimeSurvey DB (active='$active')"; exit 1; }
echo "OK  LimeSurvey: survey $sid active, questions=$(q "$ls" "SELECT COUNT(*) FROM lime_questions WHERE sid=$sid"), responses=$(q "$ls" "SELECT COUNT(*) FROM lime_responses_$sid")"

# The set's secrets backup must hold all LimeSurvey keys: they are what decrypts
# this set's data. Keys rotated since the backup are reported, not a failure.
env_backup="$dest/env-$set_ts.age"
saved_keys=$(decrypt "$env_backup" | grep -cE '^LS_ENCRYPT_[A-Z_]+=[0-9a-f]+$' || true)
(( saved_keys == 5 )) || { echo "FAIL: $(basename "$env_backup") holds $saved_keys of 5 LimeSurvey encryption keys"; exit 1; }
if cmp -s <(decrypt "$env_backup" | grep '^LS_ENCRYPT_' | sort) <(grep '^LS_ENCRYPT_' .env | sort); then
  echo "OK  secrets: $(basename "$env_backup") holds all 5 LimeSurvey keys (the running keys)"
else
  echo "OK  secrets: $(basename "$env_backup") holds all 5 LimeSurvey keys (rotated since; restore this set with its own keys)"
fi
echo "PASS restore test in $(( $(date +%s) - start ))s; scratch databases dropped"
