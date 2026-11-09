# Saha toplayıcısı (edge) — kurulum ve işletim (v2.561, 09.11.2026)

**Ne.** Modbus TCP 502 internete açılmaz. Sahada küçük bir toplayıcı (Linux kutusu, UPS'li, kalıcı disk) inverter/kayıt cihazını YALNIZ OKUR, yerel
journal'a yazar ve PVQuant'a HTTPS 443 üzerinden dışa doğru gönderir. Kesintide veri sahada birikir; bağlantı dönünce aynı sıra numaralarıyla yeniden
gönderilir; sunucu idempotent olduğundan çift sayım olmaz. Sunucu toplayıcıya hiçbir komut göndermez (tek yön).

**Kimlik (E2).** Santralim › Veri kaynakları › Saha toplayıcısı: «Toplayıcı anahtarı üret». Anahtar tek santrala bağlıdır, bir kez gösterilir, sunucuda
yalnız özeti durur; iptal edilince gelen veri reddedilir. Anahtar sahada `/etc/pvquant/toplayici.key` (0600) dosyasında durur.

## Kurulum (saha)

```bash
python3 -m venv /opt/pvquant-edge && /opt/pvquant-edge/bin/pip install "pvquant @ git+https://github.com/<org>/pvquant"   # ya da wheel
/opt/pvquant-edge/bin/python scripts/edge_toplayici.py --host 192.168.10.5 --port 502 --birim 1 --cihazlar 2,3 \
  --sunucu https://pvquant.com --anahtar-dosya /etc/pvquant/toplayici.key --journal /var/lib/pvquant-edge --periyot 60 --tek-tur
```

`--tek-tur` bir okuma ve bir gönderim yapar (kabul testi). Sürekli çalışma için systemd birimi (Restart=always). Journal dizini kalıcı diskte olmalı.

## Journal ve ack (E1)

- Her örnek `sira` (artan) ile `YYYY-MM-DD.jsonl` dosyasına fsync ile yazılır; `sira.txt` son sırayı, `ack.txt` sunucunun kabul ettiği son sırayı tutar.
- Gönderim partisi ≤200; yanıt `ack_sira` kalıcı yazım sonrası döner; toplayıcı yalnız ack'a kadar olanları gönderilmiş sayar.
- Aynı sıra farklı içerikle gelirse sunucu «çatışma» döner ve ack ilerlemez (journal bozulması işareti; elle inceleme).
- Ack'lanmamış satır içeren dosya hiçbir koşulda silinmez. Tamamı ack'lanmış ve `--sakla-gun`'den eski dosyalar silinir.
- Journal `--azami-mb` eşiğini aşınca `[ALARM]` satırı yazılır; sessiz silme yoktur. Kalıcı bağlantı kesintisi = disk dolar = alarm; veri kaybı değil.

## Ağ ve mTLS

Toplayıcı yalnız dışa 443 açar. TLS zorunlu (Caddy, Let's Encrypt). İstemci sertifikası (mTLS) bu sürümde zorunlu değil; araçları hazır:

- `scripts/edge_ca.sh kur /etc/pvquant-edge-ca` → kök CA ve CRL; `ver <dizin> kabin-a 365` → istemci anahtarı + sertifikası; `iptal <dizin> kabin-a` → CRL yenilenir; `liste`.
- Caddy bloğu: `docs/edge/Caddyfile.edge-mtls.snippet` (ayrı alt alan adı önerilir; `client_auth require_and_verify`, CA ve CRL dosyaları).
- Toplayıcı: `--sertifika istemci.crt --sertifika-anahtari istemci.key`.
- Döndürme: yeni sertifika `ver` ile verilir, toplayıcıya konur, eski `iptal` edilir; CRL Caddy'ye kopyalanıp yeniden yüklenir. Anahtar (Santralim) ve sertifika iptali birlikte yapılır.
- İmzalı toplayıcı güncellemesi bu sürümde yok: toplayıcı paketi git etiketinden/wheel'den kurulur; sürüm `toplayici_surum` alanıyla sunucuya bildirilir.

Eski metin (bilgi): 

Toplayıcı yalnız dışa 443 açar. TLS zorunlu (Caddy, Let's Encrypt). İstemci sertifikası (mTLS) bu sürümde zorunlu değil; etkinleştirmek için Caddyfile'da
`/v1/edge/*` yoluna ayrı bir `tls { client_auth { mode require_and_verify; trusted_ca_cert_file /etc/caddy/edge-ca.pem } }` bloğu ve toplayıcıda
`--sertifika/--sertifika-anahtari`. Sertifika döndürme ve iptal (CRL) işletim prosedürü ilk çok sahalı müşteriyle yazılır; anahtar iptali bugün
uygulamadadır (E2).

## Sunucu tarafı

`POST /v1/edge/ornekler` (başlık `X-Toplayici-Anahtar`), gövde `{"ornekler": [{sira, ts_utc, cihaz_id, sinir, profil, guc_w, enerji_wh, dc_guc_w, durum_kodu, olaylar, kisit_yuzde}]}`.
Örnekler `canli_ornek`'e `kanal='edge'` ile yazılır; saatlik toplama aynı motor (tam/kısmi ayrımı, gölge görünüm, revizyon). Defter: `edge_alim`.
