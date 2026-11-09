#!/usr/bin/env bash
# PVQuant saha toplayıcısı — istemci sertifikası (mTLS) araçları (v2.563, Aşama 6 E2). Yalnız openssl.
# Kullanım:
#   edge_ca.sh kur  <dizin>                       → kök CA (10 yıl), CRL, dizin yapısı
#   edge_ca.sh ver  <dizin> <toplayici-adi> [gun] → istemci anahtarı + sertifikası (varsayılan 365 gün); çıktı <dizin>/istemciler/<ad>.{key,crt}
#   edge_ca.sh iptal <dizin> <toplayici-adi>      → sertifikayı iptal eder, CRL'yi yeniler (Caddy'ye kopyalanır)
#   edge_ca.sh liste <dizin>                      → verilen/iptal edilen sertifikalar
# Kök anahtar (ca.key) yalnız bu makinede, 0600; Caddy'ye yalnız ca.crt ve crl.pem gider (docs/edge/TOPLAYICI.md).
set -euo pipefail
cmd=${1:-}; d=${2:-}
[ -n "$cmd" ] && [ -n "$d" ] || { sed -n '2,9p' "$0"; exit 2; }
case "$cmd" in
  kur)
    mkdir -p "$d/istemciler" "$d/yeni"; : > "$d/index.txt"; echo 1000 > "$d/serial"; echo 1000 > "$d/crlnumber"
    cat > "$d/openssl.cnf" <<CNF
[ ca ]
default_ca = pvq
[ pvq ]
dir = $d
database = \$dir/index.txt
new_certs_dir = \$dir/yeni
serial = \$dir/serial
crlnumber = \$dir/crlnumber
certificate = \$dir/ca.crt
private_key = \$dir/ca.key
default_md = sha256
default_days = 365
default_crl_days = 30
policy = p
unique_subject = no
[ p ]
commonName = supplied
organizationName = optional
[ istemci ]
basicConstraints = CA:FALSE
keyUsage = digitalSignature
extendedKeyUsage = clientAuth
CNF
    openssl genrsa -out "$d/ca.key" 4096 2>/dev/null; chmod 600 "$d/ca.key"
    openssl req -x509 -new -key "$d/ca.key" -sha256 -days 3650 -subj "/O=PVQuant edge/CN=PVQuant Edge CA" -out "$d/ca.crt"
    openssl ca -config "$d/openssl.cnf" -gencrl -out "$d/crl.pem" 2>/dev/null
    echo "CA hazır: $d/ca.crt (Caddy'ye), $d/crl.pem (Caddy'ye), $d/ca.key (YALNIZ burada)";;
  ver)
    ad=${3:?toplayıcı adı}; gun=${4:-365}
    openssl genrsa -out "$d/istemciler/$ad.key" 2048 2>/dev/null; chmod 600 "$d/istemciler/$ad.key"
    openssl req -new -key "$d/istemciler/$ad.key" -subj "/O=PVQuant edge/CN=$ad" -out "$d/istemciler/$ad.csr"
    openssl ca -batch -config "$d/openssl.cnf" -extensions istemci -days "$gun" -in "$d/istemciler/$ad.csr" -out "$d/istemciler/$ad.crt" 2>/dev/null
    rm -f "$d/istemciler/$ad.csr"
    echo "istemci sertifikası: $d/istemciler/$ad.crt + $ad.key ($gun gün) → toplayıcıya --sertifika/--sertifika-anahtari";;
  iptal)
    ad=${3:?toplayıcı adı}
    openssl ca -config "$d/openssl.cnf" -revoke "$d/istemciler/$ad.crt" 2>/dev/null
    openssl ca -config "$d/openssl.cnf" -gencrl -out "$d/crl.pem" 2>/dev/null
    echo "iptal edildi: $ad; yeni CRL $d/crl.pem → Caddy'ye kopyalayıp yeniden yükleyin";;
  liste)
    awk -F'\t' '{ printf "%s\t%s\t%s\n", ($1=="V"?"geçerli":"iptal"), $4, $6 }' "$d/index.txt";;
  *) echo "bilinmeyen komut: $cmd"; exit 2;;
esac
