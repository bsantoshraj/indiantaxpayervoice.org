#!/usr/bin/env bash
# Generate a local .env with random secrets. Refuses to overwrite an existing one.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -e .env ]]; then
  echo ".env already exists; delete it deliberately if you want new secrets." >&2
  exit 1
fi

rand() { openssl rand -base64 32 | tr -d '/+=' | cut -c1-32; }

# LimeSurvey stores libsodium keys hex-encoded in security.php.
keys=$(docker run --rm --entrypoint php martialblog/limesurvey:7.5.1-261021-apache -r '
  $kp = sodium_crypto_box_keypair();
  echo "LS_ENCRYPT_KEYPAIR=", bin2hex($kp), "\n";
  echo "LS_ENCRYPT_PUBLIC_KEY=", bin2hex(sodium_crypto_box_publickey($kp)), "\n";
  echo "LS_ENCRYPT_SECRET_KEY=", bin2hex(sodium_crypto_box_secretkey($kp)), "\n";
  echo "LS_ENCRYPT_NONCE=", bin2hex(random_bytes(SODIUM_CRYPTO_SECRETBOX_NONCEBYTES)), "\n";
  echo "LS_ENCRYPT_SECRET_BOX_KEY=", bin2hex(sodium_crypto_secretbox_keygen()), "\n";')

umask 077
{
  sed -E '/^LS_ENCRYPT_/d; s/^(#.*)$/\1/' .env.example \
    | while IFS= read -r line; do
        if [[ $line == *"=<generated>" ]]; then echo "${line%%=*}=$(rand)"; else echo "$line"; fi
      done
  echo "$keys"
} > .env
sed -i 's/^ITV_LS_SURVEY_ID=.*/ITV_LS_SURVEY_ID=/' .env
chmod 600 .env
echo "Wrote .env (mode 600). Secrets were not printed."
