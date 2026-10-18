#!/bin/bash
# baslat.sh <ad> <taban> — üretimdeki iki katmanlı Caddy'nin yerel kopyası + iki kısıtlı hat.
#   statik (Caddyfile.web aynen; kök ve port değişir): 127.0.0.1:<taban>080
#   kenar (Caddyfile ile aynı: encode zstd gzip, /v1/* → API, kalan → statik): https://localhost:<taban>443  [h1+h2; yerelde h3 yok]
#   /v1/* yerelde canlı API'ye (https://pvquant.com) gider — doğrulama verisi gerçektir.
#   kısıtlı hatlar: https://localhost:<taban+1>443 (hizli3g), https://localhost:<taban+2>443 (yavas4g)
set -euo pipefail
AD=$1; T=$2
KOK=$(git rev-parse --show-toplevel); R="$KOK/perf/.replika/$AD"; mkdir -p "$R/caddy"
{ printf '{\n\tadmin off\n\tstorage file_system %s/caddy/veri\n}\n' "$R"
  sed -e "s#^:8080 {#:${T}080 {#" -e "s#root \* /srv#root * $R/dist#" "$KOK/Caddyfile.web"; } > "$R/caddy/Caddyfile.web"
cat > "$R/caddy/Caddyfile.kenar" <<KENAR
{
	admin off
	skip_install_trust
	auto_https disable_redirects
	http_port ${T}000
	storage file_system $R/caddy/veri
	servers {
		protocols h1 h2
	}
}
https://localhost:${T}443 {
	tls internal
	encode zstd gzip
	route /v1/* {
		reverse_proxy https://pvquant.com {
			header_up Host pvquant.com
		}
	}
	reverse_proxy 127.0.0.1:${T}080
}
KENAR
for k in Caddyfile.web Caddyfile.kenar; do caddy validate --config "$R/caddy/$k" --adapter caddyfile > /dev/null 2>&1 || { echo "geçersiz: $k"; caddy validate --config "$R/caddy/$k" --adapter caddyfile; exit 1; }; done
nohup caddy run --config "$R/caddy/Caddyfile.web" --adapter caddyfile > "$R/caddy/statik.log" 2>&1 & echo $! > "$R/caddy/statik.pid"
nohup caddy run --config "$R/caddy/Caddyfile.kenar" --adapter caddyfile > "$R/caddy/kenar.log" 2>&1 & echo $! > "$R/caddy/kenar.pid"
nohup node "$KOK/perf/replika/kisitla.mjs" $((T+1))443 ${T}443 hizli3g > "$R/caddy/hizli3g.log" 2>&1 & echo $! > "$R/caddy/hizli3g.pid"
nohup node "$KOK/perf/replika/kisitla.mjs" $((T+2))443 ${T}443 yavas4g > "$R/caddy/yavas4g.log" 2>&1 & echo $! > "$R/caddy/yavas4g.pid"
nohup node "$KOK/perf/replika/kisitla.mjs" $((T+3))443 ${T}443 seffaf > "$R/caddy/seffaf.log" 2>&1 & echo $! > "$R/caddy/seffaf.pid"
sleep 3
curl -sk -o /dev/null -w "kenar  %{http_version} %{http_code} %{time_total}s\n" "https://localhost:${T}443/"
curl -sk -o /dev/null -w "hizli3g %{http_version} %{http_code} %{time_total}s\n" "https://localhost:$((T+1))443/"
curl -sk -o /dev/null -w "yavas4g %{http_version} %{http_code} %{time_total}s\n" "https://localhost:$((T+2))443/"
curl -sk -o /dev/null -w "API    %{http_code}\n" "https://localhost:${T}443/v1/dogrulama"
