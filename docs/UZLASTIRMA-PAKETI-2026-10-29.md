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

# Yedinci paket — v2.507 (30.10.2026, canlı): gün içi revize program önerisi (F-10) + EPİAŞ piyasa verisi durumu kartı

Commit `74dee5a`, CI #622 (3 dk 58 s). Dağıtım: api + worker + web imajları (yeni cron `kgup_revizyon_kontrol`, saat 04–15 UTC :10), alembic yok.
Canlı: index.html ve 22/22 JS/CSS birebir (referans 74dee5a geçici çalışma ağacından); `revizyon_service.oner` api ve worker kapsayıcılarında;
worker günlüğünde iş kaydı; `GET …/kgup/revizyon` kimliksiz 422; `GET /v1/piyasa/durum` kimlik tanımlı; api günlüğü hatasız.

Kapsam: revizyon_service (program ↔ güncel beklenti, eşik max(%10·program, %2·kurulu), revizyon son anı = teslimat − 30 dk, kayıt yazmaz),
seçimlik alarm «Program revizyonu önerisi», Tahminler › «Bugünün programı — revizyon önerisi» kartı, Santralim alarm sözlüğü/eşikleri,
Ayarlar › «EPİAŞ piyasa verisi bağlantısı» kartı. İnceleme düzeltmeleri: sahte API GİP örneği arka uçla hizalandı (11:00/11:30);
alarm açıklaması «07:10–18:10 arası her saat».

Ayrıntı: `PVQuant_Ilk_Uygulama/02` M21, `03` §7g, `04` #15 ve #12 kapandı.

# Sekizinci paket — v2.508 (30.10.2026, canlı): geri testte WMAPE hata duyarlılığı (04 #2)

Commit `e059569`, CI #624 (7 dk 27 s). Dağıtım: api + worker + web imajları (üç imaj aynı Dockerfile'dan; sürüm kayması olmasın diye hepsi), alembic yok.
Canlı: index.html ve 22/22 JS/CSS birebir (referans e059569 geçici çalışma ağacından); `backtest_service.wmape_duyarlilik_df` api kapsayıcısında;
api günlüğü hatasız.

Kapsam: santralin kendi saatlik hata deseni hedef WMAPE'ye ölçeklenir (5/8/12/15/20 + gerçek), 0–kurulu güç kırpması, rastgele üretim yok;
`maliyet_geri_test_df` çıktısına `duyarlilik`; Doğruluk › geri test kartı › «Hata duyarlılığı · varsayımsal» açılır tablosu, «öngörü ya da
taahhüt değildir» notu. Testler: `tests/test_duyarlilik.py` (2), tam takım 778/1 atlandı.

Ayrıntı: `PVQuant_Ilk_Uygulama/02` M22, `04` #2 kapandı.

# Dokuzuncu paket — v2.509 (30.10.2026 gece): CI'dan ssh ile dağıtım işi

Commit `de04917`, CI #626 (4 dk 6 s). Sunucu dağıtımı yok (imaj değişmedi; yalnız `.github/workflows/dagitim.yml` + `docs/CI-DAGITIM.md`).
`Dağıtım` iş akışı Actions listesinde. **İlk gerçek koşu (30.10 gece, Dağıtım #1, imaj `web`): BAŞARILI, 18 s** — gizli değişkenler
kullanıcı tarafından eklendi (yalnız dağıtım için ed25519 anahtar, sunucuda `authorized_keys`), beş adım yeşil (gizli değişken kontrolü, ssh
anahtarı + sabit sunucu kimliği, sunucuda pull/build/up, HTTPS 200, anahtar silme); sunucu HEAD `ef52c84`'e çekildi; web imajı önbellekten
aynı çıktığı için kapsayıcı yenilenmedi (beklenen: v2.508'den beri web kaynağı değişmedi). Dağıtım artık tek makineye/IP'ye bağlı değil. Kapılar: `yaml.safe_load` iki iş akışında geçerli, actionlint 0 hata,
sırrı yazdıran adım yok.

Neden: 30.10'da geliştirici IP'sinden port 22 saatlerce erişilemedi (dışarıdan açıktı); dağıtım tek makineye/IP'ye bağlı kalmamalı.

# Onuncu paket — v2.510 (31.10.2026, canlı): mevzuat araştırması çelişkileri (Ç1–Ç5) + dayanak metinleri + Şeffaflık uç gövdeleri + panel dili

Commit `676fb13` (CI #629, 7 dk 43 s) + rötuş `fb25a8d` (CI #630, 5 dk 51 s). Dağıtım: api + worker + web imajları (ssh ile; port 22 bu ağdan açıktı), alembic yok.
Canlı: index.html ve 22/22 JS/CSS birebir (referans fb25a8d); `kurallar._AFL_ZINCIRI`, `kupst_kurali(luy_istisna=…)`, `epias.UC_ZORUNLU`
api ve worker kapsayıcılarında; api günlüğü hatasız; `PUT /eak` kimliksiz 422.

Kaynak: `~/Desktop/PVQuant_Acik_Konular_Arastirma` (Opus + ultracode; 17 araştırma + 17 doğrulama ajanı; 114 belge; OZET.md). Sonuç: 2023–2026
sayısal parametrelerinde çelişki yok. İşlenenler: Ç1 `afl()` 1.9.2022 öncesi (RG künyeli 35 halka; 600–4.000, formüllü aylar 563–1.745);
Ç2 lisanssızda net sapma yok (14907 Md.1(3)); Ç3 LÜY m.5(1)(ç),(d),(e) santral ayarı (14907 Md.5; motor → API → Santralim, yalnız iletim
lisanssız segmentte görünür); Ç5 `kupst-7524`; `dsg_esigi()` etiketleri; `BELIRSIZ_2027_GEREKCE`; 2025 k/l dayanağı EPDK 4-16180 taslağı.
`kgup.py`: şablon TPYS'de (CAPTCHA), EPYS dışa aktarımı uyarısı. `epias.py`: uevcb-list {organizationId, startDate}; organization-list ve
uevcb-list-by-power-plant-id; «v1.16.4» notu düzeltildi.

Panel dili (kullanıcı kararı): «Emre amade kapasite» kartı → «Program sınırları»; alan «Verilebilecek en yüksek güç (EAK), kW», yer tutucu
«boşsa AC sınırı»; resmî terim açıklamada bir kez; «kullanılabilir güç» kullanılmadı (Kullanılabilirlik ölçütüyle çakışır).

Hâlâ belirsiz/kullanıcıda: #9 2027 rejimi, #10 2027 DSG oranı (Kasım–Aralık RG izleme), #14 1.11.2026 öncesi portföy katsayısı, #5 TPYS
şablon içeriği (CAPTCHA), #11 canlı sınama (uevcb-list, imbalance-cost), #12 kimlik girişi kararı.

Ayrıntı: `PVQuant_Ilk_Uygulama/02` M23, `04` (#5, #8, #9, #10, #11, #14).

# On birinci paket — v2.511 (31.10.2026, canlı): toplayıcı/GTŞ portföyünde KÜPST UEVÇB bazında (04 #14) + Şeffaflık uçları canlı sınama (#11)

Commit `8e3739f`, CI #632 (7 dk 32 s). Dağıtım: api + web imajları (ssh ile), alembic yok. Canlı: index.html ve 22/22 JS/CSS birebir (referans 8e3739f);
`dengesizlik.portfoy_kupst_saatlik` api kapsayıcısında; `GET /v1/portfoy/kupst` kimliksiz 422; api günlüğü hatasız.

Kapsam: dağıtıma bağlı lisanssız santraller `params_json.uevcb` ile UEVÇB'ye gruplanır (boş kod → «tek birim varsayıldı»); birim başına program ve
üretim toplanır, sapma brüt (Karar 14907 Md.1(3)); KÜPSM = max(|ΣG − ΣK| − m·ΣK, 0), KÜPST = KÜPSM·max(750, PTF, SMF)·n (1.11.2026'dan 0,25 / 0,01;
öncesi hesaplanamaz). Santrallere dağılım anahtarı sapma | üretim | kurulu güç | eşit, «mevzuatta tanımsız · sözleşmeye bağlı» etiketiyle
(bulgular/14.md §14.4: mevzuatta anahtar yok). Portföy sayfasında kart, yalnız bu segmentte santral varsa.

#11 canlı sınama (sunucu, kayıtlı kimlik, yalnız okuma): organization-list 692 kuruluş; uevcb-list {organizationId, startDate} 200, eski gövde 400
(neden teyit); uevcb-list-by-power-plant-id 200; imbalance-cost yalnız ≤30.04.2016 (sonrası 400 (BUS)SEF1181) → eski uç, güncel YEKDEM kaynağı
değil; `epias.py` notları. #11 kapandı.

İnceleme düzeltmeleri: sahte verinin KÜPST büyüklüğü katsayıyla tutarsızdı (41,2 → 4,1 bin TL); dört dağıtım anahtarı tarayıcıda doğrulandı.

Kalan (#14): `uevcb-list` ucundan otomatik UEVÇB eşlemesi (organizationId gerekir); 1.11.2026 öncesi için isteğe bağlı duyarlılık senaryosu.
Ayrıntı: `PVQuant_Ilk_Uygulama/02` M24, `04` #11 ve #14.

# On ikinci paket — v2.512 (31.10.2026, canlı): KGÜP dosyası TPYS resmî şablonuyla birebir (04 #5) + EAK ayrı dosya (TPYS EAK.csv)

Commit `e1c4a55`, CI #634 (5 dk 38 s). Dağıtım: api + web imajları (ssh ile), alembic yok. Canlı: index.html ve 22/22 JS/CSS birebir (referans e1c4a55);
api kapsayıcısında varsayılan KGÜP çıktısı 204 bayt «Saat,Miktar / 00:00,0 …» BOM'suz, EAK dosyası CRLF «0,0,,12.5,,,,», `TAKVIM.eak_acilis` 09:00;
`GET /v1/plants/{id}/kgup?fmt=eak` kimliksiz 422; api günlüğü hatasız.

Kaynak: kullanıcı 30.10.2026'da TPYS giriş sayfası › Duyurular › «CSV Şablonları» eklerini (KGUP.csv 146797, EAK.csv 146796) ve 19.02.2025 / 20.11.2025
duyurularının docx eklerini (648549, 763302, 763303) CAPTCHA'yı çözerek indirdi (`PVQuant_Acik_Konular_Arastirma/kaynaklar/`, bulgular/05.md son bölüm);
KGUP.csv ve EAK.csv `tests/data/tpys/` altında test sabiti.

Bulgu: KGUP.csv = «Saat,Miktar», 24 satır «HH:00», virgül, LF, BOM yok; tarih ve UEVÇB dosyada yok. EAK.csv = 8 kolon (Saat 0–23 tam sayı, Miktar,
ic_tuketim, kaynak_yetersizligi, iklim_verim, mucbir, dissal, guvenlik), boş hücre = yok, CRLF. PVQuant'ın eski varsayılanı (5 kolon, «;», «,», BOM)
TPYS'ye olduğu gibi yüklenemezdi; EAK ayrı ekran (09:00–15:30) ve ayrı web servis (setEak).

Kapsam: `Sablon` varsayılanı TPYS (saat_bicim «%H:00», bom boş, kesir boş); v2.506–v2.511 arasında öğrenilmiş müşteri şablonları eski çıktıyı
bayt bayt korur. `eak_csv_metni`: kurulu güç − EAK − iç tüketim → «kaynak_yetersizligi» (TPYS Bildirim Dokümanı; GES gece kurulu gücün tamamı).
`csv_oku` «HH:00» ve eski «;» dosyalarını okur. Panel: «KGÜP (CSV)» + «EAK (CSV)»; vitrin ve panel metinlerindeki «EPYS dosyasından öğrenilir» kaldırıldı.

İnceleme düzeltmeleri: piyasa takvimi bölümündeki bayat EPYS cümlesi, biçim açıklaması (EAK ayrı), kıyas tablosunda saat «HH:00».

Kalan (düşük): ondalık ayraç şablonda örneklenmemiş (nokta varsayıldı); dengeleme birimi çeyrek satırı TPYS'de doğrulanmadı; EAK dosyası arşivlenmiyor.
Ayrıntı: `PVQuant_Ilk_Uygulama/02` M25, `04` #5.

# On üçüncü paket — v2.513 (31.10.2026 gece, canlı): bülten fiyatlarının birincil doğrulaması (04 #4) + geçici m.39 etiketi + EAK dosyası arşivi + EPİAŞ'tan UEVÇB arama (04 #14 kalan)

Commit `7679d83`, CI #636 (5 dk 39 s). Dağıtım: api + web imajları (ssh ile) + **`alembic upgrade head` DB sahibiyle → v2513_kgup_surum_eak**
(ilk denemede temiz; `alembic current` = head). Canlı: index.html ve 22/22 JS/CSS birebir (referans 7679d83); api kapsayıcısında `gecici_m39_notu`
(2026 metin / 2027 None), `piyasa_service.uevcb_ara`, `kaydet` kaynak kapısı «pvquant|musteri|eak»; `GET /v1/epias/uevcb-ara` ve `?fmt=eak` kimliksiz 422;
api günlüğü hatasız. Not: `.env` kaynaklanırken 47. satır (`PVQ_SMTP_FROM=PVQuant <…>`) kabuk hatası veriyor; önceki satırlar (DB_PASSWORD) yüklendiği için
göç çalıştı — ileride o satır tırnaklanmalı.

#4 (KAPANDI): EPİAŞ Günlük Bülten 26.01.2026 ve 26.10.2026 PDF'leri web-fetch ile indirildi (ssh o saatte IP engeliyle kapalıydı, sunucuya gerek
kalmadı); `pdftotext -layout` ile «Saat PTF SMF Sistem Yönü» ve «Saatlik Kontrat … Dengesizlik Fiyatı (pozitif/negatif)» tabloları okundu;
`birim_fiyatlar()` bültenin PTF/SMF/yönüyle 45/45 saatte ±0,011 TL içinde (en büyük fark 0,0043 TL; AFL 3.400/4.500 dalları dâhil; V/B dalı yok).
Üç saatte metin çıkarımı yön okunu düşürdü; o saatlerde bülten fiyatını üç yönden yalnız biri tutturuyor. Şeffaflık API'sinde «ptf-smf-sdf» ucu yok
(rapor adı); bülten birincil kaynak. Kanıt `PVQuant_Ilk_Uygulama/kanit/bulten-kiyas-*`.

Kapsam: `GECICI_M39_NOT/gecici_m39_notu` → `dsg_ozet.gecici_m39` + dipnot cümlesi; Portföy DSG çipi «· dağıtım/GTŞ DSG'sinde %100». EAK dosyası
`?fmt=eak` ile KGÜP gibi değiştirilemez sürüm kaydı (kaynak 'eak', kantil 'eak'); sürüm geçmişinde «EAK» rozeti. `piyasa_service.kuruluslar()`
(6 saat önbellek) + `uevcb_ara()`; `GET /v1/epias/uevcb-ara?kurulus=`; `segment_bilgisi.uevcb`; Santralim «UEVÇB kodu» ayarı (kod + Kaydet,
EPİAŞ'ta ara → aday → kaydet).

İnceleme düzeltmeleri: girdi+düğme satırları, adaylar tek satır, «Kaydedilemedi» yeşil boyanıyordu; DSG dipnotuna m.39 cümlesi; sahte EAK satırı.
Kalan (isteğe bağlı): 1.11.2026 öncesi dönem için toplayıcı KÜPST duyarlılık senaryosu. Ayrıntı: `PVQuant_Ilk_Uygulama/02` M26, `04` #4 ve #14.

## v2.513 rötuş (31.10.2026 gece, canlı): DSG dipnotunda geçici m.39 cümlesi doğru yere; KGÜP kartında şablon durumu uyarı değil

Commit `d1d52a9`, CI #638 (7 dk 19 s). Dağıtım: yalnız api imajı (ssh; ev ağından 22. port kapalı olduğu için kullanıcı ağ değiştirdi); web ve göç yok.
Kapsayıcıda `kurallar.GECICI_M39_DIPNOT` var, `dsg_ozet` dipnota ekliyor, `uret` uyarı listesinde `SABLON_DURUMU` yok; günlük hatasız.
Kullanıcının canlı incelemesi bulmuştu: cümle `simulasyon()`'daki ilk `out["not"]` bloğuna girmişti (etkisiz); şablon durumu v2.510 kalıntısı
olarak kırmızı uyarı listesindeydi. DERS: sahte API dipnotu fixture'dan verdiği için önizleme servis metnini doğrulamaz; yama anchor'u fonksiyona
özgü seçilmeli. Ayrıntı: `PVQuant_Ilk_Uygulama/02` M26 rötuş.

# On dördüncü paket — v2.514 (31.10.2026, canlı): tahmin grafiğinde «AC …» etiketi eksen başlığıyla çakışmıyor

Commit `ee14d9e`, CI #640 (4 dk 9 s). Dağıtım: yalnız web imajı (ssh); api ve göç yok. Canlı: index.html ve 22/22 JS/CSS birebir (referans ee14d9e);
web günlüğü hatasız. Kullanıcı canlıda görmüştü: AC sınırı tavanın yarısına denk gelince (10.000 / 20.000) eksen sütunundaki «AC 10.000»
etiketi dikey «Güç [kW]» başlığının üstüne biniyordu. Etiket artık çizim alanının sağ kenarında, kesikli çizginin hemen üstünde (AC üstünde seri
bulunmaz; «şimdi» çizgisi sağ uca nadiren gelir); 1280 ve 375 px önizlemede doğrulandı. Ayrıntı: `PVQuant_Ilk_Uygulama/02` M27.

# On beşinci paket — v2.515 (31.10.2026 gece, canlı): yönetim panelinde santral envanteri uzlaştırma hazırlığı + denetim tabloları düzeni

Commit `7e224e1`, CI #642 (7 dk 39 s). Dağıtım: api + web imajı (ssh; ev ağından 22. port kapalı olduğu için kullanıcı ağ değiştirdi); göç yok —
pvq_api BYPASSRLS ve varsayılan ayrıcalıklarla `kgup_surum`'u okur. Canlı: index.html ve 23/23 JS/CSS birebir (referans 7e224e1); api ve web
günlüğü hatasız; api kapsayıcısında `sistem_service` yeni kodu taşıyor (kgup_yarin). Not: referans derleme proje dışındaki klasöre yazılınca Vite
klasörü boşaltmıyor; eski parçalar «farklı» sayıldı → referans klasörü her mühürde silinip yeniden derlenir.
Kapsam: `sistem_service.santraller` → segment / uevcb / kgup_yukumlu + `kgup_yarin` (yarının İstanbul teslim günü: öneri sürümü / bildirilen / EAK)
+ «segment_yok» bayrağı; `platform_service.kiraci_detay` santral segmenti. Sistem › Santral envanteri yedi sütun: kurulu güç adın altında künye,
«Segment / UEVÇB» tek hücre (düz mono kod), «KGÜP yarın» rozetleri, son hata bağlantısı Sorun'un altında; Müşteri detayı › Santraller aynı hücre.
Denetim izi / Son işlemler: ayrıntı çipleri keep-all, aktör e-postası yalnız «@» sonrasında kırılır, platform santral tablolarında oluk 14 px.
İnceleme düzeltmeleri (kullanıcı ekranları): envanter 1438 px'te 1527 px'e taşıyordu → dokuz sütun yediye, 1045/1045 kaydırmasız; UEVÇB kodu
çipin 12 px boşluğuyla içeri kayıyordu → `.kunye-not.kod-duz`. DERS: aynı sayfada birden çok `table.veri.santral` var; ölçümde tabloyu thead
metniyle seç (ilk «1047/1047» iddiası Üretici işler tablosuna denk gelmişti).
Kalan: 04 D #3–#7 (üretici işler tazeliği, piyasa kartı yön/kimlik, açık alarm KPI, kullanım KGÜP sütunları, denetim izine yeni eylemler).
Ayrıntı: `PVQuant_Ilk_Uygulama/02` M28, `04` D.

# On altıncı paket — v2.516 (31.10.2026 gece, canlı): yönetim paneli boşlukları #3–#7 — izlenen işler, piyasa kartı, açık alarm, kullanım, denetim

Commit `8273ebc`, CI #644 (7 dk 31 s). Dağıtım: api + web imajı (ssh; ev ağından 22. port kapalı, kullanıcı ağ değiştirdi); göç yok (alerts, kgup_surum,
jobs_log mevcut tablolar). Canlı: index.html ve 23/23 JS/CSS birebir (referans 8273ebc, klasör silinip derlendi); api ve web günlüğü hatasız; api
kapsayıcısında `IZLENEN_ISLER` (13) ve `alarmlar` doğrulandı.
Kapsam: (#3) `sistem_service.IZLENEN_ISLER` — gün içi tahmin ve revizyon kontrolü 30 sa, günlük işler 36 sa, aylık temizlikler 35 gün; durum kodu
ok / esik_asimi / henuz_yok / beklenmiyor; müşteri hükmü (URETEN_ISLER) değişmedi; Sistem KPI'ı ve Genel bakış şeridi izlenen aşımlarını uyarı sayar,
kartta ikinci tablo. (#4) piyasa özeti kimlik / yön ufku / 7 günlük yönlü saat / gün öncesi PTF ufku; yön fiyatın 24 saatten fazla gerisindeyse ya da
kimlik yoksa kart uyarır. (#5) `alarmlar` + `GET /v1/yonetim/alarmlar` — okunmamış ve 7 günden yeni (müşteri tanımı), kural etiketi arka uçtan; Genel
bakış beşinci KPI. (#6) kullanım ay toplamı ve günlük kırılımda kgup (kaynak pvquant) ve kgup_bildirilen (kaynak musteri); anahtar/webhook/son API
müşteri adının altına künye (1440'ta 1060/1060). (#7) EYLEMLER_MUSTERI +7 ve altı uçta denetim kaydı (ayrıntı: gün, sürüm, yeni_surum, kantil, kanal,
dosya adı, biçim, segment/UEVÇB, EAK alanları; içerik ve sır yok); SOZLUK.eylem +7; uzun ayrıntı değeri çipte anahtarın altına iner.
İnceleme düzeltmeleri: sahte piyasa fixture'ı gerçekleşen fiyatı yarına uzatıyordu (düne çekildi); «yeni: true» → `yeni_surum`. DERS: dil bekçisi
dizgelerde «taze/bayat» yasaklar — API durum kodlarını görünen Türkçe sözcük yapma; bekçi testleri ton ifadelerini kilitler, değişince testi niyetle
güncelle. 04 D listesi (#1–#7) kapandı. Ayrıntı: `PVQuant_Ilk_Uygulama/02` M29, `04` D.

# On yedinci paket — v2.517 (31.10.2026 gece, canlı): uzlaştırma hesabı fiilî programla — bildirilen KGÜP, piyasa pozisyonu, saatlik döküm (CSV/XLSX), GÖP'e esas sürüm, DSG üye KÜPST

Commit `ee38ab7`, CI #646 (4 dk 44 s). Dağıtım: api + web imajı (ssh; bu kez 22. port açıktı, ağ değişimi gerekmedi); göç yok (params_json alanları,
mevcut kgup_surum). Canlı: index.html ve 23/23 JS/CSS birebir (24/24; referans ee38ab7, klasör silinip derlendi); api ve web günlüğü hatasız; api
kapsayıcısında `dokum_xlsx` / 21 kolon ve `pozisyon_ayari` («sabit 2,5 MWh/saat») doğrulandı, saatlik uç yönlendiriliyor.
Kaynak: GES sahibi ihtiyaç araştırması yol haritası P2a (ENV-F02: program = PVQuant P50 varsayımı). Kapsam: `bildirilen_serisi` (kgup_surum
kaynak='musteri', teslim günü başına son sürüm) + `pozisyon_ayari` (program | uretim | sabit MWh/saat); `saatlik_hesap` programı bildirilen varsa
ondan kurar, budup = program, pozisyon ayrı; ay/toplamda tolerans_disi_saat, kupsm_mwh, bildirilen_saat ve yanıtta «program» bloğu. Saatlik döküm
`dokum_df/dokum_csv/dokum_xlsx` + `GET /v1/plants/{id}/dengesizlik/saatlik?fmt=json|csv|xlsx` (gun 14–365; CSV BOM + «;» + ondalık virgül + ilk
satır not; XLSX Saatlik + Aylar). EakIstek pozisyon_kaynagi / pozisyon_sabit_mwh (0–kurulu güç). `kgup_arsiv.listele` gop_esas (bir gün önce 12:30
İstanbul kapanışından önceki son öneri). Web: Doğruluk çipi + 2 sütun + katlanır döküm (son 48 saat, indir); Santralim «Piyasa pozisyonu»; Tahminler
«GÖP'e esas» rozeti; Portföy üye tablosunda «Santralde kalan EDT» ve «KÜPST».
İnceleme (4 sayfa, kullanıcı kareleri) + dil turu: döküm yön/durum kodları müşteri diline («enerji açığı/fazlası/dengede», «hesaplandı / sistem yönü
verisi eksik / KÜPST katsayısı yok»), «D-1 … koşu» → «bir gün önce 15:30'dan önceki son tahmin», ikinci kişi, ondalık virgül, 422 iletileri cümle; EDT
tanımı «gerçekleşen üretim ile piyasa pozisyonu (varsayılanı program)». Sahte fixture: üye KÜPST toplamı null (gerçek API `kupst_eksik`).
SINIR (karar 31.10): DSG (`dsg_ozet`) ve UEVÇB KÜPST (`kupst_ozet`) hesapları hâlâ `program_df` P50 önerisiyle; bildirilen KGÜP'e bağlanması P2b'de.
Testler: +2 (bildirilen program/pozisyon/döküm; gop_esas); tam takım 804 passed, 1 skipped (365 s). Sıradaki: v2.518 = P3a takvim, sonra P7a alarm, P5a YEKDEM.

# On sekizinci paket — v2.518 (01.11.2026 gece, canlı): Takvim — uzlaştırma, nakit ve mevzuat tarihleri (DUY m.132 zinciri, günlük piyasa saatleri, yıllık son tarihler) + santral tarih alanları

Commit `8e00f01`, CI #648 (7 dk 14 s). Dağıtım: api + web imajı (ssh; 22. port açıktı); göç yok (tarih alanları params_json'da). Canlı: index.html ve
24/24 JS/CSS birebir (25/25; yeni Takvim parçası dâhil; referans klasörü silinip derlendi); api kapsayıcısında `ext/turkiye/takvim` doğrulandı
(Ekim 2026 dönemi 16.11 / 24.11 / GTŞ 7.12; 13 günlük adım, `gunler` alanı); api ve web günlüğü hatasız.
Kaynak: GES sahibi ihtiyaç araştırması yol haritası P3a. Kapsam: `takvim.py` saf modül — resmî tatiller (2429 + Diyanet 2026–2027), iş günü;
`donem_takvimi` fatura dönemi başına DUY m.81(1) sayaç 10'u, m.132/A ön bildirim 11'i (EPİAŞ hafta sonu da yayımlıyor), m.132/B itiraz 12'si 17:30 ve
sonuç 14'ü 16:00 (kaydırma kuralı yok → «belirsiz», hafta sonu rozeti), nihai bildirim 15'i (hafta sonu/tatilde izleyen iş günü), m.132/C fatura 7 gün,
m.132/Ç ödeme 6. ve tahsilat 7. iş günü, m.133 yazılı itiraz 60 gün; lisanssızda LÜY m.23(3) GTŞ bildirimi 6'sı, m.25/m.26 GTŞ ödemesi izleyen ayın
5. iş günü. `gunluk_saatler` 13 adım (her gün: EAK 09:00, KGÜP 14:00–15:30, BYTM 14:30, teyit 17:00, GİP; iş günü: teminat 10:30/11:00/16:30/17:00,
avans 14:30/15:00/17:00, ESY devreye alma 11:00). `sabit_tarihler`: 30.11 YEKDEM, 10.12 ön / 31.12 nihai YEK listesi, 30.4 planlı devre dışı, LÜY
işletim bedeli Temmuz/Aralık son iş günü, 1.12.2026 DSG kararı, 10.12.2026 AYM, 18.12.2026 LÜY Geçici 14, 1.1.2027 (m.110, Geçici m.39, SKTT),
30.4.2027 cezai şart. Santral tarihleri (10 alan, PUT /kunye-tarihler, denetim santral_tarihler) ve türeyenler: lisans kalan süre, lisans bedeli
muafiyeti (ilk kabul + 8 yıl, m.43(4)), YEKDEM süresi (5905-27 / 7189 CK / kullanıcı yılı), poliçe kalan. Her olay kaynak_turu (mevzuat | hesaplanan |
duyuru | kunye = «santral tarihi») ve kaydirma (is_gunu | yok | belirsiz). Web: yeni sayfa «Takvim» (4 kart), `table.veri.takvim`.
İnceleme (01.11, kullanıcı kareleri × DUY/Lisans Yön. metinleri, pdftotext): tarih hesapları doğru; 9 metin/dayanak bulgusu düzeltildi — m.69(1)/(4)
atıfları; «her iş günü» yerine her gün / iş günü ayrımı («Günler» sütunu); araştırma numaraları görünür metinden çıktı (bekçi testi); «bitiş − 6 ay»
türetmesi kaldırıldı (m.26(2) erken sona erdirme süresidir, lisans m.26(1)(a) ile kendiliğinden biter); m.47 «teminat altına alma»; «İlk kabul
tarihi (kısmi ya da tam)»; fatura 7 gün ve itiraz 60 gün «belirsiz»; «santral tarihi» rozeti; dipnot yeniden yazıldı.
SINIR: dinî bayramlar 2026–2027 için tanımlı (2028 Diyanet yayımlayınca eklenir; dipnot söylüyor); alarm üretimi P7a, ilerleme raporu vb. P3b, EPYS
mutabakatı ve DSG/UEVÇB'de bildirilen KGÜP P2b.
Testler: test_takvim.py 12; tam takım 816 passed, 1 skipped (318 s). Sıradaki: v2.519 = P7a alarm (takvim olayları hazır), sonra P5a YEKDEM.

# On dokuzuncu paket — v2.519 (01.11.2026 gece, canlı): alarm — kural bazlı sıklık, santral alıcıları, webhook alarm.yeni, takvim/piyasa/hatırlatma kuralları; Santral ayarları kartı kurumsal dil ve sunum turu

Commit `c56fafb`, CI #650 (7 dk 27 s). Dağıtım: api + worker + web imajı (ssh; 22. port açıktı); göç yok (alıcılar ve eşikler params_json'da). Canlı:
index.html ve 24/24 JS/CSS birebir (25/25; referans klasörü silinip derlendi); api kapsayıcısında 12 seçimlik kural, yeni etiketler, 23 saatlik
kilit, webhook olayları (tahmin.yeni, alarm.yeni), dört yeni iş sözlükte ve izleme listesinde, dosya adı düzeltmesi; worker «basladi» satırı ve dört
giriş noktası (iletisim_kontrol, hatirlatma_teminat, ptf_kontrol, hatirlatma_avans); api/worker/web günlüğü hatasız.
Kaynak: GES sahibi ihtiyaç araştırması yol haritası P7a (K-08, ENV-F03, B13, IH-009/011/031/032, A7) + kullanıcının üç brief'i (Santral ayarları
kurumsal dil, ikinci tur, son kalite kontrolü).
Alarm: yeni seçimlik kurallar takvim_son_tarih (Takvim'deki her son tarih için N gün kala; olay başına tek alarm, aynı mesaj 60 gün içinde ikinci
kez yazılmaz), ptf_dusuk_saat (yarının gün öncesi PTF'si eşik altında; 0 → sıfır ve negatif, lisanslı YEKDEM'de tarifedeki YEK fiyatı; senaryo
fiyatı sayılmaz), ariza_sayaci_yaklasti (elle girilen aylık arıza ≥ eşik), teminat_hatirlatma (iş günü 10:15) ve avans_hatirlatma (iş günü 14:45;
yalnız lisanslı). kgup_teslim_gecikti «bildirildi» beyanına bakar (tahmin yoksa kritik, bildirilen dosya yoksa uyarı). Alıcılar: santral e-posta
listesi (≤10) ∪ PVQ_ALARM_TO; her alarmda webhook «alarm.yeni». Spam kilidi 24 → 23 saat (zamanlayıcı sapmasında günlük işin bir günü sessizce
atlaması — v0'dan beri gizli kusur). Worker: iletişim her saat :50, teminat 07:15 UTC, PTF 11:40 UTC, avans 11:45 UTC; gece taraması gün içi
kurallarını atlar. API: KuralIstek.alicilar; webhook olay listesi. Sahte fixture gerçek API şekline çekildi.
Santral ayarları (Santralim): altı bölüm iki cümlelik açıklama + bilgi düğmesi «Ayrıntı» (aria-expanded/aria-controls, Tab + Enter; gövde satırın
altında tam genişlik: ne işe yarar / ne zaman değiştirilir / neyi etkiler / ne zaman geçerli); etiketlerde birim, aralık, zorunlu/isteğe bağlı;
yanıltıcı «bir sonraki tahminden itibaren» çipi kalktı; alarm kuralları dört konu grubunda, her kuralın altında düz koşul cümlesi ve kontrol
saati («Son ölçüm 48 saatten eskiyse. Kontrol: her gece 07:00»), sabit iki kural işaretli-değiştirilemez (gerçek API secilebilir'e koymaz; panel
ayrıca çizer), dokuz eşik düzenlenebilir (oranlar panelde yüzde), bildirim alıcıları; program sınırları ve tarife formları hizalı; seçenek metinleri
kısa; «açık (fiziksel)». Sayfa ızgarası 1:1 → 1:1,45 (ÖLÇÜLDÜ: 1440 px'te ayarlar kartı 542 → 641 px; 70 öğe taşıyordu). Lisanssız dağıtım ifadesi
kural tablosuyla eşlendi (sapma tutarı santrale değil GTŞ/toplayıcı UEVÇB'sine; dağılım sözleşmesel). Dil ve alarm sözlüğü bekçileri.
kgup_service.uret: dosya adı santralın UEVÇB kodunu kullanır (API parametre geçmediğinden ad «KGUP_UEVCB_…» kalıyordu; yalnız ad).
İnceleme turları: P7a inceleme 10 bulgu (02 M32-inceleme), dil turu (M33), ikinci tur (M33-ikinci), son kontrol (M33-son).
Doğrulanamayan: lisanssız dağıtımda GTŞ/toplayıcı UEVÇB'sine KÜPST'nin EPİAŞ'ça fiilî uygulaması (kural tablosunda «belirsiz»; panel kesinlik
iddia etmez). Sonraya: SMS/push (B13), sıfır üretim olay alarmı ve arıza sayacının olay kaydından sayılması (P1), md.23(6) (P5a), aynı sunum
kalıbı Kuruluş/Ayarlar sayfalarına.
Testler: test_alarm_p7a 10 (+ senkron/isler bekçileri); tam takım 826 passed, 1 skipped (380 s). Sıradaki: v2.520 = P5a YEKDEM.

# Yirminci paket — v2.520 (01.11.2026 gece, canlı): YEKDEM katmanı — fiyat rejimi (Cetvel I / 7189), TCMB günlük kur arşivi, 7189 aylık ilan ve USD sınır kontrolü, YEK Yön. m.23(6) saat işareti

Commit `cea37fa`, CI #652 (4 dk 45 s). Dağıtım: api + worker + web imajı (ssh; 22. port açıktı) + **`alembic upgrade head` → v2520_yekdem DB sahibiyle**
(`.env`'deki `PVQ_SMTP_FROM=PVQuant <…>` satırı `set -a; . ./.env` ile kabuk hatası verdi → parola `grep "^DB_PASSWORD=" .env | cut -d= -f2-` ile okundu; DERS).
Canlı: index.html ve 24/24 JS/CSS birebir (25/25); alembic_version v2520_yekdem, yekdem_fiyat 6 tohum satırı; worker «basladi», api «startup complete»;
kur arşivi ilk doldurması sunucuda worker kapsayıcısından tetiklendi (`kur_service.gunluk()`; sonuç 02 M34 raporunda).
Kaynak: GES sahibi ihtiyaç araştırması yol haritası P5a (IH-012, IH-041, K-12); bulgular 02-12 (EPİAŞ 01.10.2026 duyurusu: Ağustos 278,92 / Eylül 284,81 /
Ekim 289,74 kr/kWh; yerli 75,80 / 77,40 / 78,74; depolamalı 328,98 / 335,93 / 341,74), 02-21 (kur: enerjinin sisteme verildiği günün TCMB döviz alış kuru,
5346 m.3(1)(16), YEK Yön. m.3(1)(dd)), 02-22 (7189 Ek-2 aylık güncelleme; alt–üst sınır bir önceki ayın ortalama USD alış kuruyla 4,95–6,05 ¢), 01-14 (m.23(6)).
Göç: kiracısız `doviz_kuru` (gün PK; USD/EUR alış, bülten) ve `yekdem_fiyat` (ay + tesis tipi PK; kr/kWh, yerli katkı, kaynak) + tohum.
kur_service: TCMB today.xml / günlük arşiv (ForexBuying); bülteni olmayan gün (hafta sonu, resmî tatil, arefe yarım günü — `bulten_gunu`) önceki iş
gününün kurunu taşır ve işaretler; aylık ortalama beklenen/eksik bülten günleriyle; geri doldurma ≤400 gün; worker `gece_kur` 13:05 UTC, ilk koşuda 13 ay.
yekdem_service: rejim işletmeye giriş tarihinden (≤30.6.2021 Cetvel I; 1.7.2021–31.12.2030 7189; sonrası belirsiz) ya da seçimle; gün bazlı YEK fiyatı
(Cetvel I ¢ × 10 × günün kuru + yerli ¢ 5 yıl; 7189 ilan × 10 + yerli katkı süresi içinde; ilan yoksa önceki ay işaretli; elle kur yalnız yedek); USD sınır
kontrolü (kr ÷ kur = ¢; tabanda / içinde / tavanda ±0,02); m.23(6) işareti (PTF ya da SMF < V ve sistem fazlası saatinde program üstü üretim, PTF < YEK
fiyatı → YEKDEM dışı MWh, fark = MWh × (YEK − 0,98 × PTF); 19.10.2026'dan; «belirsiz»; talimat saatleri dâhil değil); ilan kaydı kaynak + duyuru tarihi
ister (gelecekte ya da dönemden önce → 422); kayıt durumu resmî duyuru / elle / doğrulanmadı; bekleyen dönem listesi.
Bağlantılar: tarife_service yekdem alanları (rejim, tesis_tipi, yerli_katki, yerli_katki_usd_cent; ¢ ve kur isteğe bağlı), yapi/gelir_df/ortalama santralı
alır (YekdemSeri); dengesizlik _girdiler/saatlik_pv/yekdem_eki → lisanslı YEKDEM dökümü 25 sütun; alarm ptf_dusuk_saat eşiği yarının YEK fiyatı; API
GET /v1/plants/{id}/yekdem, GET /v1/yonetim/yekdem, PUT /v1/yonetim/yekdem-fiyat, POST /v1/yonetim/kur-doldur (denetim eylemleri yekdem_fiyat, kur_doldur).
Web: Santralim tarife formu rejime göre (bilgi satırı: rejim + bugünkü fiyat); Doğruluk «YEKDEM» kartı (yalnız lisanslı YEKDEM) + dökümde dört ek sütun;
Yönetim › Sistem «YEKDEM fiyatları ve döviz kuru» (ilan tablosu: geçerli dönem, kuruş/kWh, USD karşılığı, USD sınır kontrolü, kaynak, kayıt durumu, kayıt
zamanı; resmî kaynak bağlantıları; ilan girişi; kur arşivi doldurma). Ayar satırı seçicileri 375 px'te kartı taşırıyordu (314/293) → sınırlandı.
İnceleme turları (01.11): kullanıcı kareleri 9 bulgu (02 M34-inceleme); yönetim kartı brief'i (M34-ikinci inceleme: karedeki Kasım satırı sahte API'ye
yazılan deneme girişiydi; kur eksikleri arşiv kapsamındandı → ilk doldurma, kaynak doğrulaması, kayıt durumu, bağlantılar); üçüncü inceleme (dönemden
önceki duyuru tarihi reddi, kur ayı tamlığı, bekleyen dönem); son kontrol («Band» sözcüğü). DERS: sahte API'ye deneme kaydı yazma, kullanıcı kareyi gerçek sanır.
Doğrulanamayan: tatil günü kur kuralı (önceki iş günü kuru taşındı ve işaretlendi), m.23(6) uygulaması (saatlik mi, hangi KGÜP sürümü, ilk fatura dönemi;
YAT saatleri veri yok), Kasım 2026 ilanı (bekleyen; yönetimden girilir), depolamalı yerli katkı, EPİAŞ sitesine makineden erişim.
Sonraya (P5b): YEKBED yeniden hesabı ve nihai bildirim kalemleriyle kıyas (P2b), yıllık YEKDEM içi / serbest kıyası (30 Kasım), talimat verisi, Cetvel II
yerli katkı kalemleri, EPİAŞ ilanının otomatik çekimi (uç yok).
Testler: test_yekdem 14; tam takım 839 passed, 1 failed (test_modb_rapor 17 dakikalık yüklü koşuda zaman aşımı; tek başına 9/9 geçti), 1 skipped; web tsc 0 /
103 / oxlint 0 / build. Sıradaki: v2.521 = P1 olay kaydı ya da P2b (yol haritası dalga 2).

