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


# Yirmi birinci paket — v2.521 (02.11.2026 gece, canlı): olay kaydı — planlı bakım, arıza, talimat (YAL/YAT), acil durum kesmesi, şebeke kesintisi, hasar; EAK dosyasında saatlik düşüm ve gerekçe sütunu, aylık arıza sayacı, kullanılabilirlik istisnası, dâhilî bilgi geri sayımı

Commit `45e3090`, CI #654 (7 dk 24 s). Dağıtım: api + worker + web imajı (ssh; 22. port açıktı) + **`alembic upgrade head` → v2521_olay DB sahibiyle**
(parola `grep "^DB_PASSWORD=" .env | cut -d= -f2-`; `.env` source edilmedi). Canlı: index.html ve 25 JS birebir (26/26); alembic_version v2521_olay; olay
tablosu boş; pvq_app SELECT/INSERT/UPDATE (DELETE yok); api «startup complete»; worker «basladi»; olaylar uçları kimlik olmadan 422 (yol canlıda var).
Kaynak: GES sahibi ihtiyaç araştırması yol haritası dalga 2 P1a (IH-086, IH-017, IH-009, IH-003, IH-085, IH-103, IH-076); bulgular 01-18 (TPYS EAK gerekçe
sütunları: kaynak yetersizliği, iklim/verim, mücbir, dışsal, güvenlik; başka neden yoksa «kaynak yetersizliği»; arıza/bakım TPYS «Arıza ve Bakım
bildirimleri» sayfasından ayrıca; Karar 14029/14907: UEVÇB'de ayda 30 ve üzeri arıza kaydı KÜPST n 0,05 → 0,08), 01-19 (Karar 14967: tesis 30 MW / portföy
50 MW, olaydan en geç 1 saat içinde Dâhilî Bilgi Platformu; yürürlük metinde yok → «belirsiz»), 03-10 (ESY m.52–54 bakım bildirimi), DUY m.69/A (EAK'yi
arıza/bakım kaydıyla düşürmeyi itiyat etmek Kanun m.16'ya gider → kayıt gerekçeli, tür ve başlangıç değiştirilemez, silme yok).
Göç: `olay` (kiracı RLS; tür, başlangıç/bitiş, devre dışı kW, neden, EAK gerekçe sütunu, belge no, durum açık/kapalı/iptal, oluşturan; DELETE yetkisi yok).
olay_service: tür → kural tablosu (EAK'yi düşürür mü, varsayılan gerekçe sütunu, kullanılabilirlik istisnası, arıza sayacı); doğrulama (başlangıç ≤400 gün
ileri, bitiş > başlangıç, devre dışı güç 0–AC sınırı, gerekçe türe uygun); ekle (çakışan kayıt uyarısı; engel değil) / güncelle (bitiş, kW, gerekçe, iptal;
tür ve başlangıç değişmez) / listele / aralık; görünen evre planlı / sürüyor / bitti / geçersiz (DB durumu ayrı); saatlik etki (Türkiye günü 24 saat, saat
içinde kısmen süren olay süreyle orantılı, «tesisin tamamı» = günün EAK tabanı — AC sınırı / EAK alanı / kurulu güç, kWp değil; birden çok olay toplanır,
taban sınırlar; bitişi girilmemiş olay gün sonuna kadar); istisna saatleri (planlı bakım, talimat, acil kesme, kesinti); aylık arıza sayısı olay ∨ elle
giriş (kaynak etiketi); dâhilî bilgi 1 saat geri sayımı; özet; hasar dosyası CSV (; ayraç, BOM, evre sütunu).
Bağlantılar: kgup.eak_csv_metni gerekçe payları (olayın sütunu önce, kalan kaynak yetersizliği); kgup_service.uret saatlik EAK serisi (program tavanı,
eak.kaynak «+olay»); kullanılabilirlik istisna saatleri «kısıntı» gibi dışarıda; dengesizlik/portföy/alarm arıza sayısı olay kaydından; denetim eylemleri
olay_ekle / olay_guncelle; API GET/POST /v1/plants/{id}/olaylar, PUT /olaylar/{olay_id}, GET /olaylar.csv.
Web: «Olay kaydı» sayfası (KPI: süren olay + planlı, aylık arıza kaydı n/30, bugün kapasite düşümü saat + taban, dâhilî bilgi açıklaması; yeni olay formu;
tür etkileri tablosu; olay listesi Bitir / Geçersiz say; CSV; «Bu sayfa nasıl çalışır»); Santralim arıza alanı notu; sahte API fixture; kare.mjs.
İnceleme turları (01–02.11): kareler (evre: ileri tarihli bakım «açık» değil «planlı»); brief 1 (kısmi saat orantılı, AC tabanı, çakışma uyarısı, CSV evre,
dil); brief 2 — bağımsız hesap testleri (gece yarısı kesimi, 20/60, ileri tarihli bakım, taban, toplam, geçersiz) geçti; hatalar: hasar «mücbir sebep»i
otomatik seçiyordu (fiziksel tür ≠ mevzuat gerekçesi → varsayılan kaynak yetersizliği, seçim kullanıcıda), çakışma uyarısı «iki kez düşürmez» diyordu
(gerçekte toplanır, ekipman kimliği yok → dürüst metin), dosyada «iptal» / ekranda «geçersiz», giriş sınırı kWp (→ AC), «Bitir» saat dilimsiz (→ UTC).
Doğrulanamayan: mücbir sebep resmî koşulları ve TPYS'nin gerekçe sütunlarını değerlendirmesi; ekipman bazlı çakışma (model ekipman tutmuyor); Karar 14967
yürürlüğü ve platform arayüzü; lisanslı GES'te EAK = KGÜP izni; dağıtıma bağlı bakım bildirim süresi; EAK.csv arıza sütunu.
Sonraya: P7b olay alarmları, P2b talimat → BUDÜP, P3b Takvim satırı, P1b ekipman bazlı olay (varlık ağacı), P8 kayıp enerji ve TL, kanıt eki (dosya).
Testler: test_olay 6; tam takım 846 passed, 1 skipped (328 s); web tsc 0 / 103 / oxlint 0 / build; 1440/768/375 taşma 0. Sıradaki: v2.522 = dalga 2 devamı
(P2b DSG/UEVÇB bağlanması ya da P7b olay alarmları).

# Yirmi ikinci paket — v2.522 (02.11.2026 gece, canlı): mutabakat — EPİAŞ uzlaştırma bildirimi içe alma ve kalem kalem kıyas; teminat göstergesi mevzuat formülüyle; DSG/UEVÇB hesaplarında bildirilen KGÜP; DSG üye dağılımı belgesi

Commit `780041b`, CI #656 (7 dk 30 s). Dağıtım: api + worker + web imajı (ssh; 22. port açıktı) + **`alembic upgrade head` → v2522_mutabakat DB sahibiyle**
(parola `grep "^DB_PASSWORD=" .env | cut -d= -f2-`). Canlı: index.html ve 26 JS birebir (27/27); alembic_version v2522_mutabakat; `uzlastirma_bildirimi` boş,
pvq_app yalnız SELECT/INSERT, üç inceleme kolonu (dosya_donem, dosya_surum, surum_kaynagi) var; api «startup complete»; worker «basladi»; mutabakat ve
dsg.csv uçları kimlik olmadan 422 (yol canlıda var).
Kaynak: yol haritası dalga 2 P2b (c)(d)(e) + v2.517'de P2b'ye bırakılan sınır (IH-027, IH-028, IH-033, IH-036; ENV-F01, K-05); bulgular 02-23/02-24
(EPYS «Uzlaştırma Bildirimi» ekranı: aylık alacak/borç özeti, kalem kodları DAM/IDM/RES/IMBALANCE/BPM/RETROSPECTIVE/SIDE_PAYMENT/ZERO_BALANCE/MOF/KUPST/…;
dosya başlıkları BULUNAMADI), 02-01/02-02 (takvim: ön bildirim izleyen ayın 11'i, nihai 15'i → iş günü; itiraz 12'si 17:30, faturaya 60 gün), 02-08
(dengesizlik teminatı: 3 ayın en yüksek aylık negatif EDM × 12 ay ortalama SMF × risk katsayısı; katsayı BULUNAMADI), 02-27 (DSG iç fatura BULUNAMADI).
Göç: `uzlastirma_bildirimi` (kiracı RLS; dönem, sürüm ön/nihai, yükleme kimliği, kalem kodu + dosyadaki ad, yön, tutar, dosya adı, SHA-256, dosyadan
okunan dönem/sürüm, sürüm kaynağı dosya/kullanıcı/varsayılan, yükleyen; güncelleme ve silme yok — her yükleme yeni sürüm).
mutabakat_service: dosya okuma CSV (ayraç/ondalık tanıma) ve XLSX (openpyxl) — başlık satırı («Uzlaştırma Kalemleri» + «Tutar (TL)» ya da ayrı
alacak/borç sütunları), bölüm başlıkları, tip sütunu ya da işaret; dönem satır düzeyinde (etiket/değer ayrı hücre, gün.ay.yıl tam tarihler elenir) ve
sürüm («Nihai Bildirim» / «Ön Uzlaştırma Bildirim») dosyadan; kalemler EPYS kodlarına ipuçlarıyla, tanınmayan «diğer» adıyla; dosyadaki durum kullanıcı
seçiminden üstün (uyarı), dosyadaki dönem seçilenle çelişirse 422. Sürüm doğrulaması: takvim.donem_takvimi ile (Ekim 2026: ön 11.11, nihai 16.11; itiraz
12.11 17:30 / 15.01.2027) — yükleme takvim tarihinden önceyse «takvimden önce»; EPİAŞ durumu dosyadan doğrulanamadığından resmî durum her zaman
«doğrulanmadı». PVQuant kalemleri: dönem için dengesizlik_service.dokum (Doğruluk ile aynı hesap) → EDT alacak/borç, KÜPST, lisanslı YEKDEM'de YEK
alacağı (kaba); güvenilirlik {gerçek, kısmi, senaryo, doğrulanamadı} + nedenler (dönemin kaç saati var, son üretim verisi, kaç saatte öneri program,
hesaplanamayan saat; senaryo saatleri DÖNEM bazında — dokum özetine saat_fiyat_kaynak). Mutabakat: kalem satırları (EPİAŞ alacak/borç, PVQuant
alacak/borç, fark net ve bileşen bazlı, durum uyumlu / fark / senaryo hesabı / yalnız bildirim / bildirimde yok / hesaplanamadı); uyum ölçütü PVQuant
işletme ölçütü (bileşen başına %2 ya da 50 TL'nin büyüğü; mevzuat toleransı değil); özet aynı kapsamla (EPİAŞ toplamı ≠ karşılaştırılan kalemler:
bildirim_kiyas_*, pvquant_*, fark); «Ne yapmalı» (EPYS saatlik detay, itiraz süreleri); yükleme tarihçesi (dönem + sürüm başına en yeni geçerli).
dengesizlik_service: teminat_gostergesi (mevzuat formülü; katsayı params_json.teminat_risk_katsayisi, yoksa tutar yok; doğrulanmamış; eski
sadeleştirilmiş gösterge kaldırıldı); program_bildirilenle + _pozisyon_serisi → dsg_ozet ve portfoy_kupst_ozet bildirilen KGÜP ve pozisyon ayarıyla
(v2.517 sınırı kapandı; dipnot programın kaynağını söyler); dsg_uye_csv. API: GET/POST /v1/plants/{id}/mutabakat, GET /v1/portfoy/dsg.csv,
EakIstek.teminat_risk_katsayisi; denetim eylemleri mutabakat_yukle, dsg_belge_indir.
Web: «Mutabakat» sayfası (dönem/sürüm seçici; KPI EPİAŞ toplam alacak / EPİAŞ toplam borç / PVQuant yeniden hesaplanan tutar + aynı kalemlerde EPİAŞ /
Hesaplama farkı; «EPİAŞ bildirimi yükleme» + tarihçe (takvim rozeti); «Hesaplamada kullanılan veriler» (güvenilirlik rozeti, saat/beklenen, son üretim
verisi, program, fiyat, üretim kaynağı, sürüm uyarısı, «Ne yapmalı»); «Uzlaştırma kalemlerinin karşılaştırılması»); Santralim «Teminat risk katsayısı»;
Doğruluk teminat cümlesi bileşenlerle; Portföy «Üye dağılımı (CSV)»; sahte API fixture durumu gerçek kuralla hesaplar.
İnceleme turları (02.11): kullanıcı karesi (dönem tanıma ayrı hücre / tam tarih karışması, kuruşlu tutarlar, dönem düğmesi); brief (kapsam ayrımı,
bileşen bazlı eşik, senaryo/kısmi/gerçek etiketi, sürüm takvimi, tarihçe) — 02 M36, M36-inceleme, M36-ikinci inceleme.
Doğrulanamayan: EPYS dosyasının gerçek kolon başlıkları (örnek dosya yok; ipuçlu tanıma gerçek dosyayla sınanmalı), EPİAŞ «Uzlaştırma Durumu»nun
resmî doğrulaması, UEVM sayaç verisi (P4), düzeltilmiş bildirim sürümleri, risk katsayısı ve Teminat U&E güncel metni, DSG iç fatura biçimi, tesis
kimliği dosyadan. Sonraya (P2b-2): saatlik detay dosyaları (KÜPST Detay, Dengesizlik Uzlaştırma XLSX) içe alma ve saat bazında kıyas; YEKBED (P5b).
Testler: test_mutabakat 9; tam takım 855 passed, 1 skipped (356 s); web tsc 0 / 103 / oxlint 0 / build; 1440/768/375 taşma 0. Sıradaki: v2.523 = dalga 2
devamı (P4a sayaç izleme ya da P3b uyum takvimi).

# Yirmi üçüncü paket — v2.523 (02.11.2026 gece, canlı): Sayaç — OSOS/MASS/EPYS sayaç verisi SCADA'dan ayrı içe alma, veri geliş beklentisi ve 12. gün geri sayımı, SCADA ile sayaç farkı, kaynak/nitelik etiketi; lisanssızda SCADA bağlantı durumu ve Karar 14909 bedel göstergesi

Commit `a2b8ef3`, CI #658 (5 dk 41 s). Dağıtım: api + worker + web imajı (ssh; 22. port açıktı) + **`alembic upgrade head` → v2523_sayac DB sahibiyle**
(parola `grep "^DB_PASSWORD=" .env | cut -d= -f2-`). Canlı: index.html ve 27 JS birebir (28/28); alembic_version v2523_sayac; `sayac_saatlik` ve `sayac_yukleme` boş, pvq_app
SELECT/INSERT(/UPDATE); `olay.tur` CHECK'inde uzaktan_acma; api «startup complete»; worker «basladi»; sayac / sayac.csv / sayac-ayar uçları kimlik olmadan 422.
Kaynak: yol haritası dalga 2 P4 (a) kademesi (IH-019, IH-020, IH-022, IH-057; 01-15/03-20 Ölçüm Sist. Yön. m.8(2)–(3); 02-09 DUY m.81(1), m.82(4); 01-16
LÜY m.21(7), DUY m.75(4), Karar 14909; 06-44 MASS, 06-46 BEDAŞ OSOS portal metinleri; Açık Konular 14.md s.279 Karar 14909 / LÜY Geçici m.14 askısı).
Göç: `sayac_saatlik` (saat UTC + kaynak osos/mass/epys/elle; veriş ve çekiş kWh; nitelik ölçülmüş/tahmini/doldurulmuş/elle/yok; dilim sayısı; yükleme
kimliği; PK saat+kaynak; yeniden yükleme = düzeltme, silme yok) ve `sayac_yukleme` tarihçesi (dosya, SHA-256, aralık, saat/satır, nitelik sayımı,
uyarılar); kiracı RLS; `olay.tur` CHECK'ine «uzaktan_acma». SCADA tablosu dokunulmadı; sayaç serisi tahmin ve uzlaştırma hesabına GİRMEZ.
sayac_service: dosya tanıma CSV/XLSX (başlık ipuçları: zaman/tarih/saat/profil tarihi; veriş/üretim/kWh/MWh; çekiş; durum → EDAŞ kodları Estimated /
FilledByDiff / ManuelData / NoData / BackupMeterData niteliğe; ayrı tarih+saat, «08:00-09:00», «24:00», Excel tarih hücresi; 10/15/30 dk dilimler saate,
saatin niteliği en zayıf dilim; endeks sütunu değer sayılmaz; yinelenen dilimde son satır; gelecek tarihli ve negatif satırlar alınmaz; belirsiz veriş
sütunu uyarısı; başlıksız yedek yalnız satırların ≥ %90'ı zaman;kWh ise), kayıt + tarihçe, aynı saatte kaynak önceliği epys > osos > mass > elle,
SCADA okuma (kaynak etiketi scada_dosya / epias_seffaflik), fark (günlük Türkiye günü; yalnız ortak saatler; «yalnız ölçülmüş» ↔ «tahmini dâhil» ayrı;
kapsam ortak/pencere, yalnız SCADA, yalnız sayaç, ikisi de yok; en büyük fark günü; kaynak sayımı), geliş (15 dk sayaç: saat + 2 sa m.8(2) «belirsiz»,
dilim sonundan koruyucu; diğer: m.8(3) takvim; sınıflandırma geçen / vadesi gelen / vadesi gelmemiş / yüklü (ölçülmüş, tahmini) / eksik; dönem 10. gün
ve 12. gün 17:30 geri sayımı takvim.donem_takvimi'nden + dönem kapsamı), SCADA durumu (LÜY m.21(7) 50 kW; anlaşma tarafı dağıtım/iletim; durum beyan;
kopukluk gün sayacı; uzaktan açma olayları olay kaydından; Karar 14909 m.16(1): (f) yalnız m.75(4) 900 kW+ ve askıda, (g) ihlal başına bir kat en çok üç
askıda, (ç) bu ayın 30 günü aşan günleri (g) günleri hariç «belirsiz» ve askı doğrulanmadı; tutar varsayımsal, bedel girilmezse yok; iletime bağlıda
gösterge yok; lisanslıda kart yerine not), ayar doğrulama (kopukluk başlangıcı gelecekte olamaz), günlük CSV.
mutabakat_service: `_sayac_kapsami` — dönemin yüklü/ölçülmüş/tahmini sayaç saati ve ölçülmüş saatlerde SCADA farkı güvenilirlik nedenlerine ve «Üretim»
satırına; hesap SCADA ile. olay_service: tür «Uzaktan açma yapılamadı» (EAK düşmez, istisna değil, sayaca girmez).
API: GET/POST `/v1/plants/{id}/sayac` (kaynak; dosya ≤8 MB), GET `sayac.csv`, PUT `sayac-ayar` (sayac_turu, scada_durum, scada_kopukluk_baslangic,
uzaktan_acma_var, sistem_kullanim_bedeli_tl_ay); denetim eylemleri sayac_yukle, sayac_ayar.
Web: «Sayaç» sayfası (KPI son sayaç verisi / eksik saat sınıflandırmalı / SCADA–sayaç farkı ölçülmüş + tahmini dâhil + kapsam / düzeltme son anı + dönem
kapsamı; yükleme + tarihçe; geliş beklentisi + sayaç türü + dönem satırları; günlük tablo «Ölçülmüş fark» sütunu + CSV; lisanssızda SCADA kartı: beyan rozeti,
m.75(4) kapsamı, bedel tablosu «varsayımsal», askı ayrımı, uygulanmayan maddeler); Mutabakat «Üretim» satırı sayaç kapsamı; sahte API SAYAC segment'e bağlı
(a1 lisanslı → not, a4 lisanssız → kart), gelis gerçek saate bağlı, saat bazlı ölçülmüş; dil: «ceza» yerine «bedel maddesi».
Üç inceleme turu (02 M37 + inceleme/ikinci/üçüncü): sahte toplam tutarsızlıkları, pencere 720 sa, 441 ↔ 408 (gün bazlı dışlama → saat bazlı), Karar 14909
kapsam/askı ayrımı, tesis sınıfı, içe alma sıkılaştırma, beyan/varsayımsal etiketleri.
Testler: tests/test_sayac.py 9 (OSOS 15 dk + nitelik; MASS ayrı saat + XLSX MWh + endeks reddi + başlıksız + yinelenen/gelecek/negatif + belirsiz sütun;
zaman/nitelik; fark_df saf + ölçülmüş = ortak − tahmini; kayıt-yeniden yükleme-öncelik-fark-geliş-sınıflandırma-ay sınırı-dönem kapsamı (test DB); SCADA
durumu + (f)/(g)/(ç) kuralları + iletim + askı ayrımı; ayar doğrulama; olay türü + özet + lisanslı/segment notu; API 201/422/404 + CSV); test_olay tür 8;
test_mutabakat 9; tam takım 864 passed / 1 skipped; web tsc 0, 103, oxlint 0; 1440/768/375 (a1) + 1440/375 (a4) taşma 0 (`kanit/sayac-*-2026-11-02.jpg`).
Doğrulanamayan / sonraya: OSOS/MASS/EPYS resmî sütun başlıkları (portal JS metinlerinden türetildi; gerçek dosyayla sınanmalı); «2 saat»in sayım başlangıcı
(01-15 BULUNAMADI); askı tarihi 30.4.2027 ikincil kaynak, (ç) askı kapsamı; (ç) günlük %1 sayım yöntemi; GTŞ/toplayıcı portföy üyeliği beyan edilmiyor;
EPİAŞ'a fiilî geliş ve geç geliş ölçülemez; sayaç verisi uzlaştırma girdisi değil (P4a-2); eksik saat alarmı P7b; inverter/protokol alımı P4b. Tahmin
motoru, kalibrasyon ve uzlaştırma formülleri değişmedi.

# Yirmi dördüncü paket — v2.524 (02.11.2026 gece, canlı): Takvim — lisans, bildirim ve uyum takvimi; sorumlu taraf ve işlem sınıfı; YEKDEM uygunluğu; olay kaydından bakım bildirim son anı; «Aykırılıkta»

Commit `3ddc19e`, CI #660 (5 dk 53 s). Dağıtım: api + worker + web imajı (ssh; 22. port açıktı); **göç yok** (künye alanları params_json). Canlı: index.html ve 27 JS birebir (28/28);
api «startup complete»; worker «basladi»; takvim ucu `uyum`, `bakim`, `yaklasan_piyasa`, `islem_etiketleri` alanlarını döner (kimlik olmadan 422).
Kaynak: yol haritası P3 (P3a'da bırakılan uyum satırları): IH-068 EPDK periyodik bildirimler (03-01), IH-069 ilerleme raporu (03-02 Lisans Yön. m.30(2)(ç)),
IH-070 lisans bedeli taksitleri (03-03 m.43(4), (5)(a), (7)(a), (8)), IH-074 olay anı sayaçları (03-08 m.57(2), 03-09 m.30(2)), IH-075 planlı devre dışı
(03-10 Şebeke Yön. m.52, m.54), IH-078 poliçe (m.47), IH-079 İSG periyodik kontrol (03-21 İş Ekipmanları Yön. Ek-III), IH-077 «kaçırılınca» (03-14 6446
m.16; bent eşlemesi çıkarım, tutar yok), 03-18 lisanssız 10 yıl (LÜY m.26(4), m.33(7)), YEKDEM uygunluğu (03-12 Karar 5905-27 / 7189; YEK Yön. m.5–7).
ext/turkiye/takvim: `_olay(..., sonuc, sonuc_kisa, islem, sorumlu)` — işlem sınıfı (islem / takip / mevzuat / dogrulama) ve sorumlu taraf her olayda;
`uyum_olaylari(pj, bugun, segment, capacity_kwp)`: ilerleme raporu (Ocak/Temmuz sonu; tam kabule kadar; hafta sonu «belirsiz»), lisans bedeli taksitleri
(Şubat/Haziran/Ekim 5. iş günü — `_n_inci_is_gunu`; ilk kabul + 8 yıl muafiyeti bitince; kabul yoksa doğrulama), BDB-02 (15 Mayıs; kurulu güç ≥ 100 MW,
mekanik güç kWp ile yaklaşıldı → doğrulama), TEİAŞ bakım planı adımları (30 Nisan talep, 31 Temmuz itiraz, 31 Ağustos alternatif, 31 Ekim TEİAŞ yayımı;
lisanslıda bağlantı türü kayıtlı değil → doğrulama, iletime bağlı lisanssızda işlem), İSG periyodik kontrol (+1 yıl), ortaklık değişikliği bildirimi
(+6 ay), izin/ruhsat iptali bildirimi (+2 ay), lisanssız 10 yıllık alım süresi; `bakim_bildirim(bas, bit)` Şebeke Yön. m.54 (< 8 sa → 24 sa, 8–48 sa → 7 gün,
> 48 sa → yıllık plan); `yekdem_uygunluk` (YEKA'da yok; destek süresi hedef yıldan önce bitmişse satır düşer; tarih yoksa doğrulama; lisanslı serbestte
«isteğe bağlı» notu); `yaklasan(..., capacity_kwp)` uyum olaylarını ve süzgeci taşır; dönem adımlarına kısa sonuçlar («Düzeltme o aya girmez», «Temerrüt +
teminat mahsubu», «EPİAŞ ödemesi gecikir», «İtiraz hakkı düşer» — 60 gün itirazı isteğe bağlı hak: takip); sabit tarihler sınıflı (m.110 mevzuat değişikliği,
Geçici m.39 doğrulama — DSG türü kayıtlı değil, Karar 15005 öz tüketim, Karar 14909 askısı mevzuat). Künye +4 alan: tam_kabul_tarihi, isg_son_kontrol,
ortaklik_degisikligi, izin_iptali (`kunye_turet` → ilerleme_raporu_yukumlu, isg_sonraki_kontrol).
takvim_service: `ozet(plant, gun, bugun, tenant_id)` → `uyum` (12 ay; UYUM_KODLAR), `bakim` (olay kaydındaki planlı bakımlar → bildirim son anı),
`yaklasan_piyasa` (uyum tarihleri hariç; sayfa bunu gösterir, alarm tam `yaklasan`ı kullanmaya devam eder), `islem_etiketleri`, `uyum_not`, `bakim_kaynak`.
API: KunyeTarihIstek +4 alan; GET takvim kiracı ve kurulu güçle.
Web: Takvim — «Uyum takvimi» kartı (Tarih / Ne + işlem rozeti + not ipucu / Kim / Dayanak / «Aykırılıkta» kısa biçim / Kalan; planlı bakım tablosu;
sınıflar ve kapsam dışı olanlar açılır alanda), Yaklaşan'da işlem rozeti + «Kim» sütunu + uyum tarihleri hariç, aylık tabloda adım yanında sorumlu, Santral
tarihleri formu +4 alan, künye listesinde «İlerleme raporu» ve «İSG periyodik kontrol»; `.rozet-dikkat` (amber «işlem gerekli»), «doğrulama gerekli»
rozet-uyari; sahte takvim fixture'ı gerçek motordan üretilir, sahte API bugünü ve kalan günleri gerçek saatten hesaplar.
İki inceleme turu (02 M38 + inceleme + ikinci inceleme): taksit kaydırma rozeti, hafta sonu belirsiz, TEİAŞ adımları, «Aykırılıkta» boşlukları, sahte saat;
sorumlu/işlem sınıfı, YEKDEM uygunluğu, 1 Ocak 2027 sınıfları, tekrar ve okunabilirlik; son kontrol: 60 gün itirazı takip.
Testler: tests/test_takvim.py 15 (yıllık uyum tarihleri; 5. iş günü 2026: 6 Şub / 5 Haz / 7 Eki, 2027: 5 Şub / 7 Haz / 7 Eki; tam kabul → ilerleme raporu
kalkar; 8 yıl muafiyeti; BDB-02 eşiği; hafta sonu belirsiz; TEİAŞ adımları; künye türevleri +1 yıl / +6 ay / +2 ay; bakım bildirimi üç kural + süre yok;
sınıf/sorumlu; YEKDEM uygunluğu 6 durum; planlı devre dışı sınıfı; `yaklasan_piyasa`; görünür metin bekçisi uyum olaylarını ve sonuçları da tarar;
kunye_dogrula; servis ozet); alarm P7a 10; tam takım 867 passed / 1 skipped; web tsc 0, 103, oxlint 0, build; 1440/768/375 taşma 0 (`kanit/takvim-uyum-{1440,768,375}-2026-11-02.jpg`).
Doğrulanamayan / sonraya: EPDK ilerleme raporu ve BDB-02 son günü hafta sonuna gelince uygulama; dağıtıma bağlı lisanslı tesiste Şebeke Yön. m.52;
mekanik güç ≈ kWp; m.16 bent eşlemeleri çıkarım, 2027 tutarları yok; m.43(4) yıl sayımı; DUY m.110 1.1.2027 uygulama ayrıntıları; serbest piyasadaki tesisin
destek süresi içinde YEKDEM'e yeniden giriş hakkı (YEK Yön. m.5 metninden; uygulama teyidi yok); DSG türü ve bağlantı türü alanları (P3c adayı); toplayıcı
lisansı takvimi, piyasadan alım sınırı (Karar 14626), YEK-G yıllık kaydı, siber güvenlik öz denetimi kapsam dışı; uyum tarihleri için alarm sınıfa göre (P7b).
Tahmin motoru, kalibrasyon ve uzlaştırma formülleri değişmedi.

# Yirmi beşinci paket — v2.525 (02.11.2026 gece, canlı): Raporlama — dönem raporu (ay / çeyrek / yıl; geçmiş dönem yeniden üretilebilir), zamanlanmış aylık e-posta gönderimi, panel derin bağlantıları (#sayfa/santral)

Commit `461a7b4`, CI #662 (5 dk 38 s). Dağıtım: api + worker + web imajı (ssh; 22. port açıktı); **göç yok** (ayar params_json.rapor_gonderim). Canlı: index.html ve JS/CSS birebir (25/25);
api «startup complete»; worker «basladi»; `rapor-donem` ve `rapor-gonderim` uçları kimlik olmadan 422/401 döner.
Kaynak: yol haritası dalga 2 «raporlama / dönem seçici» — IH-096 aylık O&M raporu (geçmiş herhangi bir aralık için yeniden üretim; çeyrek/yıl özeti), IH-105
finansör çıktısı ve zamanlanmış gönderim, IH-107 yıllık özet; envanter B14 (zamanlanmış rapor yoktu), B17 (dönem seçici yoktu), B16 (derin bağlantı yoktu),
ENV-F05-5 (rapor ucu açıklaması üç şablon sayıyordu). Türk O&M aylık rapor şablonu ve finansörün beklediği biçim BULUNAMADI (04-24, 05-40); içerik SPE Tablo 10
asgarisine yakın tutuldu.
aylik_rapor_service: `donem_cozumle` (YYYY-MM ay, YYYY-QN çeyrek, YYYY yıl; verilmezse son tam ay; süren dönem bugüne kırpılır ve etiketlenir; gelecek dönem
ValueError → 422), `gunluk` (Türkiye günü; geçerli SCADA kWh — energy_kwh yoksa power_kw; saat sayısı; POA toplamı; forecast_daily P50/P10/P90; sapma yalnız
iki değer de varsa), `olaylar` (olay_service.aralik; dönem içi süre), `kullanilabilirlik_olay` (1 − Σ(arıza/hasar süresi × devre dışı güç / kapasite) /
dönem saati; planlı bakım, talimat, acil kesme, şebeke kesintisi istisna; SCADA tabanlı olan Doğruluk'ta kalır), `pr_temel` (IEC 61724-1 temel PR =
(E/P_stc)/(H/G_stc); sıcaklık düzeltmesiz; POA ölçümü olan ≥ 10 gün; yoksa «ölçülen düzlem ışınımı yok»), `uzlastirma` (yalnız ay döneminde:
mutabakat_service.pvquant_kalemleri — Mutabakat ile aynı hesap — ve yüklü EPİAŞ bildirimi yan yana; güvenilirlik ve nedenler; sayaç kapsamı), `veri`
(özet: üretim, beklenen, ortak gün, sapma, kapsam, olay/arıza, en iyi/en düşük gün; **veri durumu** tam ≥ %99,5 ölçülü saat | kısmi | yok, metniyle;
ölçüm yoksa üretim ve beklenen «yok» (None), 0 değil; `kaynaklar` listesi; günlük tablo ay döneminde, aylık tablo çeyrek/yıl), `rapor` (rs.Rapor: Özet —
ilk satır veri durumu —, Günlük/Aylık üretim ve beklenti, Olay kaydı, Uzlaştırma kalemleri + not, Performans oranı, Notlar + kaynaklar; künye + üretim
zamanı), `html` (şablon raporlarla ortak kabuk `sablon_rapor_service.html_sar`). Zamanlanmış gönderim: `gonderim_ayari` / `gonderim_dogrula` (aktif, ayın
günü 1–28, en çok 10 e-posta), `alicilar` (boşsa alarm alıcıları), `gonder` (HTML gövdeli e-posta — posta_service `html` parametresi, multipart/alternative;
durumlar gonderildi / gonderim_hatasi / rapor_hatasi / posta_yapilandirilmadi / alici_yok; sonuç params_json.rapor_gonderim.son_* + deneme sayacı ve denetim
izi), `gonderilmeli_mi` (aktif ∧ bugün ≥ gün ∧ dönem gönderilmemiş; **başarısızlık dönemi kapatmaz**: günde bir, en çok GONDERIM_DENEME = 3 yeniden deneme;
elle «Şimdi gönder» aynı sayaçla yazılır, yineleme yok). Worker `rapor_gonderimi` her gün 05:10 UTC (08:10 TSİ); ISIM_TR «Dönem raporu gönderimi (08:10)».
API: GET `/v1/plants/{id}/rapor-donem?donem&fmt=html|json` (HTML indirme + denetim «rapor_donem_indir»; JSON önizleme), GET/PUT `rapor-gonderim`
(«rapor_gonderim_ayar»), POST `rapor-gonderim/dene` («rapor_gonderim»); rapor-sablon açıklaması dört şablonu sayar.
Web: Raporlar — «Dönem raporu» kartı (seçici: son 12 ay, son 4 çeyrek, bu yıl/geçen yıl; Önizle → veri durumu rozeti + üretim zamanı + 4 KPI + uzlaştırma
tablosu PVQuant ↔ EPİAŞ + notlar; HTML indir), «Zamanlanmış gönderim» kartı (açık/kapalı rozeti, gün, alıcılar, Kaydet, «Şimdi gönder (ay)», son gönderim
«Eylül 2026 raporu, 03.10.2026 08:10 — gönderildi», SMTP yoksa dürüst not); sayfa üst cümlesi mimariye uygun (tahmin bölümleri arşivden, üretim/olay/
uzlaştırma/kalibrasyon kayıtlardan); Tahmin geçmişi «Tahmin modu» A/B/C açıklamalı, adlar mono değil; PDF/Excel/JSON kartlarında düğmeler alta hizalı;
`.kart-arac` şeridi 900 px altında başlığın altına kırılır; App derin bağlantı `#sayfa/santral` (yüklemede okunur, sayfa/santral değişince replaceState,
hashchange; yonetim/yontem dışında); sahte API rotaları; sözlük eylemleri.
Üç inceleme turu (02 M39): son gönderim etiketi ve tarih biçimi, «Şimdi gönder (ay)», «gönderilemedi», dar ekran şeridi; brief ile ikinci tur (veri
bütünlüğü / gönderim / biçim / arayüz, 3 geçiş): veri durumu sınıfı, ölçümsüz dönem, kaynak listesi, yeniden deneme + rapor_hatasi, üst cümle, mod
etiketleri, kart hizası; son kontrol: yeni kusur yok.
Testler: tests/test_aylik_rapor.py 4 (dönem çözümleme 8 durum + yıl geçişi; Ekim 2026 fixture'ı: 20 gün × 10 sa × 100 kWh, 12 gün POA 600 W/m², 31 gün
P50 1.100, arıza 4 sa 500 kW + planlı bakım 3 sa → üretim 20.000, beklenen 34.100, sapma −9,1 %, kapsam %26,9 «kısmi», kullanılabilirlik 1 − 2/744,
PR (12000/1200)/72; HTML bölümleri + «Kısmi: 200/744» + «Kaynaklar:»; Eylül boş dönem → üretim None «yok»; çeyrek aylık tablo; ayar doğrulama; günü gelme
kuralı; gönderim SMTP yok/var → params_json; yeniden deneme: hata → deneme 1, bugün denendiyse bekle, 3'te dur, rapor hatası ayrı durum → deneme 2; API
200/422/404 + denetim). tests/test_olay.py saat bağımlı sabit tarih (02.11 09:30) gelecek ayın ilk günlerine taşındı. Tam takım 871 passed / 1 skipped;
web tsc 0, 103, oxlint 0, build; 1440/768/375 taşma 0 (`kanit/raporlar-donem-{1440,768,375}-2026-11-02.jpg`).
Doğrulanamayan / sonraya: gerçek SMTP teslimi (test monkeypatch); Ekim 2026 canlı kapsamı; 16 sayfa PDF / Excel / JSON / standart PDF bu turda elle
üretilmedi (mevcut testler yeşil); dönem raporu ile Doğruluk günlük toplamlarının çapraz kıyası; PDF eki (HTML gövde); EPI, düzeltmeli PR, kayıp TL, yıl yıl
P-değeri (P8 kalanı, dalga 3); API kapsamları ve panel/API eşitliği (P10 kalanı); dönem seçicinin Doğruluk/Mutabakat'a taşınması.
Tahmin motoru, kalibrasyon ve uzlaştırma formülleri değişmedi.

# Yirmi altıncı paket — v2.526 (02.11.2026 gece, canlı): Sayaç verisi uzlaştırma girdisi — Mutabakat ve dökümde SCADA ya da yüklü sayaç saatleri, SCADA ile fark kıyası, hükümde doğrulama niteliği; «Sayaç verisi eksik» alarmı

Commit `d554cee`, CI #664 (7 dk 56 s). Dağıtım: api + worker + web imajı (ssh; 22. port açıktı); **göç yok** (ayar params_json.uzlastirma_girdi; alarm kuralı/eşiği params_json.alarm_*).
Canlı: index.html ve JS/CSS birebir (25/25); api «startup complete»; worker «basladi»; `mutabakat?uretim=` ucu kimlik olmadan 422/401 döner.
Kaynak: yol haritası dalga 2 P4a-2 (02 M37'de sonraya bırakılan «sayaç → uzlaştırma girdisi») + P7b (sayaç eksik saat alarmı); IH-052/IH-054 (UEVM ≠ SCADA farkının
uzlaştırmaya yansıması), IH-055 (12. gün düzeltme penceresi için eksik sayaç verisi uyarısı).
dengesizlik_service: `URETIM_SECENEKLERI` (scada | sayac), `uretim_secimi(pj)` (params_json.uzlastirma_girdi; varsayılan scada); `program_df(..., uretim)` — «sayac»
seçilince sayaç satırı olan saatlerde gercek_kw sayacın veriş kWh'si (öncelik EPYS > OSOS > MASS > elle), `uretim_kaynak` sütunu (scada | sayac_olculmus |
sayac_tahmini — tahmini/doldurulmuş/veri yok nitelikleri); SCADA'da olmayan saat sayaçla EKLENMEZ (program ve fiyat satırı SCADA'dan kurulur; sonraya);
`_girdiler(..., uretim)` ayarı okur; `dokum(..., uretim)` özete `uretim_kaynak` sayımı + `saat_uretim_kaynak`; sayaçla dökümde `uretim_kaynak` sütunu ve not
(DOKUM_NOTU_SAYAC); SCADA'lı döküm 21/25 sütun aynen. Uzlaştırma formülleri değişmedi; yalnız gerçekleşen serinin kaynağı seçilir.
mutabakat_service: `pvquant_kalemleri(..., uretim)` — seçim parametre > santral ayarı > SCADA; sayaçla hesapta güvenilirlik nedeni («hesap N saatte sayaç
verisiyle (ölçülmüş/tahmini), M saatte SCADA; UEVM ile aynılığı doğrulanmaz»; tahmini ya da SCADA tamamlaması varsa en az «kısmi»), yüklü sayaç saatlerinin
SCADA satırı olmayanı sayılır (`sayac_kullanilmayan_saat`, «yüklü N sayaç saatinden M saat hesaba girmedi»), sayaç seçili-veri yok nedeni; `kiyas` (aynı dönem
SCADA ile hesaba göre dengesizlik neti ve KÜPST borcu farkı; dengesizlikte artı lehte, KÜPST'te artı aleyhte). **Doğrulama niteliği** (02.11 ikinci inceleme):
satır ve özette `dogrulama` tam | kismi | senaryo | yok — kısmi kapsamda «uyumlu / fark var» hükmü korunur ama niteliklidir (EPİAŞ tutarı bütün ayı, PVQuant
tutarı yalnız hesaplanan saatleri kapsar); eylem metni «Kapsam kısmi (saat/beklenen; nedenler): … fark doğrulanmış sayılmaz» ile başlar, uyumlu-kısmi «tam ay
verisiyle kesinleşir»; `ozet.kapsam_saat/beklenen_saat`. Eşik kuralı doğrulandı: bileşen başına |fark| ≤ max(%2 × bildirim, 50 TL), sıfır bildirimde 50 TL,
yüzde paydası |bildirim neti|; KÜPST örneği 81,75 TL ≤ 286,42 → uyumlu; işletme ölçütü (UYUM_NOTU). Sürüm: dosya/kullanıcı etiketi, resmî durum
«doğrulanmadı», takvim çelişkisi satır + notta; dosya ve tarihçe korunur (değişiklik gerekmedi). `mutabakat/ozet(..., uretim)` + `uretim_ayari`, `uretim_secenekleri`.
sayac_service: `ayar_dogrula` uzlastirma_girdi; `ozet.ayar.uzlastirma_girdi` + `uretim_secenekleri`.
alarm_service (P7b): kural `sayac_eksik_saat` («Sayaç verisi eksik»; eşik `sayac_eksik_esik_saat` 24, 1–744): 15 dk sayaçta bu ayın vadesi gelen (m.8(2)) ama
yüklenmemiş saati; aylık okumalı sayaçta veri günü geçmiş önceki dönemin eksiği; gece taraması, günde en çok bir; «EPİAŞ'a ulaşıp ulaşmadığı PVQuant'tan görülmez».
API: GET `mutabakat?uretim=scada|sayac` (422 başka değer), GET `dengesizlik/saatlik?uretim=` (döküm CSV/XLSX/JSON; JSON'da `uretim_kaynak`), PUT `sayac-ayar`
`uzlastirma_girdi`.
Web: Mutabakat — başlıkta üçüncü seçici «üretim: santral ayarı — sayaç / SCADA (geçici) / sayaç, yüklü saatlerde (geçici)» (kalıcı seçim Sayaç sayfasında;
ayarla aynı seçenek aynı sonucu verir — fare ipucunda), «Üretim» satırı seçime göre (saat sayımı, hesaba girmeyen sayaç saatleri, SCADA ile fark cümlesi;
SCADA'da yönlendirme), kart altı sayaçla «Doğruluk'taki 90 günlük hesap SCADA ile kalır», rozet «fark var · kısmi» / «uyumlu · kısmi», Hesaplama farkı KPI altı
«kapsam kısmi (528/744 saat), fark doğrulanmış değil»; Sayaç — «Veri geliş beklentisi» kartında «Uzlaştırma yeniden hesabında üretim» seçici; Santralim —
alarm kuralı açıklaması + eşik alanı «Eksik sayaç saati (adet)» + KURAL_ADI (web bekçisi arka uçla birebir); sahte API (a1 ayarı «sayaç», ?uretim= dalı, alarm).
Üç inceleme turu (02 M40): sahte sayım tutarsızlığı; brief (mali karşılaştırılabilirlik / kaynak / sürüm / eşik; 3 geçiş) → doğrulama niteliği, kullanılmayan
sayaç saati, seçici etiketleri (375'te 80 px taşma → kısaltma + select en fazla görünüm genişliği); son kontrol: Türkçe sayı eki → ek gerektirmeyen cümleler.
Testler: test_sayac +1 (program_df sayaç girdisi 08–10 TSİ → 600/700/200 kWh, kaynak etiketleri, SCADA saati kalır; uretim_secimi; _girdiler ayarı; ayar_dogrula;
ozet), test_mutabakat +1 (40/4/4 saat; kiyas EDT +7.200 / KÜPST +480; «kısmi»; santral ayarı; SCADA varsayılan kıyassız; sayaç seçili-veri yok; kullanılmayan
16 saat; ozet seçenekleri) + doğrulama niteliği (kısmi/tam/senaryo satır ve özet, eylem ön eki) + API ?uretim 422/200, test_alarm_p7a +1 (kural, eşik, mesaj,
1–744). Tam takım 874 passed / 1 skipped; web tsc 0, 103, oxlint 0, build; Mutabakat ve Sayaç 1440/768/375 taşma 0 (`kanit/mutabakat-sayac-girdi-*`, `kanit/sayac-girdi-ayar-*`).
Doğrulanamayan / sonraya: sayaç dosyasının UEVM ile aynılığı (EPYS dışa aktarımı birebir sınanmadı); SCADA'sız saatlerin sayaçla eklenmesi; resmî saatlik
tutar yok → eş kapsamlı karşılaştırma üretilmedi, orantılı paylaştırma yapılmadı (P2b-2); Doğruluk 90 günlük simülasyon SCADA ile kalır; 15 dk DGP geçişi.
Tahmin motoru, kalibrasyon ve uzlaştırma formülleri değişmedi.

# Yirmi yedinci paket — v2.527 (03.11.2026 gece, canlı): Mutabakat — EPYS saatlik detay dosyası içe alma, eş kapsamlı saatlik kıyas ve fark ayrıştırması (fiyat / üretim / program / EDM-pozisyon / yuvarlama / kural-yön)

Commit `55b2ef7`, CI #666 (4 dk 31 s). Dağıtım: api + worker + web imajı (ssh; 22. port açıktı); **göç `v2527_saatlik_detay` canlıda DB sahibiyle** (uzlastirma_saatlik,
RLS, pvq_app SELECT/INSERT). Canlı: index.html ve JS/CSS birebir (25/25); api «startup complete»; worker «basladi»; `mutabakat/saatlik` ucu kimlik olmadan 422.
Kaynak: yol haritası dalga 2 P2b-2 (02 M36/M40'ta sonraya bırakılan) ve 02.11 Mutabakat brief'inin «eş kapsamlı karşılaştırma» boşluğu; IH-028 (EPYS dökümlerinin içe
aktarımı: saatlik detay XLSX — UEVM, KUDÜP, BUDÜP, YALM/YATM, PTF, SMF, KÜPSM/KÜPST, EDM/EDT), 02-24 (EPYS detay ekranları kolonları; resmî dosya başlıkları görülmedi).
saatlik_detay_service: `dosya_oku` (CSV/XLSX 20.000 satıra kadar; başlık = tarih (+saat) sütunu + ≥2 bilinen ölçüm sütunu; dd.mm.yyyy[ HH:MM], yyyy-mm-dd[ HH:MM:SS],
«HH:00-HH:00», 0–23; Türkiye saati → UTC saat başı; yinelenen saat son satır; dönem ilk satırdan, çok ay uyarısı; ekran türü sütunlardan detay | dengesizlik | kupst),
`kaydet` (≤5 MB; dönem uyuşmazlığı/gelecek 422; her yükleme yeni yukleme_id, silme yok), `yuklemeler`, `oku` (ekran bazında en son yükleme, saat bazında dış birleşim,
«detay» öncelikli), `kiyas` (PVQuant dökümü dönem dilimi UTC'ye çevrilir; yalnız ortak saatler; toplamlar EDT net/pozitif/negatif ve KÜPST EPİAŞ ↔ PVQuant, UEVM ↔
gerçekleşen; ayrıştırma sırası: fiyat |ΔPTF/SMF| > 0,01 TL/MWh → üretim |UEVM − gerçekleşen| > 0,5 kWh → program |BUDÜP − program| > 0,5 kWh → EDM/pozisyon (üretim ve
program eşitken EPİAŞ EDM ≠ PVQuant sapması: İA / pozisyon / DSG payı) → yuvarlama (girdiler tolerans içinde, sıfır değil, |ΔEDT| ≤ 5 TL) → kalan kural/yön (k/l, sürüm,
hesap); satırda EDM/sapma ve PVQuant'ın sistem yönü; `neden_aciklama`; en büyük 10 saat; saatlik satırlar), `kiyas_csv`, `ozet_kisa`. mutabakat_service: yanıta
`saatlik_detay` özeti; eylem metninde kapsam notundan SONRA «Eş kapsamlı kıyas (ortak N saat): dengesizlik neti EPİAŞ / PVQuant / fark» (bildirim olmasa da).
API: POST `/v1/plants/{id}/mutabakat/saatlik` (dosya, donem; denetim «mutabakat_saatlik_yukle»), GET `…/mutabakat/saatlik?donem&uretim&fmt=json|csv»
(«mutabakat_saatlik_indir»); sözlük etiketleri.
Web: Mutabakat — «Saatlik detay kıyası (EPYS)» kartı (yükleme formu; KPI'lar: ortak saat, dengesizlik neti EPİAŞ, dengesizlik neti PVQuant, **eş kapsamlı dengesizlik
farkı** + KÜPST borcu ayrı satır; fark ayrıştırması cümlesi; en büyük farklı 10 saat tablosu — PTF, UEVM/gerçekleşen, BUDÜP/program, EDM/sapma · yön, EDT net, fark,
neden + ipuçları; CSV); «Hesaplama farkı (aylık bildirim)» KPI'sında ikincil satır «saatlik eş kapsamlı, N saat (yalnız dengesizlik)» — iki ölçü ayrı etiketli, birleşik
eş kapsamlı toplam HESAPLANMADI; sürüm durumu üç yerde aynı: «nihai bildirim (dosyada) — resmî doğrulama bekleniyor» (KPI altı, çip, veri kartı + resmî yayın tarihi);
«Hesaplamada kullanılan veriler» sadeleşti (Kapsam, Üretim, Program, Fiyat, Bildirim sürümü, Ne yapmalı; «Ayrıntılar» açılır: kural sürümü, güvenilirlik nedenleri,
sayaç ↔ SCADA, sürüm takvimi); sahte API (a1 Ekim 2026: 744 EPİAŞ saati, 528 ortak; sayaç/SCADA dalı).
Üç inceleme turu (02 M41): KPI karışması (eş kapsamlı fark ikincil satır) + eylem sırası; brief (mali kapsam / saatlik kıyas / KÜPST / sürüm / kaynak / arayüz, 3 geçiş)
→ neden sınıfları, etiketler, sürüm durumu, kart sadeleştirme; son kontrol: yeni kusur yok. Oturum yenilenince scratchpad silindi (sahte derleme, sahte API, önizleme,
commit taslağı, başsız Chrome, test DB yeniden kuruldu).
Testler: tests/test_saatlik_detay.py 4 (CSV 48 saat tanıma, XLSX tek hücre tarih-saat, yalnız KÜPST ekranı, başlıksız hata, yinelenen/çok ay, _zaman biçimleri;
kayıt + dönem uyuşmazlığı + gelecek; ekran bazında son yükleme birleşimi 48+1 «detay» öncelikli; kıyas 72 PVQuant ↔ 48 EPİAŞ → ortak 48, ayrıştırma 10/10/5/5/2/5,
EDT farkı 37 saat, toplam −427 TL, CSV 50 satır + EDM/sapma/yön sütunları; mutabakat özeti + eylem; döküm yoksa ortak 0; API 201/422/200/csv/404). Tam takım 878 passed / 1 skipped;
web tsc 0, 103, oxlint 0, build; Mutabakat 1440/768/375 taşma 0 (`kanit/mutabakat-saatlik-detay-{1440,768,375}-2026-11-02.jpg`).
Doğrulanamayan / sonraya: EPYS XLSX'in gerçek başlıkları ve sayfa düzeni (BULUNAMADI; tanıma esnek, gerçek dosyayla sınanmalı); UEÇM / ikili anlaşma / YEK sütunları
saklanır, kıyaslanmaz; DSG üyeleri için grup bazlı saatlik EDT kapsam dışı («pozisyon» sınıfına düşer); saatlik toplam ↔ aylık bildirim kalemi köprüsü; birleşik eş
kapsamlı toplam (dengesizlik + KÜPST) bileşen/işaret uyumu belgelenmeden verilmez.
Tahmin motoru, kalibrasyon ve uzlaştırma formülleri değişmedi.

# Yirmi sekizinci paket — v2.528 (03.11.2026, canlı): Dış API rezerve dört kapsam canlı, Hakkında kural tablosu (panel/API eşitliği), alarm adları tek sözlük, Portföy segment etiketi; üç inceleme turu (kural tablosu dönem bütünlüğü, webhook SSRF, portföy tutarlılığı)

Commit `717a77b`, CI #668 (6 dk 7 s). Dağıtım: api + worker + web imajı (ssh); göç yok. Canlı: index.html ve JS/CSS birebir (25/25); api «startup complete»; worker «basladi».
Kaynak: yol haritası dalga 2 P10 kalanı — envanter «rezerve API kapsamları» (ENV-100), ENV-F04 (kural tablosu yalnız API'de), ENV-F05-3/4 (ham segment kodu, zilde «Alarm»).
api_anahtar_service: `CANLI_KAPSAMLAR` altı kapsam + `KAPSAM_ACIKLAMA` (GET /v1/api-anahtarlari `kapsam_aciklama`). Dış API (X-API-Key): GET `/v1/dis/santral/{id}/gerceklesen?bas&bit&kaynak=scada|sayac`
(«gerceklesen:oku»; saatlik kWh UTC; SCADA geçerli ölçüm + kaynak etiketi ya da yüklü sayaç verisi + nitelik; ≤92 gün, varsayılan son 7 gün; «UEVM değildir»), GET `…/alarmlar?n» («alarm:oku»; kural
kodu + Türkçe adı), GET `…/rapor-donem?donem&fmt=json|html` («rapor:indir»; panelle aynı hesap; denetim aktör yok + anahtar öneki), PUT `…/ayarlar` («santral:yaz»; yalnız sayaç ayarı alanları,
panelin ayar_dogrula'sı; boş 422). Kapsam yoksa 403, geçersiz anahtar 401, oran 429. `docs/api/dis-api.md` güncel.
Web: Hakkında «Uzlaştırma kuralı sürüm tablosu» kartı (GET /v1/kurallar; geçerlilik, sürüm, rejim, k/l sistem açığı/fazlası, V, KÜPST m/n, DSG eşiği, dayanak; 2027 «belirsiz» rozeti);
alarm kuralı adları `web/src/lib/alarmSozluk.ts` (Santralim + zil; bekçi testi arka uç KURAL_ETIKET ile kıyaslar); Portföy «Segment» kısa etiket; Ayarlar kapsam listesi altı kapsam + açıklama ipucu + API uçları.
Üç inceleme turu (02 M42): (1) yedi kare → sahte API: segment alanı, güvenlik politikası/denetim rotaları. (2) brief «Portföy, Ayarlar ve Hakkında: kapsamlı teknik denetim» (3 geçiş, 13 bölüm) →
**kural tablosu dönem bütünlüğü (gerçek kusur):** `kr.tablo` el yazımı sınır listesi 1.2.2023 Karar 11589-2 geçişini atlıyordu (satır m 0,10 derken motor 0,12; hesap doğruydu) → sınırlar motor
gün gün taranarak imzadan türetilir (`donem_sinirlari`; AFL imza dışı, satırda AFL başı/sonu + `AFL_degisken`), tablo 9 → 7 satır; **webhook SSRF (gerçek kusur):** `url_gecerli` https'li iç ağ /
özel IP / 169.254 meta veri / `.internal` kabul ediyordu → `_ic_adres` reddi (ad çözümü yok, bilinen sınır); **43,5 MWh (1.830,2 ↔ 1.786,7):** gerçek kodda özet kartı ve günlük tablo aynı koşu
seçimi (`ORDER BY run_at DESC LIMIT 1`, ≥20 saat), fark sahte sabitlerdendi; koşusu olmayan santral `santral_eksik` ile tabloda söylenir; WMAPE kartı «kapasite ağırlıklı · N santral ölçüm yetersiz»;
sahte Hakkında kaynak satırı gerçek atıf şekline (ECMWF/DWD CC BY 4.0). (3) yedi kare → sahte API: DSG üyeleri (dengesizlik taşıyan dört santral) ve fiyat kaynağı KÜPST kartıyla aynı (EPİAŞ),
UEVÇB tek lisanssız üye, ekip son giriş, günlük tablo notu.
Gözlemler (kusur değil): alarm toplamı satır sorgusuyla aynı, yineleme kilidi 23 sa / 60 gün; «bildirildi» beyan; DSG «varsayımsal kıyas»; EPİAŞ senaryo saatleri her kartta sayıyla; 2FA TOTP +
kurtarma + yönetici sıfırlama; parola ≥10 bcrypt + oturum sürümü; giriş 5/dk; API anahtarı HMAC/kapsam/süre/rpm/iptal; paylaşım süre/iptal/izin/denetim; arşivli santral listelerden düşer, kimlikle
okuma aynı kiracıda.
Testler: tests/test_dis_api.py +1 ve SSRF (14 kötü / 2 iyi adres); tests/test_kurallar_gecis.py 4 (dönemler bitişik/çakışmasız; her gün 2023-01-01 → 2027-06-01 üç segmentte satır = kural();
sınır günleri 1.1.2026 rejim, 19.10.2026 toplama, 1.11.2026 V 150 → 100, 2027 belirsiz; saatlik çerçeve 31.10 → 1.11 İstanbul gününe göre; 2025 dilimine bugünkü kural sızmaz);
tests/test_portfoy_tutarlilik.py 1. Tam takım 884 geçti / 1 atlandı; web tsc 0, 103, oxlint 0, build; Portföy / Hakkında / Ayarlar 1440/768/375 taşma 0 (`kanit/*-2026-11-03.jpg`).
Doğrulanamayan / sonraya: webhook adının özel IP'ye çözülmesi (ağ katmanı); API anahtarı döndürme ucu (bugün yeni anahtar + eski iptal); portföy KÜPST `kural_dayanak` metni dönemin ilk saatinden
(sürüm sütunu saat bazında doğru); EPİAŞ durum kartında son başarılı istek / son hata alanı yok; meteoroloji arşivinde son deneme ↔ son başarılı indirme ayrımı yok; `santral:yaz` künye/segment/tarife
alanlarını kapsamaz (bilinçli); canlı EPİAŞ bağlantısı ve arşiv tazeliği bu turda doğrulanmadı.

# Yirmi dokuzuncu paket — v2.529 (04.11.2026, canlı): Doğrulama düzeltmeleri — kapsamlı doğrulama arşivinin A kanıtlı çürütmeleri koda (1.1.2025 öncesi DSG üye eşiği yok, 2024 ve öncesi KGÜP kesimi 16:00, AFL/1.11.2026 çıkarım/teminat/segment etiketleri)

Commit `36384c4`, CI #670 (6 dk 27 s). Dağıtım: api + worker + web imajı (ssh); göç yok. Canlı: index.html ve JS/CSS birebir (25/25); api «startup complete»; worker «basladi».
Kaynak: `~/Desktop/PVQuant_Kapsamli_Dogrulama_Arastirmasi` (Opus, 03–04.11.2026; 1.040 DK, 15 küme raporu, 1.151 kaynak; 31/40/50 ve KK3 girdi yürüyüşü henüz eksik — pazar). Yalnız kanıt düzeyi A çürütmeler ve
etiket düzeltmeleri; uzlaştırma formülleri değişmedi.
DK-249 (ÇÜRÜTÜLDÜ, A): m.111(3)-(5) RG 17.12.2024-32755 Md.24 ile eklendi, Md.30 ile 1.1.2025 yürürlük; EPDK 19.12.2023 konsolidesinde m.111 yalnız (1)-(2) → 1.1.2025 öncesi üye eşiği yok. `kurallar.dsg_esigi`
1.1.2025 öncesi `None` + dayanak; `Kural.dsg_esik: float | None`; `dengesizlik.dsg_saatlik` eşik yoksa sapmanın tamamını grupta netleştirir (`edt_bireysel` 0); `dsg_ozet` esik `None`, kart cümlesi
«Bu dönemde üye eşiği yoktur …» (`_esik_cumlesi`), CSV başlığı «yok (1.1.2025 öncesi)»; Hakkında tablosunda 2023–2024 satırları «—» (dayanak ipucunda) + tablo altı görünür not. C geri testi (27.10.2025–26.10.2026)
hedefleri değişmedi.
DK-154 (ÇÜRÜTÜLDÜ, A): RG 14.04.2009-27200 m.69(1) asıl metin ve 19.12.2023 sürümü «16:00»; 15:30 RG 32755 Md.17/18/20 ile 1.1.2025'ten. `kurallar.kgup_kesim(tarih)` → (16,0)/(15,30) + dayanak;
`kgup_service.kaynak_kosu_df` ve `dengesizlik_service.program_df` SQL'i (`CASE WHEN CAST(… AS date) < '2025-01-01'`; `::date` yazımı text() bağlı parametresiyle karıştığından CAST) tarihe bağlı.
DK-044 (KISMEN, A): AFL Karar 11933 etiketi «yürürlük maddesi yok — Usul ve Esaslar Md.4(5) lafzen 1.8.2023, EPİAŞ 4.7.2023 teslim gününden uyguladı; uygulama tarihi esas alındı»; değer/tarih aynı.
DK-002 (A, tarih çıkarım): Karar 14911 ve 14907 Md.7 «yayımı takip eden fatura dönemi»; 1.11.2026 kararda yazmaz, EPİAŞ uygulama duyurusu bulunamadı → edt_kurali ve kupst-14907 dayanaklarına «1.11.2026 çıkarım»;
sınır değişmedi (41_Acik_Sorular EPİAŞ-01).
DK-537 (ÇÜRÜTÜLDÜ, yalnız C): Teminat Hesaplama Yöntemi m.7 «aylık ağırlıklı ortalama SMF» piyasa geneli dengesizlik ağırlıklı; kod düz aylık ortalama → docstring düzeltildi, yanıta `smf_agirlik`, not
«SMF ortalaması ağırlıksız, yaklaşık»; hesap değişmedi (ağırlık verisi yok).
DK-292 / DK-652 (ÇÜRÜTÜLDÜ, A): `segment.KURALLAR` fiyat etiketleri «YEK fiyatı: Cetvel I (USD cent × günlük TCMB kuru) ya da 7189 CK aylık ilan», «LÜY fiyatı (GTŞ alımı, 10 yıl) / sonrası CK 11415»;
`gelir()` docstring'ine çağrılmadığı ve iki dalın düzeltilmeden bağlanmaması uyarısı (gelir tarife_service'ten).
İnceleme (02 M43): bir kare — tablo doğru; «—»nin anlamı yalnız ipucundaydı → görünür not. Sahte API'nin giriş ucu yok; önizleme örnek jetonla.
Testler: tests/test_dogrulama_v2529.py 4 (eşik None/0,10/0,05 + tablo + saatlik çerçeve 30–31.12.2024; 2024 DSG tam netleşme ↔ 2025 %10 bireysel kalan; kesim 16:00/15:30; etiketler lafzen/çıkarım).
Etkilenen 12 modül 66 geçti; tam takım 888 geçti / 1 atlandı; web tsc 0, 103, build; Hakkında 1440/375 taşma 0 (`kanit/hakkinda-dsg-esigi-2025-oncesi-2026-11-04.jpg`).
Sonraya: etki matrisindeki diğer 53 değer değişikliği satırı (AFL 2015–2019 DK-016/031/082, saatlik çerçeve DK-180/195, eşik etiketleri DK-239, YEKDEM DK-288/294/314/315, teminat DK-527/528/533, segment
DK-644/653/654/662/668/785, saatlik detay DK-430, sayaç DK-374/382/383 …) kanıt düzeyine göre (A hesapta, B/C etiket); 02.02.2020 öncesi m.111 sürümleri okunmadı; arşivin 31/40/50 + KK3 kapanışı.

# Otuzuncu paket — v2.530 (04.11.2026, canlı): Vitrin metin düzeltmeleri K-09…K-11 (veri yükleme vaadi, dosya biçimleri, TPYS şablon düzeni, 15 dk dilim, alarm kuralı sayısı, bülten sınaması)

Commit `91cd8dc`, CI #672 (5 dk 11 s). Dağıtım: yalnız web imajı (ssh); göç yok; arka uç değişmedi. Canlı: index.html ve JS/CSS birebir (25/25).
Kaynak: YOL-HARITASI-2026-10-31 «Vitrin ve iletişim düzeltmeleri (hemen; kod değil metin)» — dalga 1'de açık kalan tek kalem.
Değişen ifadeler: Hero mikro künyesi «veri yüklemeniz gerekmez» → «piyasa kimliği olan lisanslı santralde veri yüklemeniz gerekmez»; başvuru formu «Başvuru için veri yüklemeniz gerekmez»;
İş ızgarası / Türkiye piyasası / üst çubuk «CSV/XLSX» → «KGÜP ve EAK CSV; toplayıcı dosyası XLSX»; Dört adım ve Türkiye piyasası «TPYS şablonuyla birebir» → «TPYS CSV şablonu düzeninde; ondalık
ayraç şablonda örneklenmediğinden nokta varsayılır, isterseniz biçim kendi örnek dosyanızdan öğrenilir» (kgup.SABLON_DURUMU ile aynı dil); «saatlik (15 dk veri hazır)» → «saatlik; dengeleme biriminde
15 dk dilim» (kgup.ceyrek_dilimle yalnız dengeleme birimi ve ≥200 MWh sıçrama saatleri — ilk yazım «15 dk profile bölünmüş» inceleme turunda fazla iddia bulundu); Disiplin bandı «2 + 6 alarm kuralı»
→ «2 + 13» (alarm_service: 2 varsayılan + 13 ek = 15); Türkiye piyasası «pilotla doğrulanmaktadır» → «hesap piyasa işletmecisinin aylık bülten değerleriyle sınanmıştır (45 kalem, en çok 0,011 TL fark)»
(v2.513 bülten doğrulaması). «Kimin için» listesi P6 kararına kadar aynı; rakamlar bandı 29.10.2026 tarihli kaldı (888 + 103 güncellemesi sonraki pakette).
Bekçi dersi: gizlilik bekçisi (`web/test/vitrin/gizlilik.test.ts`) vitrin dosyalarında kurum adını (EPİAŞ/Şeffaflık) yasaklar → «piyasa kimliği», «piyasa işletmecisi».
İnceleme (02 M44): iki tur — /yontem kartları ve ana sayfa; tek düzeltme 15 dk ifadesi. Not: TurkiyePiyasasi kartları /yontem sayfasında; sahte API'nin giriş ucu yok, önizleme örnek jetonla.
Testler: web tsc 0, npm test 103 (vaat kuralı, gizlilik ve dil bekçileri), oxlint 0, build; «/» ve «/yontem» sayfa metninden yeni ifadeler var / eski ifadeler ve kurum adı yok;
`kanit/vitrin-k09-k11-{1440,375,yontem-1440}-2026-11-04.jpg`. Arka uç testleri koşulmadı (Python dosyası değişmedi).

# Otuz birinci paket — v2.531 (04.11.2026, canlı): Sessiz kusur düzeltmeleri (P8) — bankable bozunma σ, kayıp zinciri kısıntı anahtarı, MTBF/MTTR olay kaydına bağlı, aylık üretici işler izlemede, teknik kullanılabilirlik ve kayıp zinciri etiketleri, vitrin rakamları 04.11

Commit `bebc613`, CI #674 (7 dk 41 s). Dağıtım: api + worker + web imajı (ssh); göç yok. Canlı: index.html ve JS/CSS birebir (25/25); api «startup complete»; worker «basladi».
Kaynak: YOL-HARITASI P8 «sessiz kusurlar (düzeltme)»; UYGULAMA-ENVANTERI ENV-F05-1/2, F06, F09, F10, K-06, K-07, B20. Formül değişmedi.
ENV-F05-1: `bankable_service.hesapla` var olmayan `saglik_service.hesapla`'yı çağırıyor, try/except yutuyor, bozunma belirsizliği (σ) hep 0 kalıyordu → `saglik_service.saglik`; bozunma güven aralığı olan
santralde σ bileşeni bütçeye girer. ENV-F05-2: `kayip_service` hijyen özetinde olmayan `beklenen_saat` anahtarını okuyor, kısıntı payı hep 0 → `kisinti_aranabildi`. B20: docstring «ayda bir» →
zamanlanmış iş yok, panelden «Yenile». ENV-F10: `kullanilabilirlik_service.mtbf_ozeti` (saf) + `ariza_istatistigi` — olay kaydındaki «ariza» olaylarından `ext.standart.kullanilabilirlik.mtbf_mttr`
(IEC 61724-3: MTBF = (dönem − toplam onarım)/arıza sayısı, MTTR = ortalama onarım); açık arıza pencere sonuna kadar, planlı bakım/talimat sayılmaz; yanıt `ariza_olay_sayisi`, `mtbf_saat`, `mttr_saat`.
ENV-F06: `IZLENEN_ISLER`'e aylik_kalibrasyon / aylik_iklim / aylik_bankable (aylık, santral başına; temizlik işlerinin önünde — test_faz3_sistem_izleme dizin bazlı). ENV-F09: iklim_service docstring 20 → en çok
19 yıl (2005–2023); ekran zaten veriden yıl sayısı yazıyor. Web: Santralim «Teknik kullanılabilirlik (30 gün)» + «sözleşmesel tanım O&M sözleşmenize göre ayrı» + olay kaydından MTBF/MTTR satırı
(yalnız arıza varsa) + alarm koşul cümlesi «teknik kullanılabilirliği» (K-07); Kayıp zinciri kartı altı «tipik yıl ışınımı ve tipik varsayılanlarla hesaplanır, gerçekleşen üretim değildir» (K-06); vitrin
rakamlar bandı 04.11 sayımı («900 otomatik test» = 892 + 103 yüzlüğe aşağı; bulgu sayısı 29.10 defterinden işaretli). ENV-119 `kurtarilan_tl`: etiket zaten «Referans programa göre fark · varsayımsal», alan adı sözleşme.
İnceleme (02 M45): altı kare — alarm koşul cümlesi hizalandı; sahte API kayıp zinciri tablosu nota uymuyordu → ardışık zincir, şebeke/PR/özgül satırlardan.
Testler: tests/test_sessiz_kusurlar_v2531.py 4 (işlev adı var olan fonksiyona; anahtar hijyen özetiyle aynı; MTBF/MTTR deterministik 2 arıza → MTTR 74 sa, MTBF 46 sa; izleme listesi + ISIM_TR).
Tam takım 892 geçti / 1 atlandı (ilk koşuda 1 başarısız: dizin bazlı test, sıralamayla çözüldü); web tsc 0, 103, oxlint 0, build; Santralim 1440/375 taşma 0
(`kanit/santralim-teknik-kullanilabilirlik-mtbf-2026-11-04.jpg`, `kanit/vitrin-rakamlar-0411-2026-11-04.jpg`).
Doğrulanamayan / sonraya: bankable σ etkisi canlı santralde ≥13 ay ölçüm ister; MTBF yalnız olay kaydına girilen arızalardan (otomatik tespit edilen arıza saatleri olay değildir); kullanılabilirlik
istisna/birim bazlı kütüphane (zaman/enerji tabanlı, `birim_bazli`, `sozlesme`) hâlâ bağlı değil → P8a performans katmanı; «32 kapatılmış bulgu» yeniden sayılmadı.

# Otuz ikinci paket — v2.532 (04.11.2026, canlı): Doğrulama düzeltmeleri II — AFL 2017 halkası, YEKDEM süre sınırı ve CK 2949, 7189 yedek dal kapalı, m.23(6) KGÜP = 0 okuması, sayaç çekişinden UEÇM, teminat katsayısı notu; saat × gün hata haritası kaldırıldı, saat profili Kalibrasyon'da

Commit `f396f9c`, CI #676. Dağıtım: api + web imajı (ssh); göç yok. Canlı: index.html ve JS/CSS birebir (25/25); api «startup complete», worker «basladi»; /hata-matrisi canlıda 404, /saat-profili kimliksiz 422.
Kaynak: 03.11.2026 doğrulama arşivinin 04.11 kapanışı (1.040 DK; 40_Yonetici_Degerlendirmesi «en yüksek etkili 10 bulgu», 30 etki matrisi #1–#25). Ölçüt: kanıt A, müşteriye görünen yolda,
yürürlükte ya da geriye dönük hesapta. Formül çekirdeği değişmedi; UEÇM girdisi motorda zaten vardı (uecm_mwh), servis geçirmiyordu.
DK-016/DK-082 (KISMEN, A): `_AFL_ZINCIRI`'ne Karar 6851 Geçici 1(3) (RG 6.1.2017-29940) — 7.1.2017–28.2.2017 teslim günleri 500 TL/MWh, 1.3.2017'den 2.000; RG lafzı 6.1.2017 ve 1.3.2017
günleri açık (EPİAŞ 5.1.2017 ve 24.2.2017 duyuruları esas; 41 EPİAŞ-158 sorusu). 2016 ve 2018–2019 ara kararı hâlâ doğrulanmadı (etiket).
DK-306/DK-304 (A): `takvim.yekdem_suresi` 1.1–30.6.2021 girişli tesiste CK 2949 m.1(1) (RG 18.9.2020-31248) — Cetvel I 31.12.2030'a kadar (ilk yıl 2022, son yıl 2030; eski kod 5905-27
grubuyla 2031 veriyordu). `rejim_turet` kaynak cümlesi CK 2949'u söyler.
DK-287/DK-285 (A): `yekdem_service.gunluk_fiyat_serisi` destek süresi dolan günlerde fiyat üretmez (kaynak `sure_doldu`): Cetvel I → takvim son yararlanma yılı (5905-27 / 2949 / kullanıcı
başlangıç yılı); 7189 → işletmeye girişten 10 yıl (Ek-1). Süre türetilemiyorsa sınır yok.
DK-294 (KISMEN, A): `tarife_service._yekdem_tarife` 7189 rejiminde ilan yoksa ¢ × elle kur üretmez, açık hata («ilan Yönetim › Fiyat ve kur'dan girilir»); yedek dal yalnız Cetvel I'de.
DK-301 (A): m.23(6) işaretinde bildirilen KGÜP yüklenmemiş saatler için mevzuat okuması ayrı sütun (kgup0_mwh/kgup0_tl: KGÜP = 0 → üretimin tamamı, program altı saatler dâhil) ve özette
kgup0_saat/mwh/tl; Doğruluk cümlesi iki okumayı yan yana verir («dosya yüklenmedi ≠ EPİAŞ'a bildirilmedi» — 14 raporu §9 tutumu). Program okuması değişmedi.
DK-180/DK-195/DK-192 (A): `program_df` sayaç satırındaki çekişi `cekis_kw` olarak taşır; `saatlik_hesap` 1.11.2026'dan net sapmada UEÇM olarak düşer (motor `uecm_mwh`); pv'ye `uecm` ve `net_sapma`
sütunu; program özetinde `uecm_saat`, `net_sapma_saat`, `uecm_etiketi` («UEÇM verisi yok, 0 varsayıldı: net sapma brüt sapmaya eşit» ya da «N saatte sayaç çekişinden»); KÜPST etiketi ve
döküm notu bunu söyler. Gece KGÜP = 0 saatinde çekişin KÜPSM'e girmesi (DK-192 çıkarımı) motor formülünün sonucudur, ayrı kural eklenmedi.
DK-528 (KISMEN, A): teminat notu «risk katsayısının başlangıç değeri 1,5 — Teminat U&E Geçici m.1; güncel değer katılımcı portalında, kamuya açık kaynakta bulunamadı»; motor varsayılanı 1,0
kaynaksız diye işaretli, servis varsayılan kullanmaz (değişmedi).
Hata haritası (kullanıcı kararı, 04.11): Doğruluk'taki saat × gün hata haritası (v2.111, 720 hücre + visualMap) kaldırıldı — müşteri için karar üretmiyor, günlük sütun = WMAPE grafiği,
saat profili tek özetiydi; 1440'ta sayfa 4.028 → 3.842 px. Haritanın işe yarar bilgisi (saate göre sistematik sapma) Kalibrasyon sayfasına «Saate göre ortalama sapma» kartı olarak taşındı:
accuracy_service.saat_profili_hesapla (saf; saat başına ortalama işaretli hata, mutlak hata, n; sistematik = |ort| ≥ %5 kapasite ve n ≥ 5) + /saat-profili ucu (/hata-matrisi kalktı);
kart yatay çubuk + bitişik saat aralıklarıyla cümle («12–15 saatlerinde ortalama +647 kW fazla tahmin»), AC sınırı/kırpma ve sabah sis ipucu. ECharts'tan HeatmapChart ve VisualMapComponent çıktı.
Alınmayanlar: `gelir()` yolundaki lisanssız satırları (DK-644/652/653/654/662/668/785) — fonksiyon bağlı değil; DK-326 (YEKBED net/brüt, kanıt E); DK-322 yerli katkı süre başlangıcı (gün mü
takvim yılı mı açık); DK-660 LÜY Ek m.4 (talimat verisi yok); DK-315 depolamalı (veri yok).
Testler: tests/test_dogrulama_v2532.py 7 (saat profili saf çekirdek — sistematik öğle saatleri, eşik altı sabah, boş/kısa pencere; AFL 6851 sınır günleri; 2949 grubu; süre doldu Cetvel I/kullanıcı yılı/2949/7189; 7189 yedek dal hatası; m.23(6) KGÜP = 0 okuması; UEÇM net sapma
KÜPSM = 0,3 − 0,08 ve 1.11 öncesi etkisiz), test_sayac çekiş sütunu, test_yekdem 2045 → sure_doldu. Tam takım 899 geçti / 1 atlandı (7 dk 10 s); web tsc 0, 103, oxlint 0, build.
Doğruluk (a3) ve Kalibrasyon 1440/375 taşma 0 (`kanit/dogruluk-m23-6-kgup0-2026-11-04.jpg`, `kanit/kalibrasyon-saat-profili-2026-11-04.jpg`). Sahte API tarihinde (29.10) net sapma yok → UEÇM etiketi canlı veride 1.11 sonrası görünür.

# Otuz üçüncü paket — v2.533 (04.11.2026, canlı): P8a performans katmanı I — gerçekleşen kayıp ayrışımı (kWh / TL / EPI), PR'da kırpma işareti, kullanılabilirlik sözleşme eşiği ve açığı

Commit `4110dbb`, CI #678. Dağıtım: api + web imajı (ssh); göç yok. Canlı: index.html ve JS/CSS birebir (25/25); api «startup complete»; /kayip-ayrisimi kimliksiz 422.
Kaynak: YOL-HARITASI P8 (IH-087 kayıp ayrıştırma kWh ve TL; IH-084 kırpma işaretli PR; IH-083 EPI «kısmen»); K-07 sözleşmesel kullanılabilirlik; ENV-F10 kütüphanenin `sozlesme()` dalı.
P8'in kalanı (ölçülen havayla beklenen seri, yıl yıl P-değeri ve bütçe kıyası, sensör envanteri) P8b'ye.
Kayıp ayrışımı: `kayip_ayrisimi_service.hesapla_df` (saf) — üretim mümkün saatlerde (beklenti > %2 kapasite) neden ataması öncelik sırasıyla olay kaydı (talimat YAT/YAL,
planlı bakım, şebeke kesintisi/acil kesme/uzaktan açma → şebeke, arıza/hasar), hijyen «kisinti», AC kırpma (kWh HESAPLANMAZ: beklenti AC sınırını içerir), otomatik arıza
(beklenti > %10, üretim < %0,5), ölçüm yok, kalan «açıklanmayan sapma» (kayıp toplamına girmez); kayıp = max(beklenen − gerçek, 0); TL = kWh × saatin satış fiyatı
(`tarife_service.yapi` — sabit / çok zamanlı / PTF endeksli / YEKDEM gün fiyatı; tarife yoksa PTF, senaryo saatleri sayılır); EPI = Σgerçek/Σbeklenen; satırda `kpi_disi`
(olay_service TUR_KURAL istisnası, kısıt/kırpma evet, arıza hayır). Uç `/v1/plants/{id}/kayip-ayrisimi?gun`. Dürüstlük notu yanıtta: beklenen hava tahmini girdili fizik
modeli (saha ışınım sensörü akışı yok), TL gelir kaybı tahmini, fatura/uzlaştırma kalemi değil.
PR: `pr_karti` sorgusuna `kirpma`; `pr_hesapla` kırpılan saat sayısı ve kırpma dışı PR (≥ 24 kalan saatte yeniden hesap). Santralim PR satırı: «AC sınırında kırpılan N saat dışında %x».
Kullanılabilirlik: `hesapla_df` → `beklenen_kwh`; `sozlesme_acigi` — `params_json.kullanilabilirlik_sozlesme` (0,5–1; PlantAyar alanı, 422 doğrulama) girildiyse
`kl.sozlesme(A_t, eşik, beklenen_kwh, birim fiyat)`; birim fiyat tarife ortalaması (`ortalama_fiyat_tl_mwh`) yoksa PTF 30 gün ortalaması (senaryo işaretli), yoksa TL yok.
Santralim künyesi: «sözleşme eşiği %98: açık 0,6 puan ≈ 14,5 MWh / 38.320 TL, fiyat: … — kıyas tabanı, alacak değil» ya da «karşılanıyor»; Santral ayarlarında
«Kullanılabilirlik sözleşme eşiği (%)» + açıklama. Dil: «garanti» sözcüğü bekçide yasak → «sözleşme eşiği».
Web: Kalibrasyon «Gerçekleşen kayıp ayrışımı» kartı (EPI, nedeni bilinen kayıp, TL; neden tablosu kaynak / saat / kWh / TL / KPI'dan dışlanır) Veri temizliği ile Hava verisi
tutarlılığı arasında. Sahte API: kayip-ayrisimi, pr kırpma alanları, kullanilabilirlik.sozlesme.
Testler: tests/test_performans_v2533.py 4 (3 günlük sentetik: talimat/kısıt/kırpma/otomatik arıza/ölçüm yok/açıklanmayan satırları, TL = kWh × 2.000, EPI; olay önceliği
talimat > arıza, açık olay pencere sonuna; PR kırpma 90 saat → kırpma dışı PR ≈ kırpmasız; sözleşme 0,98 − 0,95 = 3 puan → 3.000 kWh / 6.000 TL, fiyatsız → TL yok);
tam takım 903 geçti / 1 atlandı (5 dk 44 s); web tsc 0, 103, oxlint 16 uyarı (hepsi eski), build. Kalibrasyon ve Santralim 1440/375 taşma 0 (`kanit/kalibrasyon-kayip-ayrisimi-2026-11-04.jpg`).
Doğrulanamayan / sonraya: kırpma kaybının DC potansiyeli (DC ölçümü yok); talimat/ticari kapatma ayrımı olay kaydındaki türe bağlı (ticari kapatma türü yok);
gerçekleşen kirlenme kaybı yok; beklenen seri ölçülen havayla değil → P8b; sözleşme istisna listesi sözleşmeye göre seçilemiyor (olay türü istisnaları sabit).
