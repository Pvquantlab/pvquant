# Uzlaştırma kuralı paketi — v2.501 (29.10.2026, canlı)

Commit `adafd74`, CI #610 (4 dk 22 s), dağıtım `ssh` ile api + worker + web imajları (alembic YOK). Canlı: 22/22 JS/CSS ve
index.html referans derlemeyle birebir; `/yontem` 200; canlı api kapsayıcısında `kurallar.kural(1.11.2026)` →
`edt-2026-V100-edta_ayrik+kupst-14907`; worker yeni cron ile başladı (12:35 UTC `kgup_teslim_kontrol`).

Ne değişti, neden, kanıt: commit mesajı. Ayrıntılı raporlar (depo dışı, ürün stratejisi klasörü):
`~/Desktop/PVQuant_GES_Piyasa_Arastirmasi/PVQuant_Urun_Stratejisi/PVQuant_Ilk_Uygulama/` — 01 bulgu doğrulama (birincil
kaynak tablosu), 02 uygulanan değişiklikler (08 paketi M1–M10), 03 test ve kabul (54 vektör, altın çıktı, üç motor),
04 açık konular ve sonraki paket, `kanit/` (kareler, kapı çıktıları, vektör betiği, SHA-256 manifesti).

## Canlıda bekleyen (dağıtım sonrası yapılacak)
- EPİAŞ kimliği tanımlıysa `piyasa_service.geri_doldur()` ile geçmiş fiyat + **sistem yönü** (önceki sürüm yön yazmıyordu).
- `kgup_teslim_kontrol` işinin ilk koşusu (12:35 UTC) `jobs_log`'da; kural seçili santralde alarm.
- F-06 arşiv göçü (`alembic/taslak/`) ayrı mühürde; F-08 DSG motoru sonraki paket.

## Dersler
- Yerel `pvquant-db-1` şeması depo göç geçmişiyle uyumsuz (silinmiş v2417'ye işaret) → DB testleri izole kapsayıcıda
  (`docker run postgres` + `PVQ_DB_URL` + `python -m alembic upgrade head`; `.venv/bin/alembic` shebang bozuk).
- EPİAŞ `system-direction` metindir; `seri()` sayıya çevirip NaN yazıyordu — bulgu kaynağı bekçi değil kod okuma.
- Playwright: scratchpad'e `playwright@latest`, `~/Library/Caches/ms-playwright`'taki mevcut tarayıcılarla; sürüm sabitlemek
  saatlerce indirme bekletti.

---

# İkinci paket — v2.502 (29.10.2026 gece, canlı): KGÜP sürüm arşivi (F-06) + DSG netleşmesi (F-08)

Commit `b74cd8b`, CI #612 (4 dk 19 s). Dağıtım: api + web imajları + **`alembic upgrade head` → v2502_kgup_surum**. Canlı: 22/22 JS/CSS ve
index.html birebir; `kgup_surum` tablosu var, `pvq_app` yetkileri yalnız SELECT/INSERT (değiştirilemez), `pvq_api` S/I/U/D; api günlüğü hatasız.

**DERS (göç):** `docker compose run --rm api python -m alembic upgrade head` **pvq_api** ile koşar ve `permission denied for schema public` verir
(pvq_api'nin CREATE yetkisi yok, v2488 tasarımı). Göç veritabanı sahibiyle koşmalı:
`set -a; . ./.env; set +a; docker compose run --rm -e PVQ_DB_URL="postgresql+psycopg://pvquant:${DB_PASSWORD}@db:5432/pvquant" api python -m alembic upgrade head`
(.env'de 47. satır `PVQ_SMTP_FROM=PVQuant <…>` `source` ile sözdizimi hatası verir ama DB_PASSWORD ondan önce okunur; kalıcı çözüm: değeri tırnaklamak).
İlk denemede api yeni kodla göçsüz ayağa kalktı (CSV indirme o aralıkta 500 verirdi; ~1 dk).

Ayrıntı: `PVQuant_Ilk_Uygulama/02` M11–M12, `03` §7a, `04` (kalan: F-07 geri test maliyet tarafı, müşteri KGÜP içe alma, canlı EPİAŞ kimliği).

# Üçüncü paket — v2.503 (29.10.2026 gece, canlı): uzlaştırma kalemleri geri testi (F-07) + müşterinin bildirdiği KGÜP (F-06 tamamlayıcı)

Commit `2011556`, CI #614 (7 dk 34 s; test işi 7 dk 32 s — yeni C geri test takımı süreyi uzattı). Dağıtım: api + web imajları +
**`alembic upgrade head` DB sahibiyle → v2503_kgup_surum_kaynak** (ilk denemede temiz; v2.502 dersi uygulandı). Worker imajı yenilenmedi
(değişen modüller yalnız api yolunda; worker cron işleri dokunulmadı). Canlı: index.html ve 22/22 JS/CSS birebir; api günlüğü hatasız;
`backtest_service.maliyet_geri_test`, `kgup_arsiv_service.musteri_kaydet/kiyas` canlı kapsayıcıda; yeni uçlar kimliksiz 422 (başlık zorunlu),
sahte jetonla 401, olmayan yol 404.

**Ne:** `GET /v1/plants/{id}/dengesizlik/geri-test?gun=` (Doğruluk kartı «Uzlaştırma kalemleri geri testi — son 12 ay»; başlık «varsayımsal
yeniden hesap; EPİAŞ uzlaştırma sonucu değildir»); `kgup_surum.kaynak` (pvquant | musteri), `POST …/kgup/bildirilen?gun=` (CSV, editör),
`GET …/kgup/kiyas?gun=` (Tahminler «Bildirilen KGÜP ile kıyas»). Karşı-olgu: `parametre_cercevesi(karsi_olgu="2026"|"2026_V100")`.

**Kanıt:** `tests/test_c_geri_test.py` C T1 beş seviye (W15 911.844 = 420.732 + 388.115 + 102.997), T6 S3 (3.202.845 / 3.483.043 / 414.994 /
280.198), karşı-olgu (634.526 / 805.767 / 949.292) ±1 TL birebir; pytest 763 geçti / 1 atlandı (izole DB, göç ileri-geri temiz); web tsc 0,
102 test, oxlint 16/0, build ok. Kareler `PVQuant_Ilk_Uygulama/kanit/kareler/dogruluk-geritest-*`, `tahminler-arsiv-*`.

**Ders:** `.gitignore`'daki `data/` deseni `tests/data/` fixture'larını yok sayıyordu (eski fixture'lar `-f` ile girmiş); `!tests/data/` eklendi.

**Kalan:** canlı EPİAŞ kimliği/yön geçmişi kontrolü (üretim okuma izni); 24 ay saklama/temizlik işi; DSG üyelere dağıtım anahtarı; TPYS şablonu.
Ayrıntı: `PVQuant_Ilk_Uygulama/02` M13–M14, `03` §7b, `04`.

# Dördüncü paket — v2.504 (29.10.2026 akşam, canlı): arşiv saklama işi, DSG dağıtım anahtarı, «bildirildi» rozeti, panel dili turu

Commit `2521e9a`, CI #616 (7 dk 31 s). Dağıtım: **api + worker + web** imajları (worker kodu değişti: aylık `kgup_arsiv_temizlik`); göç yok.
Canlı: index.html ve 22/22 JS/CSS birebir; api ve worker günlükleri hatasız; `kgup_saklama_ay` 24, ISIM_TR etiketi, `temizle`, dağıtım
anahtarları ve worker işi kapsayıcılarda doğrulandı; `/v1/portfoy/dsg?anahtar=` sahte jetonla 401, olmayan yol 404.

**Ne:** `kgup_saklama_ay` (24 ay, taban 15, 0 = silme yok) + worker aylık iş (jobs_log detail'e sonuç; `_logla_tek` dönen metni kaydeder);
`dsg_saatlik(dagitim_anahtari=sapma|esit|uretim)` → üye başına EDT grupta / netleşme farkı / para payı, API `anahtar`, Portföy «DSG
maliyetinin üyelere dağılımı» seçici + tablo; Portföy program satırında «bildirildi» rozeti (kgup_surum kaynak=musteri). Panel dili turu:
**DSG = Dengeden Sorumlu Grup** (önceki «dengeleme grubu» yanlıştı), «dengesizlik maliyeti / enerji dengesizlik tutarı», «KGÜP sapma tutarı ·
KÜPST», «eksi = santral öder», «varsayımsal karşılaştırma»; parantez yerine orta nokta; `Bilgi`/`BilgiliEtiket` simgeleri; formüller açılır alanda;
dil bekçisine 5 desen.

**Kanıt:** test_temizle_saklama, test_dsg_dagitim_anahtari (+ kapı 422), test_program_durumu_bildirildi; pytest tam takım 765 geçti / 1 atlandı
(+ etiket düzeltmesi sonrası bekçiler 5/5); web tsc 0, 102 test, oxlint 16/0, build ok; tarayıcı 1440/375 taşma 0, açık/koyu, görsel ölçümler
öncekiyle aynı. Ayrıntı `PVQuant_Ilk_Uygulama/02` M15–M18, `03` §7c–7d.

**Kalan:** canlı EPİAŞ kimliği/yön geçmişi, jobs_log zamanlama ve KGÜP alarm kanıtı → `PVQuant_Ilk_Uygulama/canli-kontrol.sh` (salt okuma,
kullanıcı koşturur); TPYS resmî şablonu (pilot müşteri); WMAPE duyarlılık üreteci; 2027 rejimi parametreleri.

# Beşinci paket — v2.505 (29.10.2026 gece, canlı): fiyat akışı dayanıklılığı, gün öncesi PTF, EPİAŞ istemcisi, arıza alanı, alarm adları

Commit `c0e7772`, CI #618 (4 dk 32 s). Dağıtım: api + worker + web imajları; göç yok. Canlı: index.html ve 22/22 JS/CSS birebir; api/worker
günlükleri hatasız; `gun_oncesi_ptf` işi ve etiketi, `UC_GET`/`VARSAYILAN_EK`, `geri_doldur(bugun=)`, alarm etiketi «Tahmin doğruluğu düştü»
kapsayıcılarda doğrulandı; `/eak` ve `/alarm-kurallari` sahte jetonla 401. Gün öncesi PTF işi ilk kez 30.10 14:35 TSİ'de koşar (elle tetiklenmedi:
üretim yazması).

**Aynı gün canlıda yapılan (kod dışı):** `canli-kontrol.sh` ile salt okuma; kullanıcı onayıyla `geri_doldur("2025-01-01","2026-10-28")` → 15.984 saat
PTF/SMF/yön eksiksiz (önce yön 0 saatti); uzlaştırma kartları artık gerçek fiyat ve yönle. EPİAŞ uçları canlı kimlikle sınandı (02 M19).

**Ne:** `geri_doldur` bitiş düne kırpılır, parça hatası atlanır (`kismi`/`hatali`); `kaydet` COALESCE; `gun_oncesi_ptf` (kaynak epias_gop);
`epias.santral_listesi()` GET, `dpp` region=TR1; `EakIstek.ariza_sayisi_ay` + Santralim alanı; alarm kuralı yedek sözlüğü + ipuçları + birimli eşikler.

**Kanıt:** pytest 771 geçti / 1 atlandı; web tsc 0, 103 test, oxlint 16/0, build ok; `alarm-sozluk.test.ts` panel ↔ arka uç. Ayrıntı
`PVQuant_Ilk_Uygulama/02` M19, `03` §7e.

**Kalan:** TPYS resmî şablonu (EPYS hesabından indirilecek; kamuya açık değil — 04 #5); `uevcb-list` ve `renewables/imbalance-cost` gövdesi;
EPİAŞ kimliği için Ayarlar alanı (sır saklama kararı); 2027 rejimi parametreleri; WMAPE duyarlılık üreteci.

# Altıncı paket — v2.506 (30.10.2026, canlı): bildirim dosyası biçimi müşterinin EPYS dosyasından öğrenilir

Commit `edc184b`, CI #620 (4 dk 25 s). Mühür iki parçaya bölündü: commit/CI 30.10 gece, dağıtım 30.10 gündüz — ssh port 22 ev IP'sinden
~12 saat zaman aşımı verdi. Dış port denetleyicisi 22'yi açık gördü (engel IP'ye özgü); telefon hotspot'uyla bağlantı anında açıldı.
Dağıtım: api + worker + web imajları (kgup modülü worker'ın program işlerinde de kullanılır), alembic yok. Canlı: index.html ve 22/22 JS/CSS
birebir (referans edc184b geçici çalışma ağacından); api ve worker kapsayıcılarında `kgup.sablon_ogren`/`Sablon.sira` var; api günlüğü hatasız;
`POST/DELETE …/kgup/sablon` kimliksiz 422.

**DERS:** «ssh timed out» sunucu kapalı demek değil; önce dışarıdan port denetimi, sonra hotspot/VPN. Saatlerce bekçi koşturmak boşa gitti.
Kalıcı öneri: CI'dan ssh ile dağıtım işi (gizli anahtar GitHub'da; açık karar).

Ayrıntı: `PVQuant_Ilk_Uygulama/02` M19–M21, `03` §7f, `04` (TPYS şablonu EPİAŞ Yardım Masası yanıtına bağlı).
