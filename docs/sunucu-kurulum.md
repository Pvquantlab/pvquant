# PVQuant — Sunucu Kurulumu ve Alan Adı Bağlama

Bu kılavuz, PVQuant'ı laptoptan alıp genel IP'li bir sunucuda `https://pvquant.com`
adresinde yayına almak içindir. Sıra önemli: **DNS'i sunucu hazır olmadan
yönlendirme** — Let's Encrypt sertifikayı alamaz ve gereksiz hata döngüsüne girer.

Tahmini süre: ~30 dakika (ilk imaj derlemesi dahil).

---

## 0. Ön koşullar

| Ne | Gereken |
|---|---|
| Sunucu | 4+ vCPU, **16 GB RAM** (8 GB asgari), 300 GB SSD, bol/ölçümsüz trafik |
| İşletim sistemi | Ubuntu 22.04 LTS ya da 24.04 LTS (veya Debian 12) |
| Erişim | root ya da sudo yetkili kullanıcı, SSH anahtarı |
| Alan adı | pvquant.com — DNS yönetimi Turhost panelinde |

RAM gerekçesi ölçümdür, tahmin değil: worker gece NWP GRIB dosyalarını açarken
ve LightGBM eğitirken sıçrar; 150 santral hedefi varsa 16 GB'ı düşürme.

**Sanallaştırma KVM olmalı.** Satın almadan önce sağlayıcıya sor; OpenVZ/LXC'de
Docker çalışmaz. Sunucu gelince ilk komut `systemd-detect-virt` — `kvm` demeli.
İlk kurulumda (22 Eyl 2026, EclitGO VPS ProMax) doğrulandı.

---

## 1. Sunucuyu hazırla

```bash
# sunucuda, root olarak
apt update && apt upgrade -y
apt install -y ca-certificates curl git

# Docker (resmi depo)
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  > /etc/apt/sources.list.d/docker.list
apt update && apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
docker --version && docker compose version
```

### Güvenlik duvarı

Yalnız SSH ve web açık olmalı. API (8000) ve veritabanı (5432) portları
compose tarafında zaten `127.0.0.1`'e kilitli (v2.342) — yine de duvar şart:

```bash
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
ufw status
```

---

## 2. Kodu al ve ayarları yaz

```bash
git clone https://github.com/Pvquantlab/pvquant.git /opt/pvquant
cd /opt/pvquant
cp .env.ornek .env
```

Sırlar **doğrudan dosyaya** üretilir — ekrana basılmaz (v2.352: eski hâli
`echo` ile yazdırıp elle kopyalatıyordu; sır terminal geçmişine, ekran
görüntüsüne ve kaydırma tamponuna düşüyordu):

```bash
sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=$(openssl rand -hex 24)|; \
        s|^PVQ_JWT_SECRET=.*|PVQ_JWT_SECRET=$(openssl rand -hex 32)|" .env
chmod 600 .env
nano .env          # yalnız PVQ_DOMAIN ve (varsa) SMTP alanlarını düzenle
```

`hex` bilinçli: base64'ün `/` ve `+` karakterleri veritabanı bağlantı
adresini parçalar (bkz. `.env.ornek` şerhi).

Yayın öncesi kontrol — **0 dönmeli**:

```bash
grep -v '^#' .env | grep -c "DEGISTIR\|pvquant_dev\|dev-secret"
```

`grep -v '^#'` şart: yer tutucu kontrolünün kendisi `.env.ornek`'te yorum
satırı olarak duruyor ve onu da sayıyordu — eski komut asla 0 dönemezdi.

Sırların yazıldığını **içeriğini göstermeden** doğrula:

```bash
awk -F= '/^DB_PASSWORD=|^PVQ_JWT_SECRET=/{print $1": "length($2)" karakter"}' .env
# DB_PASSWORD: 48 karakter · PVQ_JWT_SECRET: 64 karakter
```

---

## 3. DNS kayıtlarını gir

### ÖNCE isim sunucusu, SONRA kayıt (v2.352 — canlı kurulumda düşülen tuzak)

Turhost iki isim sunucusu ailesi işletir ve **DNS Yönetimi ekranı yalnız
ikincisine yazar**:

| Aile | Ne zaman |
|---|---|
| `cpns1/cpns2.turhost.com` | Turhost'ta **barındırma** hizmeti varsa |
| `dns1/dns2.turhost.com` | Alan adı **başka sunucuya** yönlendirilecekse ← bizim durum |

Alan adı varsayılan olarak `cpns*` ile gelir. Bu hâldeyken DNS Yönetimi
ekranına kayıt girersen ekran kabul eder ama **hiçbir yere yayılmaz** —
`cpns*` o bölgeyi tanımaz, dışarıdan sorgu bomboş döner (SOA bile yok).

**Sıra:** Alan Adı Yönetimi → pvquant.com → **İsim Sunucuları / NS** →
`dns1.turhost.com` + `dns2.turhost.com` → Güncelle. *Sonra* DNS Yönetimi.

Bölgeyi görebildiğini doğrula (bu komut boş dönerse kayıt girmenin anlamı yok):

```bash
dig @dns1.turhost.com pvquant.com SOA +short
```

### Kayıtlar

Turhost panelinde: **Alan Adı Yönetimi → pvquant.com → DNS Yönetimi**

| Tip | Ad | Değer | TTL |
|---|---|---|---|
| A | `@` | sunucunun IP'si | 3600 |
| CNAME | `www` | `pvquant.com` | 3600 |

`www` için A yerine CNAME yeterli; Caddy `www`'yu apex'e kalıcı olarak
yönlendirir (v2.352 Caddyfile). Hazır gelen park kayıtlarından `mail`/`ftp`
CNAME ve MX, posta sunucusu kurulana kadar zararsızdır — sunucuda 25/587
kapalı olduğu için gelen posta gönderene geri döner.

Yayılmayı bekle ve **doğrula** (kendi makinenden):

```bash
dig +short pvquant.com A        # sunucu IP'sini döndürmeli
```

Bu komut IP'yi döndürmeden sonraki adıma geçme; Caddy sertifika isteğinde
başarısız olur ve Let's Encrypt hız sınırına takılabilirsin.

**İsim sunucusu değişikliği saatler sürebilir** (kayıt kuruluşu seviyesi);
A kaydı değişikliği ise dakikalar. Önce NS'i değiştir, beklerken kurulumun
geri kalanını (imaj derleme, şema, ilk yönetici) bitir — hepsi DNS'siz koşar.

---

## 4. İlk yayın

DNS yayılmasını beklerken **Caddy dışındaki her şey kurulabilir** — sertifika
isteyen tek servis Caddy'dir:

```bash
cd /opt/pvquant
docker compose build                                     # birkaç dakika
docker compose up -d --wait db                           # şemadan önce sağlıklı olsun
docker compose run --rm api python -m alembic upgrade head   # şema
docker compose up -d api web worker                      # Caddy HARİÇ
docker compose ps                                        # hepsi Up
curl -s http://127.0.0.1:8000/v1/healthz                 # {"ok":true}
```

### TLS kapısını DNS'siz sına (v2.352)

Caddy'yi gerçek alan adıyla ilk kez başlatmak, aynı anda hem yönlendirmeyi
hem sertifikayı sınamak demektir. Yönlendirmede bir kusur varsa Let's
Encrypt denemeleri boşa gider (saatlik hata kotası vardır). Önce yerel CA
ile prova et — komut satırındaki değişken `.env`'i geçici olarak ezer,
dosyaya dokunmaz:

```bash
PVQ_DOMAIN=localhost docker compose up -d caddy
curl -sk https://localhost/v1/healthz    # {"ok":true}  → API yolu sağlam
curl -sk https://localhost/ | head -c 80 # <!doctype html> → panel yolu sağlam
```

DNS hazır olunca gerçek alan adıyla yeniden oluştur:

```bash
docker compose up -d          # .env'deki PVQ_DOMAIN ile Caddy'yi tazeler
```

Sertifikayı izle (ilk istekte alınır):

```bash
docker compose logs caddy --tail 30 | grep -i "certificate\|error"
curl -I https://pvquant.com     # 200 dönmeli, sertifika uyarısı OLMAMALI
```

### İlk yönetici hesabı

Parola komut satırına YAZILMAZ (v2.352: kabuk geçmişine ve ekran görüntüsüne
düşerdi) — gizli girdiyle sorulur:

```bash
docker compose exec -it api python -c "import getpass; from pvquant.services import auth_service as au; p=getpass.getpass('Parola: '); tid,uid=au.tenant_ve_admin_olustur('ŞİRKET ADI','siz@sirketiniz.com',p); print('kiraci:',tid,'yonetici:',uid)"
```

Girişten sonra panelden **iki adımlı doğrulamayı aç** (Portföy → Hesap ve ekip).

---

## 5. Yedeği kutu dışına çıkar

Gece yedeği otomatik çalışır (`./yedekler`, son 14 kopya) ama **aynı diskte
duruyorsa yedek sayılmaz** — sunucu kaybedilirse yedek de gider. Başka bir
yere günlük kopyala; örnek (kendi makinene):

```bash
# kendi makinende, cron ya da elle
rsync -avz --delete root@SUNUCU_IP:/opt/pvquant/yedekler/ ~/pvquant-yedek/
```

Geri dönüş sınaması (yılda bir kez gerçekten dene). **Dolu veritabanına
basma** — mevcut nesnelerle çakışıp yarıda kalır; geçici boş bir veritabanına
aç ve içeriğine bak:

```bash
docker compose exec -T db createdb -U pvquant geri_test
gunzip -c yedekler/pvq_YYYYAAGG_SSDD.sql.gz | \
  docker compose exec -T db psql -U pvquant -d geri_test
docker compose exec -T db psql -U pvquant -d geri_test -c "SELECT count(*) FROM users;"
docker compose exec -T db psql -U pvquant -d geri_test -c \
  "SELECT count(*) FROM scada_hourly;"   # asıl DB'deki sayıyla karşılaştır
docker compose exec -T db dropdb -U pvquant geri_test
```

Geri yükleme sırasında **3–4 hata satırı görmek NORMALDİR** ve veri kaybı
anlamına gelmez (19 Eyl 2026'da ölçüldü: satır sayıları birebir geri geldi,
iki hypertable yapısıyla kuruldu). Bilinen zararsız hatalar: "ONLY option
not supported on hypertable", "is not a hypertable" (dump'ın sıralama
artıkları — TimescaleDB katalogu tabloları sonradan hypertable'a çevirir)
ve "unrecognized parameter transaction_timeout" (pg_dump 17 istemcisi,
PG16 sunucu). Ölçüt hata sayısı değil, yukarıdaki SATIR SAYISI kıyasıdır.

---

## 6. Yayın sonrası kontrol listesi

- [ ] `https://pvquant.com` açılıyor, sertifika geçerli
- [ ] Panele giriş çalışıyor, 2FA açıldı
- [ ] `docker compose exec api python -m alembic current` → en son sürüm
- [ ] Gece işleri koşuyor: panelde **Veri yükleme → Gece işleri** kartı uyarı vermiyor
- [ ] Bir gün sonra `yedekler/` içinde yeni dosya var
- [ ] SMTP dolduysa: parola sıfırlama isteğinde mektup geliyor
- [ ] `ufw status` → yalnız 22/80/443
- [ ] `docker compose ps` → 5432 ve 8000 `127.0.0.1` üzerinde

---

## Güncelleme (sonraki sürümler)

```bash
cd /opt/pvquant
git pull
docker compose build
docker compose up -d
docker compose exec api python -m alembic upgrade head
```

---

## Bilinmesi gerekenler

**Gece işleri saatleri UTC'dir.** Karne 00:30, yedek 01:15, tahmin 02:00,
alarm 04:00 UTC — İstanbul'da 03:30 / 04:15 / 05:00 / 07:00. Sunucu 7/24
açık olduğu için bunlar artık gerçekten koşar (laptopta koşmuyordu, v2.336
ve v2.339 bu yüzden açılış yakalamaları ekledi).

**150 santral hedefi için önce GEFS düzeltilmeli.** Şu an olasılık topluluğu
verisi santral başına ayrı indiriliyor (`kosu_cek_ve_arsivle` içindeki
`for lat, lon in noktalar: gefs_cek_ve_arsivle(...)`). Tek nokta ~26 dakika;
150 nokta gece penceresine sığmaz. ECMWF ve ICON zaten doğru kalıpta (tek
indirme, çok nokta çıkarımı) — GEFS de aynısına çevrilmeli.

**Disk büyümesi.** Ölçüldü: `forecast_values` 685 bayt/satır, `meteo_uye`
220 bayt/satır. `meteo_uye` zaten 45 günle budanıyor (her yazımda; 150
santralde ~8 GB'da sabitlenir). Sınırsız büyüyen tek tablo `forecast_values`:
150 santralde ~40 GB/yıl — TimescaleDB sıkıştırması açılınca birkaç GB/yıl.
