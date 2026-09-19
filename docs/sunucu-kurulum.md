# PVQuant — Sunucu Kurulumu ve Alan Adı Bağlama

Bu kılavuz, PVQuant'ı laptoptan alıp genel IP'li bir sunucuda `https://pvquant.com`
adresinde yayına almak içindir. Sıra önemli: **DNS'i sunucu hazır olmadan
yönlendirme** — Let's Encrypt sertifikayı alamaz ve gereksiz hata döngüsüne girer.

Tahmini süre: ~30 dakika (ilk imaj derlemesi dahil).

---

## 0. Ön koşullar

| Ne | Gereken |
|---|---|
| Sunucu | 4+ vCPU, **16 GB RAM** (8 GB asgari), 320 GB SSD, bol/ölçümsüz trafik |
| İşletim sistemi | Ubuntu 24.04 LTS (veya Debian 12) |
| Erişim | root ya da sudo yetkili kullanıcı, SSH anahtarı |
| Alan adı | pvquant.com — DNS yönetimi Turhost panelinde |

RAM gerekçesi ölçümdür, tahmin değil: worker gece NWP GRIB dosyalarını açarken
ve LightGBM eğitirken sıçrar; 150 santral hedefi varsa 16 GB'ı düşürme.

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
# Sırları ÜRET (kopyalama, üret):
echo "DB_PASSWORD=$(openssl rand -base64 24)"
echo "PVQ_JWT_SECRET=$(openssl rand -hex 32)"
nano .env          # üretilen değerleri ve PVQ_DOMAIN=pvquant.com yaz
```

Yayın öncesi kontrol — **0 dönmeli**:

```bash
grep -c "DEGISTIR\|pvquant_dev\|dev-secret" .env
```

---

## 3. DNS kayıtlarını gir

Turhost panelinde: **Alan Adı Yönetimi → pvquant.com → DNS Yönetimi**

| Tip | Ad | Değer | TTL |
|---|---|---|---|
| A | `@` | sunucunun IP'si | 3600 |
| A | `www` | sunucunun IP'si | 3600 |

Yayılmayı bekle ve **doğrula** (kendi makinenden):

```bash
dig +short pvquant.com A        # sunucu IP'sini döndürmeli
```

Bu komut IP'yi döndürmeden sonraki adıma geçme; Caddy sertifika isteğinde
başarısız olur ve Let's Encrypt hız sınırına takılabilirsin.

---

## 4. İlk yayın

```bash
cd /opt/pvquant
docker compose build            # ilk derleme birkaç dakika sürer
docker compose up -d
docker compose exec api python -m alembic upgrade head   # şema
docker compose ps               # hepsi Up olmalı
```

Sertifikayı izle (ilk istekte alınır):

```bash
docker compose logs caddy --tail 30 | grep -i "certificate\|error"
curl -I https://pvquant.com     # 200 dönmeli, sertifika uyarısı OLMAMALI
```

### İlk yönetici hesabı

```bash
docker compose exec api python -c "
from pvquant.services import auth_service as au
tid, uid = au.tenant_ve_admin_olustur('ŞİRKET ADI', 'siz@sirketiniz.com', 'GÜÇLÜ-PAROLA')
print('kiracı:', tid, 'yönetici:', uid)"
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

Geri dönüş sınaması (yılda bir kez gerçekten dene):

```bash
gunzip -c yedekler/pvq_YYYYAAGG_SSDD.sql.gz | \
  docker compose exec -T db psql -U pvquant -d pvquant
```

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
220 bayt/satır. 150 santralde budama ve TimescaleDB sıkıştırması olmadan
~100 GB/yıl; ikisiyle 10–15 GB/yıl.
