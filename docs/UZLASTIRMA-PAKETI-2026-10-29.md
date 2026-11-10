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

# Otuz dördüncü paket — v2.534 (04.11.2026, canlı): P8b-1 — yıl yıl P-değeri serisi ve gerçekleşen kıyası, yıllık bütçe ayarı

Commit `91f3223`, CI #680. Dağıtım: api + web imajı (ssh); göç yok. Canlı: index.html ve JS/CSS birebir (25/25); api «startup complete»; /p-degerleri kimliksiz 422.
Kaynak: YOL-HARITASI P8 — IH-098 (P50/P75/P90/P95/P99; biçim etiketi yıl n / ömür ortalaması / ömür toplamı; σ bileşenleri; yıl yıl seri degradasyon dâhil) ve
IH-099 (gerçekleşen / P-değerleri / bütçe kıyası). P8b'nin kalanı (ölçülen havayla beklenen seri ve hava düzeltmeli kıyas, sensör envanteri) saha sensörü akışı gelince.
Seri: `pdeger_service.yil_yil_seri` (saf) — P50_n = bankable P50 × (1 − d)^(n−1); P_q,n = P50_n × (1 − z_q σ₁) (σ₁ = bankable sigma_toplam); d = saglik_service YoY
bozunması (negatifse mutlak değeri; ±GA etikette) yoksa %0,5/yıl VARSAYILAN etiketli; ömür ortalaması σ_N = √(σ₁² − σ_ya² + σ_ya²/N) (bankable n_yil ile aynı kural);
ömür toplamı = N × ortalama. Yıl 1 = params isletmeye_giris yılı, yoksa ilk ölçüm yılı; N = bankable N_yil (10), cari yıl aşarsa uzar.
Kıyas: `gerceklesen_kiyas` (saf) — scada_hourly yıllık toplam (COALESCE(energy_kwh, power_kw), santral saat dilimi); tamamlanmış yıl kapsaması ≥ %90 ise oran_p50/oran_p90
ve konum (P50 üstü / P50–P90 arası / P90 altı), azsa «kapsam yetersiz»; cari yıl: iklim_beklenti aylık GHI P50 paylarıyla (bulunduğumuz ay gün oranıyla) yıl başından bugüne
P50/P90, pay yoksa kıyas yok; `params_json.butce_kwh_yil` varsa bütçe oranı (cari yılda aynı payla). Uç `/p-degerleri`; yanıt notu «hava düzeltmesiz …
finans raporu için bağımsız doğrulama gerekir».
Ayar: PlantAyar `butce_kwh_yil` (0 < x ≤ kurulu güç × 8760, 422); Santralim «Yıllık üretim bütçesi (MWh)» girdisi (×1000) + açıklama maddesi.
Web: Aylık beklenti sayfasında bankable kartının altında «Yıl yıl P-değerleri ve gerçekleşen»: yıl / takvim yılı / P50–P99 / gerçekleşen (cari yılda «yıl başından bugüne»,
kapsam yetersizde yüzde) / gerçekleşen÷P50 / konum rozeti («ışınım payıyla» eki) / bütçeye göre (bütçe girildiyse); ömür ortalaması ve toplamı satırları biçim notuyla;
dip not bozunma kaynağı, σ₁/σ_N, bütçe durumu, yanıt notu. Sahte API p-degerleri (yıl 1 = 2022, bozunma ölçülmüş %0,60, bütçe 24.000 MWh).
Testler: tests/test_pdeger_v2534.py 3 (seri: bozunma çarpanı, P sırası, ömür ortalaması P90 > yıl ortalaması; kıyas: 2023 kapsam yetersiz, 2024 P50 üstü, 2025 arası +
bütçe oranı, 2026 cari ytd payı, pay yok / seri dışı yıl / boş; bankable yoksa durum). Tam takım 906 geçti / 1 atlandı (6 dk 19 s); web tsc 0, 103, oxlint 16 eski uyarı, build;
Aylık beklenti 1440/375 taşma 0 (`kanit/aylik-p-degerleri-2026-11-04.jpg`).
Doğrulanamayan / sonraya: hava düzeltmeli kıyas (ölçülen ışınım yok); bozunma varsayılanı %0,5 sektör tipik (kaynak etiketli); cari yıl payı GHI'dan (üretim payı değil,
sıcaklık/kırpma mevsimselliği yok); aylık P-kıyası yok (yalnız yıl); P-değeri TL kıyası bankable gelir kartında kaldı.


# Otuz beşinci paket — v2.535 (04.11.2026, canlı): Kaynak künyesi hizalama I — dayanak sicili, 20 dosyada yayım bloğu, Hakkında mevzuat listesi, Takvim yayım ipucu, künye bekçisi; Hakkında doğrulama turu (durum rozeti, arşiv işi tazeliği, lisans doğrulama, KÜPST geçersiz kılma işareti); Takvim doğrulama turu (segment kapsamı, sonuç metinleri, kaydırma, tatil uyarısı)

Commit `e49a818`, CI #682. Dağıtım: api + web imajı (ssh); göç yok. Canlı: index.html ve JS/CSS birebir (25/25 aynı).
Kaynak: 04.11.2026 kaynak teyidi (`~/Desktop/PVQuant_Kaynak_Teyit_2026-11-04`, RAPOR.md + EK-1): doğrulama arşivinin koda işaret ettiği 581 satırın 100'ünde değer doğru,
birincil künye (RG tarih-sayı, karar no) yoktu; Hakkında mevzuat listesi künyesiz ve eksikti. Hesap değişmedi.
Sicil: `ext/turkiye/kunye.py` — 33 giriş (kısa ad → künye): DUY (RG 14.04.2009-27200 + 12 değişiklik), LÜY, Lisans Yön., YEK Yön., 5346, 6446, CK 7189/2949/3453/11415,
Ölçüm Sist. Yön., AFL U&E, Teminat U&E, Şebeke Yön., Toplayıcılık Yön., Şeffaflık Yön., Kurul kararları 13025/14029/14030/14907/14911/13869/14967/14968/13995/14982,
5905-27, OSOS U&E, 2429, BKK 2016/9154, AYM 2024/133, TPYS dokümanı, GİP kapı kapanışı; `kunye()`, `blok()`, `bul()`. Her RG sayısı arşiv envanterinin kopyası
`tests/data/kunye_envanteri.json` (140 sayı → tarih) ile eş; arşivde tarihi doğrulanmayan iki RG (32840, 33116) sicile alınmadı.
Dosya blokları: 20 dosyada `DAYANAK_KUNYELERI` literal metni (sicilden üretildi; yorum satırı anahtar listesini taşır, bekçi testi literal = `kunye.blok(anahtarlar)` eşitliğini sınar):
kurallar, takvim, dengesizlik, kgup, segment, epias (ext/turkiye); yekdem, sayac, mutabakat, dengesizlik, olay, kur, piyasa, kgup, takvim, alarm, saatlik_detay servisleri; reporting/schemas;
platform/tarife; kaynak/epias. İlk denemede blok çalışma zamanında üretiliyordu (kaynak metninde RG sayısı görünmüyordu) → literal.
Görünen künyeler: Takvim olaylarına `dayanak` listesi (`_olay`: kaynak metnindeki anılışlar → RG yayımı; web rozet ipucunda «Yayım: …»); mutabakat KÜPST kalemine `dayanak`
(DUY m.110(4), m.113(2), RG 19.10.2026-33405; DK-229); sayaç `GELIS_KAYNAK` Ölçüm Sist. Yön. RG 28.12.2023-32413 / 21.01.2026-33144 (DK-394); segment modül başlığı künyeli; Takvim günlük saatlerde teminat satırlarının dayanağı Teminat U&E m.7(3), (10)(a) (DK-131) ve GİP kapanışı dayanağı DUY m.66/A(1)(f) + EPİAŞ 28.08.2018 duyurusu (DK-114/779, «GİP Usul ve Esasları» etiketi kalktı).
Hakkında › Mevzuat ve standart dayanağı: 7 → 14 satır, «Yayım (Resmî Gazete tarih-sayı, karar)» sütunu; eklenen satırlar: dengesizlik katsayıları/fiyat sınırları kararları, YEKDEM
(5346/YEK Yön./CK 7189/2949/5905-27), Lisans Yön. ve 6446, Ölçüm Sist. Yön. ve sayaç usul-esasları, Teminat U&E, Şeffaflık veri listesi, resmî tatil/saat dilimi.
Dil: bekçi «künye» sözcüğünü yasaklıyor → ekranlarda «yayım»; kod/alan adlarında künye kaldı.
Sonuç (teyit betiği yeniden koşuldu): künyesi tam satır 148 → 291 (581 içinde); EK-1 100 → 45 kalan — kalanlar madde düzeyinde atıf (kod maddeyi başka biçimde anıyor ya da anmıyor)
ve ikincil karar numaraları (13423, 14908, 7522/7667, 10163/11326/5707, 3465; RG 31487/32282); v2.536 ifade paketiyle birlikte ele alınır.
Testler: tests/test_kunye_bekcisi.py 4 (koddaki her «RG tarih-sayı» envanterle eş — mevcut atıflarda uyumsuzluk çıkmadı; sicil ↔ envanter; dosya blokları ↔ sicil; Hakkında listesi
künyeli, takvim dayanak); etkilenen 7 modül 129 geçti; tam takım 926 geçti, 1 atlandı; web tsc 0, 103, build; Hakkında ve Takvim 1440/375 taşma 0 (`kanit/hakkinda-mevzuat-yayim-2026-11-04.jpg`).
Sahte API: Hakkında mevzuat 4 satır künyeli; sahte-takvim.json 103 olaya `dayanak`. ruff (CI dışı) ile segment.py'deki kullanılmayan numpy içe aktarımı kaldırıldı.
Hakkında doğrulama turu (04.11 brifi, aynı paket): `kurallar.dogrulama_durumu()` satır durumunu dayanak metnindeki işaretlerden türetir («bulunamadı/doğrulanmadı/taslağı» → doğrulama gerekli;
«çıkarım» → çıkarım; 2027 → belirsiz; aksi → doğrulandı) — lisanslı serbest tabloda 2023–2025 üç satır (k = l = 0,03 yalnız EPDK 4-16180 taslağı «Mevcut Metin» + EPİAŞ Wayback; Kurul kararı künyesi
bulunamadı) ve 1.11.2026 satırı (Karar 14911 V = 100 «takip eden fatura dönemi» çıkarımı, EPİAŞ duyurusu bulunamadı) «doğrulama gerekli», 1.1.2026 ve 19.10.2026 «doğrulandı», 2027 «belirsiz»;
web «Durum» sütunu + başlıkta «4 satır doğrulama gerekli» + dayanak açılır metinde (EDT/KÜPST/DSG + durum notu). Değerler değişmedi, gizlenmedi.
Arşiv kartı: «Son indirme» aslında `max(kosu_zamani)` (model başlangıcı) idi → «Son model tahmini»; `kaynak_service.is_tazeligi()` `jobs_log`'dan gece_meteo son başarılı / son deneme / durum
(kayıt yoksa None, «iş günlüğünde kayıt yok»); GEFS ayrı iş değil (aynı işin içinde). Lisans: `atif.LISANS_DOGRULAMA` — ECMWF (CC BY 4.0 + ECMWF Terms of Use; 0,25° kullanılır, 0,1° ürün
20.10.2026'dan var, kullanılmaz), DWD (yasal bildirim CC BY 4.0), NOAA (kamu malı) 04.11.2026 okundu; PVGIS/EPİAŞ okunmadı → «doğrulama kaydı yok». Resmî/senaryo: `hesapla_df.katsayilar.kupst_gecersiz_kilma`
ve `kupst_kaynak`; `dokum` notu; Doğruluk KÜPST etiketi uygulanan değer + «santral ayarı (resmî tablo …)», kural çipi «KÜPST: santral ayarı»; Hakkında DUY/KÜPST notları ve dipnotlar: k/l, V, B, AFL,
DSG eşiği ayarlardan değişmez, yalnız KÜPST n/tolerans. Sahte API GFS/PVGIS satırı (`kullanilan_kaynaklar` ile eş), `isler`, `kupst_kaynak`; sahte-kurallar.json motordan üretildi. İnceleme (04.11): kaynak açıklamalarındaki «günde 2/8 koşu» → «güncelleme» (müşteri dili; koşu iç terim).
Testler: tests/test_hakkinda_v2535.py 6 (durum türetme, tabloda durum, sahte tablo = motor, geçersiz kılma işareti + k/l sabit, lisans kayıtları, boş jobs_log → None); ilgili 8 modül 49;
Hakkında 1440/375 ve Doğruluk 1440 taşma 0 (`kanit/hakkinda-dogrulama-durumu-arsiv-isi-2026-11-04.jpg`, `kanit/dogruluk-kupst-kaynak-2026-11-04.jpg`).
Rapor: `~/Desktop/PVQuant_Kaynak_Teyit_2026-11-04/HAKKINDA_DOGRULAMA_RAPORU.md` (12 bölüm). Kanıt sınırı: canlı jobs_log/worker günlüğü bu oturumdan okunamadı; canlı tazelik mühür sonrası ekrandan.
Takvim doğrulama turu (04.11 brifi, aynı paket): el hesabıyla doğrulanan zincir — Ekim 2026 (11.11, 12.11 17:30, 14.11 Cmt, 16.11 Pzt nihai, 23.11, 24.11, 25.11, 15.01.2027),
Kasım 2026 (12.12 Cmt belirsiz, 15.12, 23.12, 24.12, 13.02.2027 Cmt), Aralık 2026 (10.01 Paz sayaç, 15.01, 22.01, 25.01, 26.01, 16.03), Nisan 2027 (15.05 Cmt → 17.05 Kurban → 20.05 Per; 28.05; 31.05),
Şubat 2027 (10–11.03 Ramazan «tatil» işaretli, kaydırma yok), Ocak 2028 artık yıl (29.02 iş günü) — hepsi motorla birebir; 2026–2027 Diyanet bayramları doğru, 2028 tanımsız →
servis `tatil_eksik_yillar` + web uyarısı. Düzeltmeler (Kaynak teyidi EK-2/EK-3 arşiv bulguları): iletime bağlı lisanssız EPİAŞ tarafı değil (UZLASTIRMA_TARAFI = lisanslı, GTS_ODEME = lisanssız;
DK-784/540; segment.KURALLAR ile eş), LÜY m.23(3) 6'sı yalnız 12.05.2019 öncesi → doğrulama (DK-690), sonuç metinleri dayanaklı (DK-575/552/557), 12'si hafta sonu EPİAŞ örnekli (DK-561),
LÜYTOB açılımı, ön YEK listesi «kesinleşir» kalktı (DK-335), YEKDEM 30 Kasım iş gününe kayar + duyuru tarihi kalktı (DK-302/279), LÜY işletim bedeli «6183» → m.36(3) (DK-671/700),
izin iptali m.30(2)(ı) ve 7 gün uyarısı yalnız bildirim tablosunda (DK-583/593), ilerleme raporu kabul yoksa doğrulama, BDB-02 «>» + şirket düzeyi (DK-580), ESY m.51(1) kapsam notları
(DK-567/736/752), bakım 48+ sa çıkarım (DK-568), 11:00 teminat m.132/E(4) kalktı (DK-131), 2027 GÖP ötelemesi notu (DK-853/854), Geçici m.39 lafzı takvim+kurallar+sahte (DK-244/260),
AYM/CK 11415 (DK-663/571), LÜY Geçici m.14 (DK-570/666), YEKA doğrulama gerekli (DK-337), DSG 2027 kararı «yasal son gün, izlenmez». Modüller arası: sayaç 12. gün, Mutabakat sürüm takvimi,
alarm takvim_son_tarih aynı `tk.donem_takvimi`/`takvim_service.ozet`'i kullanır; kgup.TAKVIM saatleri ile tek kaynak (test). Web: Yaklaşan açıklaması ve günlük saat dayanakları açılır alanda.
Testler: tests/test_takvim_v2535.py 10; test_takvim YEKA beklentisi güncellendi; takvim/kunye/alarm/sayaç/mutabakat/kurallar/dil/hakkında 78 geçti; Takvim 1440/768/375 taşma 0
(`kanit/takvim-dogrulama-turu-1440-2026-11-04.jpg`, `-375-`). Rapor: `~/Desktop/PVQuant_Kaynak_Teyit_2026-11-04/TAKVIM_DOGRULAMA_RAPORU.md` (14 bölüm). Yapılmayan: 2028 Diyanet listesi
(doğrulanmadı), lisans yenileme penceresi m.25(2) (metin teyitsiz), ölçüm itirazı 15 gün + 5 iş günü satırı, ≥100 MWe siber güvenlik/YEK-G satırları (EK-3; sonraya).
Sonraya: EK-2 ifade düzeltmeleri (v2.536); EK-3 bugün yapılabilir değer satırları (v2.537); kalan 45 künye satırı madde atıflarıyla birlikte; Mutabakat ekranında kupst_kaynak görünürlüğü.

# Otuz altıncı paket — v2.536 (04.11.2026, canlı): İklim beklentisi düzeltmesi, PVGIS-ERA5 yedeği, açılış yakalamasında cron slotu, bağımlılık üst sınırları

Commit `6ee1d1f`, CI #684. Dağıtım: api + worker + web imajı (ssh, 03:45–06:30 TSİ dışında); göç yok. Canlı: index.html ve JS/CSS birebir (25/25 aynı).
Kaynak: 04.11 canlı olay zinciri. v2.532 dağıtımı (05:03 TSİ) worker'ı gece_meteo (04:00) ortasında ve sabah_tahmin (05:00) başlarken yeniden yarattı; eski
konteyner düzgünce durdu (OOM değil), iş günlüğünde iz kalmadı; yeni worker'ın açılış yakalaması 30 saat ölçütüyle 3 Kasım koşularını «taze» saydı. Hakkında'daki yeni
indirme işi satırı (v2.535) bunu görünür kıldı. Telafi: sunucuda bağımsız tam tur (`nohup docker compose run --rm -T worker python -m apps.worker.main --once`,
09:38–12:50 TSİ; ICON/GEFS 4 Kasım 00Z arşivlendi, sabah tahmini ve alarm koştu). Turun günlüğü ikinci kusuru açığa çıkardı: iklim_yakalama 5 santralin 5'inde düştü —
4'ü «cannot insert time, already exists» (PVGIS indeksi «time» adlı; pandas 3'te yıl/ay anahtarları aynı adı taşıyınca reset_index düşer; yerelde 0.15.2/3.0.3 ve imajda
0.16.1/3.1.0 yeniden üretildi), 1'i PVGIS-SARAH3 kapsam dışı (Colorado; PVGIS «PVGIS-ERA5» öneriyor). Canlıda hiçbir santralin iklim beklentisi yoktu.
Düzeltmeler: `iklim_service.aylik_toplamlar` anahtar adları açık; `arsiv_isinim._pvgis_cek` kapsam hatasında ERA5 (attrs kaynak/etiket, başka hata yükselir);
`isler_service.kacan_isler` (saf) + `kacan_isler_db`: bugünkü cron slotu geçmiş ve o slottan sonra başarılı koşu yoksa kaçmış (5 dk pay); worker `acilis_yakalama`
30 saat + slot ölçütü (gece_meteo, sabah_tahmin, gece_skill, gunluk_beklenti); pyproject pandas <3.2, pvlib <0.17.
Testler: tests/test_v2536_iklim_yakalama.py 5; tam takım .venv 929 geçti / 1 atlandı (yakalama testi slot ölçütüne uyarlandı); imaj sürümleriyle (.venv-imaj pvlib 0.16.1 / pandas 3.1.0) 929 geçti / 1 atlandı. Web değişmedi.
Canlı doğrulama: dağıtım sonrası 5 santral için tek seferlik iklim hesabı (5/5 santralde 12 aylık beklenti yazıldı, Colorado ERA5 yedeğiyle (19:25 TSİ)); Hakkında arşiv kartı ve Aylık beklenti iklim katmanı.
Dersler: worker 03:45–06:30 TSİ arasında yeniden yaratılmaz; bağımlılık sürüklenmesi (imaj pip'ten en yenisini alır) → üst sınır + imaj sürümleriyle ayrı venv'de tam takım.
Sonraya: EK-2 ifade düzeltmeleri (v2.537), EK-3 değer satırları, lock dosyası (uv/pip-tools) kararı, Mutabakat'ta kupst_kaynak.

# Otuz yedinci paket — v2.537 (04.11.2026, canlı): EK-2 ifade düzeltmeleri (26 dosya) + Sayaç sayfası doğrulama ve müşteri dili turu (hesap aynı)

Commit `036faef`, CI #686. Dağıtım: api + worker + web imajı (ssh); göç yok. Canlı: index.html ve JS/CSS birebir (25/25 aynı).
Kaynak: 04.11 kaynak teyidi `EK2_etiket_ifade.md` (arşiv etki türü «etiket-ifade», kanıt A/B; takvim satırları v2.535'te kapanmıştı). Hiçbir hesap, katsayı, tarih değişmedi;
yalnız açıklama, etiket ve docstring'ler. Görünen metinlerde düzeltilenler: YEKDEM m.23(6) notunda yanlış künye «RG 19.10.2026-8» → 33405 (Doğruluk sayfası); sayaç kaynak etiketleri
OSOS/MASS «bilgi amaçlı, uzlaştırmaya esas UEVM değil» + MASS açılımı (Millî Akıllı Sayaç Sistemi); «diğer sayaç (aylık bildirim, saatlik değer)»; sayaç düzeltme yolu DUY m.82(3)/(4);
m.8(3)–m.81(1) eşitlemesi «yorum» (kesinlik belirsiz); kural tablosu dayanaklarında GTŞ (m.69(11)+m.110(3)) / toplayıcı (m.110(6)(b)(3)) ayrımı, m.132/Ç(18) yansıtma, 19.10.2026 öncesi
münferit birim, %5 payın yorum olduğu; segment «dengesizlik_sahibi» etiketleri («santral EDT/KÜPST taşımaz; talimat tutarları ve LÜY Ek m.4 tahsilatı yansıtılabilir»; YEKDEM portföy
dengesizliği 01.05.2016'dan mülga); DSG notu «aşan kısım DST'ye yansıtılır, üyeye aktarımı sözleşmesel»; 2027 varsayımının hukuki dayanağı olmadığı; senaryo «dengede» notu; olay kaydı
açıklamaları (25 ürün ön uyarısı, sayaç EPİAŞ sayımına vekil, şebeke kesintisi/hasar çıkarım, mücbir sebep Lisans Yön. m.35); Excel «CO₂ TASARRUFU» → «KAÇINILAN CO₂ (şebeke karması, varsayım)»;
Hakkında geçici m.40 notu; mutabakat GDDK/RBS/m.132/A(4). Docstring/yorumlar: SMF_N = SMF_P çıkarım, BUDÜP = KGÜP varsayımı, KÜPST paydası KÜPSM, DSG docstring güncel davranış,
m.110(6) → m.110(3)-(4), DUY m.20(4), YEKA 5346 m.4(2), lisanssız dağıtım «sahip bildirmez, GTŞ/toplayıcı UEVÇB'si», öz tüketim LÜY m.4(1)(ö)/m.26(5), saat değişimi yok (yaz saati
yıl boyu), m.22(4)(c)+depolama, EAK m.69/A(1) (m.4(1) kalktı), KGÜP ≤ EAK ürün kuralı, kurulu güç DC/AC bulunamadı, gece EAK iletime bağlı lisanssız, TPYS duyuru atıfları, m.69/A(2),
PBD, BELIRSIZ_2027_GEREKCE (Md.13 tek EDT_f, ilişki belirsiz, üç ay çıkarım, kanıt kesimi), depolamalı YEKDEM kapsam notu, SMF aritmetik ortalama + kaynak, NASA POWER/Open-Meteo,
DSG grup payı «olası neden», nowcast τ=2 saat, alarm 24 sa ürün parametresi, mcp = nihai PTF, Şeffaflık üretimi UEVM değil, kısıt tazmin hükmü yok, KDV notu, çok zamanlı tarife kaynağı,
CAMS/NASA gecikme etiketi. Uygulanmayan EK-2 satırları (sonraya; kod/veri gerektirir): DK-241/252 PH katılımcı bazı, DK-186 KGÜP eksik saat duyarlılığı, DK-850 15 dk yaklaşık etiketi,
DK-267 UEVÇB gruplaması, DK-695 portföy üyeliği beyanı, DK-397/389 sayaç ayar notu ve OSF matris ayrıştırıcı, DK-200 depolamalı segment, DK-614/627 dâhilî bilgi geri sayımı,
DK-317 YEKDEM gelir notu, DK-367 rapor kaynak etiketi, DK-478 SMF «bekleniyor», DK-792 GİP ücreti, DK-888 kış dilimleri, DK-008/150/889 belge tarafı.
İnceleme (kullanıcı, Sayaç ekranı): «Sayaç türü» ve «Bağlantı durumu» açılır listelerinde her seçenek «SCADA ölçümü» görünüyordu — v2.526'da üretim seçiminden kopyalanan yanlış üçlü;
v2.537'de her seçenek kendi etiketini gösterir (kayıt değeri doğruydu, canlıda 2 gündür yanlış etiket). Testler: ilgili 14 modül 96 geçti; test_sayac diğer sayaç beklentisi «belirsiz»; sahte-kurallar.json motordan yeniden üretildi; tam takım 934 passed, 1 skipped, 155 warnings in 329.27s (0:05:29); web tsc 0, 103, build;
Sayaç/Doğruluk/Hakkında 1440 taşma 0.
Sayaç sayfası turu (04.11 brifi): kod/veri denetimi — her kart değeri servis alanına bağlandı (gelis.siniflama, fark.olculmus/tahmini_dahil/kapsam, donemler[].kapsam); sayısal
kimlikler: SCADA 456 = 19 gün × 24, sayaç/ortak 450 (10 Ekim 18 saat), ölçülmüş 441 = 450 − 9 tahmini, ikisi de yok 264 = 720 − 456, kapsam %63 = 450/720, vadesi gelen 90 = 92 geçen − 2,
düzeltme 12 Kas 17:30 = Takvim `donem_takvimi` (DUY m.132/B(1), m.82(4)) — sahte veride yalnız Ekim kapsamı 528 tutarsızdı (1–22 Ekim ama 10 Ekim 18 saat) → 522/222; servis hesabı DB'den
tek kaynaklı, tutarsızlık üretmez. Formül doğrulaması (tests/test_sayac_v2537.py 4): fark yüzdesi paydası ortak SCADA (günlük toplam değil), tahmini/doldurulmuş/elle/veri-yok saatler
ölçülmüş kıyasa girmez, SCADA 0'da yüzde yok, çok günlü pencerede ortak/yalnız SCADA/yalnız sayaç toplamları tamamlayıcı. İçe alma: ayraç/kodlama/XLSX, ayrı tarih-saat, 15 dk → saat
(dilim başı), MWh çarpanı, yinelenen dilimde son satır, gelecek/negatif/okunamayan satır sayımı, endeks sütunu reddi, 8 MB sınırı, (plant, saat, kaynak) üzerine güncelleme — silme yok
(mevcut testler). Mevzuat: m.8(2)/(3), m.81(1), m.82(3)-(4); 12. gün Takvim motoruyla tek kaynak; «eksik» = PVQuant'a yüklenmemiş, EPİAŞ eksikliği iddia edilmez. Dil: kart adları,
eyleme dönük alt metinler, «Bu sayfa nasıl çalışır» beş soru + teknik ayrıntı açılır alanı; «Sayaç türü»/«Bağlantı durumu» seçenek etiketleri (v2.526 kopya hatası) düzeltildi. İkinci inceleme: yükleme aralığı gün biçimleyicisi saatli damganın UTC gününü kesiyordu («30 Eyl» = 1 Ekim 00:00 TSİ) → yerel gün; sahte veride Eylül kapsamı 0/720 ve ilk yükleme 354 saat hizalandı.
Yapılmayan: resmî OSOS/MASS/EPYS sütun şablonları elimizde yok (dosya ipuçlarıyla tanınır, belgeli); yükleme geri bildirimi zaten alınan/atlanan sayımları veriyor, ayrı tablo yapılmadı;
raporlarda ölçüm kaynağı etiketi (DK-367) sonraya. Rapor: `~/Desktop/PVQuant_Kaynak_Teyit_2026-11-04/SAYAC_DOGRULAMA_RAPORU.md`.
Sonraya: EK-3 değer satırları; lock dosyası kararı; Mutabakat'ta kupst_kaynak.

# Otuz sekizinci paket — v2.538 (05.11.2026) — EK-3 kanıtlı satırlar I

**Kapsam.** 03.11.2026 doğrulama arşivinin EK-3 değer/yükümlülük tablosu (63 satır) tarandı; birincil metni arşivde okunmuş, A kanıtlı, veri ya da göç gerektirmeyen 16 satır uygulandı. Kural: C/D/E kanıtlı satır birincil metin okunmadan uygulanmaz.

**Uygulanan satırlar.**
| DK | Konu | Uygulama |
|---|---|---|
| DK-613 | Dâhilî bilgi 1 saat kuralı yürürlüğü | «belirsiz» → 01.01.2027 (Yön. RG 14.02.2026-33168 m.16, RG 23.05.2026-33262 ile; Karar 14967'de ayrı yürürlük yok → çıkarım). 2027 öncesi olayda `basladi=False`, hatırlatma bilgi amaçlı. |
| DK-733/740 | Talimat tutarı yansıtması | Olay kaydı açıklaması segmente göre: lisanssızda DUY m.75(3) zinciri + LÜY Ek m.4(1) + m.107(3); lisanslıda DGP uzlaştırması. |
| DK-656/658 | SCADA (ç) askı kapsamı ve sayım | LÜY Geçici m.14(2) metni: askı yalnız (f),(g); 30.4.2027 teyit. (ç) askıda değil; sayım dağıtım şirketi uyarı tarihinden (yeni ayar) + 1 takvim ayı (yorum). Uyarı tarihi yoksa (ç) üretilmez. |
| DK-735 | 900 kW kıyası | AC sınırı yoksa DC kWp ile kıyas → «belirsiz» işareti ve uyarı. |
| DK-557/395 | İtiraz süreleri | Mutabakat `itiraz_takvimi()`: m.132/B(1), m.133(1), m.133(5) 12 ay + 3 ay (son başvuru çıkarım), m.133(3)–(4) inceleme süreleri, LÜY m.27 lisanssız. |
| DK-297/323/675 | YEKDEM kapsam sınırları | `KAPSAM_SINIRLARI`: y katsayısı (m.12(3)–(4)), kurulu güç aşımı (m.12), depolama (LÜY Ek m.3(2)); Doğruluk › YEKDEM kartında açılır liste. |
| DK-653/785 | İletime bağlı lisanssız EDT | `dengesizlik_tasir_mi` False (tabloyla tutarlı); EDT yansıtma hükmü bulunamadı, talimat tutarı m.75(3). |
| DK-662/668/696 | Öz tüketim kapsam sınırı | m.26(17) iki kat sınırı, m.26(20) mesken istisnası modellenmedi; gelir() bağlı değil — docstring ve segment notu. |
| DK-023 | İkinci EPİAŞ istemcisi k=l=0,03 | Eski formül künyesi (RG 02.02.2020-31027; ≤31.12.2025); 2026+ seride ValueError. |
| DK-134 | Kısıt listesi | Döküm notuna DUY m.71(3): kısıt/T−30 saatlerinde KGÜP kesinleşir, PVQuant işaretlemez. |

**Uygulanmayan (04'e).** DK-612 (YEK-G Ek sıra 17–18: Karar 14967 OCR metni boş, birincil okuma yok), DK-629 (PBD Yön. m.7/6 toplayıcı alıcısı — metin okunmadı), DK-333 (m.23(9) 1.1–18.10.2026 tatil işareti — mülga tarihi arşivde çelişkili: 33122 / 33405), DK-1019 (CO₂ 0,44 → kaynaklı değer, kanıt B), DK-258/252/261 (DSG gruplaması `dsg` alanına göre — hesap değişikliği, ayrı paket), DK-056 (YAL/YAT saatlerinde «hesap güvenilmez» işareti), DK-741/743 (acil kesme sona erme bildirimi, gerekçe son günü — yeni alan/göç), DK-206, DK-804.

**İnceleme (05.11).** Sahte API süreci yamadan önce başlamıştı (eski veri); yeniden başlatıldı. SCADA kartında (ç) notu iki kez görünüyordu, sol satır yalnız uyarı tarihi girilince kalır. Mutabakat «Ne yapmalı» itiraz tarihleri gün.ay.yıl yapıldı.

**Kanıt.** pytest tam takım; `tests/test_ek3_v2538.py` 11 test; web tsc/npm test 103/oxlint 16/build; sahte API kareleri (4 sayfa, taşma yok). Göç yok. Formül değişikliği yok.

**Mühür.** 79d9108 (05.11 02:4x TSİ), CI #688 yeşil; ssh dağıtım api+worker+web 02:56–02:58 TSİ (worker penceresi dışında); canlı 25/25 birebir; göç yok. Raporlar: 02 M52, 00 otuz sekizinci paket, 04 E satırı; kanıt `kanit/ek3-*-2026-11-05.jpg`.

# Otuz dokuzuncu paket — v2.539 (05.11.2026) — EK-3 kanıtlı satırlar II: DSG gruplaması, toplayıcı dışlama, talimat saatleri

**Kapsam.** DK-258 (DSG gruplaması santral kaydındaki `dsg_kodu`na göre; kodsuz = tek grup varsayımı etiketli), DK-261 (`toplayici_portfoyu` → DSG dışı, DUY m.20(4)), DK-653/785 devamı (iletime bağlı lisanssız portföy dışı), DK-252 (katılımcı düzeyi eşik — not), DK-056 (YAL/YAT/acil kesme saatleri dökümde `talimat` sütunu; hesap değişmez).

**Yüzeyler.** Portföy › DSG kartı: grup seçici (birden çok beyan varsa), «Hesap dışı santraller (n)» nedenli liste, varsayım notu; Santralim › Santral ayarları: DSG kartı; Doğruluk › Saatlik döküm: talimat rozeti ve sayım; CSV/XLSX `talimat` sütunu. API: PUT /segment `dsg_kodu`, `toplayici_portfoyu`; GET /portfoy/dsg[.csv] `grup`.

**Yapılmayan.** Katılımcı düzeyinde PH/eşik toplama (DK-252: katılımcı alanı yok; not); talimat miktarının veri olarak alınması (BUDÜP düzeltmesi, DK-056'nın ikinci yarısı); DK-612/629/333/1019 (birincil metin), DK-741/743 (göç).

**İnceleme (05.11).** Katılımcı notundaki araştırma numarası kaldırıldı; varsayım cümlesi sadeleşti.

**Kanıt.** tests/test_ek3_v2539.py 4; tam takım; web kapıları; kareler.

**Mühür.** 3ad3aa6 (05.11 03:40 TSİ), CI #690 yeşil; ssh dağıtım api+web 03:52–03:53 TSİ (worker yeniden yaratılmadı: 03:45–06:30 gece işleri penceresi; worker tarafındaki servis değişikliği yalnız DSG gruplaması ve döküm notu, gece işlerini etkilemez — 06:30 sonrası `docker compose build worker && up -d worker`); canlı 25/25 birebir; göç yok. Raporlar: 02 M53, 00 otuz dokuzuncu paket, 04 E satırı; kanıt `kanit/ek3b-*-2026-11-05.jpg`.

# Kırkıncı paket — v2.540 (05.11.2026) — EK-3 birincil metin okumaları: YEK-G sıra 17, m.23(9), ETKB CO₂

**Okunan metinler.** Karar 14967 (RG 20.10.2026-33406, görüntüden): sıra 17 YEK-G eşiksiz arıza/plansız bakım; fıkra 3(a)/(b), 4(a); yürürlük fıkrası yok. YEK Yön. değişiklikleri: RG 29.12.2025-33122 Md.7–8 ((9) eklendi, 1.1.2026) ve RG 19.10.2026-33405 Md.5/7 ((9) kaldırıldı, 19.10.2026). ETKB EVÇED emisyon faktörleri bilgi formu (2022; yayım 06.12.2024): üretim 0,438 tCO₂/MWh.

**Uygulama.** `yek_g_kayitli` beyanı + Olay kaydında eşik altı arıza hatırlatması (3(b) şartı etiketli); `m23_9` işareti ve döküm sütunları, YEKDEM kartı özeti (yarım günler ve KGÜP'süz tatil saatleri yorum); Excel CO₂ 0,438 ve kaynak etiketi. Dil bekçisi iki sözcük yakaladı («Koşu», «Garanti») → düzeltildi.

**Kanıt.** tests/test_ek3_v2540.py 4; tam takım; web kapıları; kareler. Göç yok. Arşiv: EK3 satırları DOĞRULANDI/A, `EK3_BIRINCIL_OKUMALAR_2026-11-05.md`.

**Mühür.** 334310d (05.11 04:3x TSİ), CI #692 yeşil; ssh dağıtım api+web 04:44–04:45 TSİ (worker yeniden yaratılmadı: 03:45–06:30 penceresi; worker tarafındaki değişiklik yalnız olay/yekdem notları ve DAHILI_NOTU — gece işlerini etkilemez; 06:30 sonrası `docker compose build worker && up -d worker`); canlı 25/25 birebir; göç yok. Raporlar: 02 M54, 00 kırkıncı paket, 04 E satırı; kanıt `kanit/ek3c-*-2026-11-05.jpg`.

# Kırk birinci paket — v2.541 (05.11.2026) — EK-3 kalanı: olay kaydı alanları (göç v2541_olay), DSG katılımcı toplamı, BUDÜP bilgi sütunları, YEÜM göstergesi, topluluk notu

**Kapsam.** DK-741 (LÜY m.21(8): şebeke işletmecisi acil durumun sona ermesinden itibaren 15 dk içinde bildirir) → `bildirim_zamani` + gecikme/15 dk aşımı; DK-743 (DUY m.71/A(1): talimata uyulamazsa gerekçe olayı takip eden 3 iş günü içinde yazılı) → türetilmiş `gerekce_son_gunu`; DK-056 kayıt → `talimat_mw` (hesaba girmez).

**Yüzeyler.** Olay kaydı formu (acil kesmede bildirim saati; YAL/YAT'ta talimat MW), listede «Bildirim geldi» düğmesi ve açıklama ekleri, CSV 4 sütun, açıklama paragrafı. API: OlayIstek/OlayGuncelle. Göç: `alembic/versions/v2541_olay.py` (revises v2527_saatlik_detay).

**Ek satırlar.** DK-252 `piyasa_katilimcisi` ile DSG'de katılımcı toplamı; DK-056 ikinci yarı dökümde `budup_mwh`/`sapma_talimatli_mwh` (bilgi); DK-804 Karar 14626 YEÜM göstergesi (`lisans_yillik_uretim_mwh`; yalnız negatif dengesizlik kalemi, alt sınır); DK-206 topluluk ağırlıklı tolerans notu. EK-3'te açık satır kalmadı.

**EK-2 kod satırları.** DK-659 `cagri_mektubu_tarihi` + Takvim LÜY rejimi rozeti (m.25/m.26; ölçüt çağrı mektubu); DK-367 aylık raporda üretim ve katsayı kaynağı; Mutabakat'ta KÜPST katsayı kaynağı; `requirements-lock.txt` anlık görüntüsü (Dockerfile kullanmaz). Kapanan: DK-019 (dış API'de alan yok), DK-188/618/840/480 (önceki sürümler). DK-267 `gts_toplayici_adi` ile UEVÇB kodsuz santraller ada göre birimlenir. Diyanet 2028 dinî bayramları resmî listeden eklendi (2027 teyit).

**Yapılmayan.** Talimat miktarının EDT/KÜPST toplamlarına işlenmesi (KUDÜP ilişkisi doğrulanmadı; bilgi sütunu); m.71(2) EAK değişikliği gerekçe bildirimi (metin okunmadı).

**İnceleme (05.11).** Dokuz ekran; tür notundaki «P2b» iç kodu kaldırıldı, sahte tür notları motorla eşitlendi, boş açıklamalı satırda ayraç düzeni.

**Kanıt.** tests/test_ek3_v2541.py 2; tam takım; web kapıları; kare.

**Mühür.** 58f2698 (05.11 06:54 TSİ) + rötuş e0f2c52 (07:04), CI #694 web kırmızı (`tsc -b`: YEÜM tipinde `pencere_gun` eksik; yerel kapı `tsc --noEmit` değil `npm run build`) → CI #695 yeşil; ssh dağıtım api+web 07:12 TSİ, göç `v2541_olay` DB sahibiyle (head v2541_olay; olay.bildirim_zamani / talimat_mw + CHECK doğrulandı); worker yeniden yaratılmadı: 06:4x TSİ açılış yakalaması «slotu kaçan: gece_meteo» ile tam tur başlattı, tur sürerken yaratma turu keser (04.11 v2.532 olayı) — jobs_log’da bu turun `alarm` satırı düşünce `docker compose up -d worker` (imaj kurulu); canlı 25/25 birebir; healthz ok. Raporlar: 02 M55, 00 kırk birinci paket, 04 E satırı; kanıt `kanit/ek3d-*-2026-11-05.jpg`.

## Kırk ikinci paket — v2.542 (05.11.2026): P8b-2 ölçülen havayla beklenen üretim, EPI ve sensör envanteri

**Kaynak.** YOL-HARITASI P8 (dalga 3) kalanı: IH-083 beklenen üretim serisi (ölçülen hava) ve üç referans + EPI; IH-092 sensör envanteri, kalibrasyon tarihi, ışınım kaynağı etiketi, IEC 61724-1:2021 sınıfı; IH-099 hava düzeltmeli P50 kıyası; IH-104 ölçülen ışınım / P50 ışınım kıyası (sigorta koşulu). 04 E tablosu «kalan P8b-2: ölçülen havayla beklenen seri ve hava düzeltmeli kıyas (sensör akışı gerek), sensör envanteri». Sensör akışı: `scada_hourly` zaten `poa_wm2`, `t_module`, `t_air`, `wind_ms` taşıyor (PR kartı v2.249'dan beri ölçülen POA'dan); eksik olan hesap ve beyan katmanıydı.

**Beklenen seri (saf, `performans_service`).** Saatlik beklenen kWh = P0 × (POA/1000) × PR_ref × (1 + γ·(T_c − 25)); EAK girildiyse üstten kesilir. T_c kaynağı sırayla: modül sıcaklık sensörü (≥%90 kapsam) → hava sıcaklığı + rüzgârdan Faiman (IEC 61853-2; rüzgâr yoksa 1 m/s varsayımı, etiketli) → sıcaklık terimi yok (etiketli). PR_ref: Santral ayarlarına girilen tasarım/sözleşme PR'ı (0,5–0,95) varsa o; yoksa santralın son 365 gün ölçülen PR'ı (sıcaklık düzeltmeli > kırpma dışı > ham) — bu durumda EPI «kendi geçmişine göre» okunur, etiket bunu söyler. Tire ilkesi ay bazında: POA kapsamı gündüz saatlerinin %95'inden azsa o ayın beklentisi ve EPI'si yazılmaz (GHI ile uydurulmaz; pr_service eşiğiyle aynı). Ay satırı: gerçekleşen, beklenen, EPI, EPI (kırpma ve kısıntı saatleri dışı), kırpma/kısıntı saati, ölçülen ışınım kWh/m², POA kapsamı. Üç referans tek tabloda: tahminle beklenen (fizik modeli 0–24 saat, `forecast_values.physics_kw`, yalnız ölçümün olduğu saatler), ölçülen havayla beklenen (bu paket), P50 aylık (bankable P50 × iklim GHI payı). Model çekirdeğine girmez; tasarım simülasyonu değildir, not bunu söyler.

**Işınım endeksi (IH-104/IH-099).** Ölçülen aylık ışınım toplamı / iklim P50 yatay ışınımı; yalnız yatay (GHI) ölçen sensör beyan edildiyse. Düzlem-içi ölçümde aylık toplamlar üzerinden düzlem dönüşümü YAPILMAZ: `duzlem_uyumsuz` durumu ve dürüst not («ışınım endeksi ve hava düzeltmeli P50 bu santral için verilmez»). Endeks varsa P50 aylık × endeks = hava düzeltmeli P50. Sensör beyanı yoksa `sensor_yok`, iklim yoksa `iklim_yok`.

**Sensör envanteri (IH-092).** `params_json.sensorler` listesi: tür (piranometre / referans hücre / uydu türevli / modül sıcaklık / meteoroloji istasyonu), ölçüm (poa / ghi / t_module / t_air / wind; tür–ölçüm uyumu doğrulanır), marka/model, seri no, IEC 61724-1:2021 sınıfı A/B (2017 baskısındaki C kaldırıldı), kalibrasyon tarihi ve periyodu (varsayılan 24 ay — standart metninden doğrulanmadı, beyan etiketli). Vade türetilir, saklanmaz: geçti / yaklaşıyor (≤60 gün) / uygun / tarih yok. `isinim_kaynagi()`: düzlem-içi sensör varsa o esas (IEC PR düzlem-içi ister), yoksa yatay; PR kartına «Işınım ölçümü kaynağı» satırı (etiket, sınıf, kalibrasyon durumu, vade). Alarm kuralı `sensor_kalibrasyon` («Sensör kalibrasyonu vadesi geçti», uyarı; veri KPI'ya girmeye devam eder) — alarm_service EK_KURALLAR/KURAL_ETIKET + web alarmSozluk + Santralim kural grubu «Veri ve model». Denetim eylemi `sensor_ayar`.

**API.** GET `/plants/{id}/performans?ay=1–36`; GET/PUT `/plants/{id}/sensorler` (en çok 20; doğrulama 422; PUT bütünüyle değiştirir); PUT `/eak` `pr_referans` (0,5–0,95). **Web.** Aylık beklenti › «Beklenen üretim (ölçülen hava) ve EPI» kartı (P-değerleri kartının altında; endeks sütunları yalnız `isinim.durum == ok`); Santralim › Santral ayarları «Referans performans oranı (%)» alanı; Santralim › «Sensörler ve kalibrasyon» kartı (tam genişlik; tablo + ekle/kaldır formu); Santral bilgileri kartına «Işınım ölçümü kaynağı» satırı; alarm kural açıklaması. Sahte API: `performans`, `sensorler` (GET/PUT, vade türetimi), 12 ay + cari ay örneği p-degerleri ile tutarlı (son 12 ay 19.455 MWh, P50 24.300).

**Kalanlar (aynı paket, 05.11 «diğer kalanları da yapalım»).** (1) İklim düzlem-içi beklentisi: aylık iklim işi aynı saatlik SARAH-3 arşivini pvlib ile santralın eğim/azimutuna dönüştürür (`iklim_service.poa_serisi`: Hay-Davies, albedo 0,2, güneş konumu saat ortası; dhi/dni yoksa Erbs ayrışımı), `iklim_beklenti` tablosuna POA P10/P50/P90 + eğim/azimut (göç `v2542_iklim_poa`); worker `aylik_iklim` eğim/azimut geçirir. Düzlem-içi sensörde ışınım endeksi artık aynı düzlemde; POA beklentisi henüz yoksa `poa_p50_yok` (yatayla kıyas yine yapılmaz). Canlıda ilk dolum: aylık iklim işi (ayın 1'i) ya da tek seferlik koşu; eğim/azimut girilmemiş santralda sütunlar boş. (2) Takvim: sensör kalibrasyon vadeleri Uyum takvimi satırı (`takvim_service._sensor_satirlari`, servis katmanında; kod `sensor_kalibrasyon` UYUM_KODLAR'da; kaynak türü «santral tarihi»; 12 ay ileri, geçmiş vade alarm/Sensörler kartında). (3) Aylık/dönem raporu: «Beklenen üretim (ölçülen hava) ve EPI» tablosu + not bölümü ve özet satırında EPI (`performans_service.donem(bas, bit)` kapalı dönem; `donem_cozumle` bit hariç → bit−1 gün); JSON `performans` anahtarı.

**Göç.** `v2542_iklim_poa` — iklim_beklenti'ye poa_p10/p50/p90_kwh_m2, poa_egim, poa_azimut (DB sahibiyle).

**Yapılmayan / sonraya.** Sensör kirliliği göstergesi (saha–uydu sürekli sapması, uydu akışı yok); sigorta poliçe şartları (muafiyet, bekleme süresi) PVQuant'ta yok; IEC 61724-1:2021 kalibrasyon periyodu metni doğrulanmadı.

**İnceleme (05.11, beş ekran).** (1) Alarm kuralları listesinde yeni kural görünmüyordu: sahte API'nin seçilebilir listesi eksikti (canlıda liste alarm_service.EK_KURALLAR'dan gelir) — sahte eşitlendi; (2) «Üretim programı sınırları» ayrıntısında referans PR maddesi yoktu — eklendi; (3) beklenen üretimin kesim kaynağı yalnız EAK alanıydı, sahte 12,5 MW ile santralın 12 MW AC sınırı çelişiyordu — kesim kgup_service.eak_etkin önceliğiyle (geçici kısıt > EAK alanı > AC sınırı; yalnız kurulu güç kalıyorsa kesim yok) ve kaynak etiketli («12,00 MW AC sınırı ile üstten kesildi»); EPI orta bandı (%85–95) nötr rozet. İkinci tur (kalanlar, dört ekran): Uyum takvimi açıklamasında «santral tarihlerinden türeyenler» listesine sensör kalibrasyon vadesi; Dönem raporu kartının içerik cümlesine ölçülen havayla beklenen üretim ve EPI. Aylık kartı endeks sütunları ve Raporlar alt kartları uygun.

**Kanıt.** tests/test_performans_v2542.py 13 (iklim POA beklentisi güneye eğik kışın yataydan yüksek, takvim sensör satırı, rapor bölümü; beklenen/EPI modül–Faiman–sıcaklıksız, EAK kesimi, POA'sız ay tire, kırpma/kısıntı dışı EPI, referans sırası, endeks düzlem kuralı, sensör doğrulama/vade/kaynak, API kapıları); tam takım 963 geçti / 1 atlandı (rapor tutarlılık alt süreci yük altında −11, tek başına 77/77; bantsız rapor 9 ayrı); web build + lint + 103; sahte önizleme 1440/375 taşma 0 (`kanit/p8b2-*-2026-11-05.jpg`); «Ekle» akışı sahte PUT ile.

**Mühür.** eb6774c (05.11 08:26 TSİ), CI #697 yeşil; ssh dağıtım api+web 08:38 TSİ, göç `v2542_iklim_poa` DB sahibiyle (head v2542_iklim_poa; iklim_beklenti poa_p10/p50/p90_kwh_m2 + poa_egim/poa_azimut doğrulandı); worker yeniden yaratılmadı: 06:4x açılış yakalaması turu sürerken yaratma turu keser, sınıflandırıcı da bu yüzden reddetti — v2.541+v2.542 imajı kurulu, jobs_log’da `gece_meteo` ve `acilis_yakalama` satırları düşünce `docker compose up -d worker`; canlı 25/25 birebir; healthz ok. Raporlar: 02 M56, 00 kırk ikinci paket, 04 E satırı; kanıt `kanit/p8b2-*-2026-11-05.jpg`.

## Kırk üçüncü paket — v2.543 (05.11.2026): P9 depolama ve hibrit hazırlığı (küçük kapsam)

**Kaynak.** YOL-HARITASI P9 (dalga 3, koşullu): IH-112 emre amadelik %85/%80, IH-111 hibrit akış ayrımı, IH-113 depolama gücü ve 30 MW eşiği, IH-109 15 dk hazırlığı, IH-114 kapasite mekanizması (2027 listesinde GES yok). Karar: bugünkü müşterilerde depolama yok → yalnız kayıt alanları ve kural parametreleri (hazırlık); oran hesabı, hibrit akış ayrımı ve uzlaştırma dışı veriş hesabı ilk depolamalı müşteriyle. Bulgular: `bulgular/08-yakin-gelecek.md` 08-03, 08-04, 08-06, 08-07, 08-08, 08-22 (31.10.2026 bağımsız teyit).

**Motor (`ext/turkiye/depolama.py`, saf).** `dogrula()` beyan doğrulama (güç 0–2000 MW, kapasite ≤20.000 MWh, konfigürasyon EK-1a/1b/1c/1ç/EK-2, depolama UEVÇB ≤32, kabul tarihi ISO, bütünleşik; güç yok → alanlar silinir); `dengeleme_birimi(guc)` DUY m.22(2)(ç) 30 MW ve üzeri depolama ünitesi → ilişkili UEVÇB dengeleme birimi, m.22(4)(i) altı muaf, m.22(4)(c) güneş talep/onayla (RG 29.12.2025-33122; ibare 19.10.2026-33405) — kesinlik doğrulandı; `emre_amadelik(kabul, bugun)` DUY m.81/A(2)(b) kabulden itibaren ilk 5 yıl %85 sonra %80 (29 Şubat güvenli yıl ekleme), (3) koşul sağlanmayan dönemde tüm veriş uzlaştırma dışı (YEKDEM'e bedelsiz katkı), (4) veriş sıfırsa uygulanmaz, tespit fatura dönemi bazında — eşik doğrulandı, ÖLÇÜM YÖNTEMİ BELİRSİZ (bulunamadı 31.10.2026; PVQuant oran hesaplamaz); `SMF_COZUNURLUK` saatlik, 15 dk geçişi hukuken 1.1.2027 (Geçici m.40), fiilî ilan bulunamadı → belirsiz; `YEKDEM_NOTU` 7189 Ek-1 (e) 125,00 kr/kWh + yerli katkı 38,45 10 yıl yalnız depolandıktan sonra verilen enerjiye (dipnot ***); `UEVCB_NOTU` DUY m.21(8) ayrı UEVÇB; `DAYANAK_KUNYELERI` sicilden (DUY, DEPOLAMA_YON, CK7189, LISANS) + `DAYANAKLAR` madde bazında 7 satır. Künye sicili `DEPOLAMA_YON` (RG 09.05.2021-31479; 29.12.2025-33122; 19.10.2026-33405); Hakkında mevzuat listesine satır.

**Servis/API.** `dengesizlik_service.segment_bilgisi` → `depolama` bloğu; `simulasyon` → `cozunurluk` (saatlik, belirsiz). PUT `/segment` `depolama` sözlüğü (422 doğrulama; güç None → beyan kaldırılır), yanıtta depolama alanları + özet; GET `/plants/{id}/depolama` (özet + dayanaklar). **Web.** Santralim › Santral ayarları › «Depolama ünitesi» bloğu: güç, kapasite, bağlantı şekli (EK), depolama UEVÇB, kabul tarihi, bütünleşik; sonuç rozetleri (dengeleme birimi / değil; emre amadelik eşiği %85/%80 ve geçiş tarihi), ayrı UEVÇB notu; Ayrıntı: dengeleme birimi, emre amadelik, ayrı UEVÇB/EK, YEKDEM, çözünürlük, sınır. Doğruluk › uzlaştırma kartına «uzlaştırma saatlik» çipi (15 dk notu title). Sahte API: segment.depolama (12 MW EK-1a bütünleşik, kabul 01.06.2025 → muaf, %85, geçiş 01.06.2030), dengesizlik.cozunurluk.

**Göç.** Yok (params_json).

**Dürüstlük.** Hesap yok; her parametre dayanak ve kesinlikle. «Koşul» kelimesi dil bekçisine takıldı (koşu kökü) → «Şart». Dayanak bloğu sicil üretimi (`kunye.blok`) biçiminde; ayrıntılı liste ayrı ad.

**İnceleme (05.11, dört ekran).** Depolama bloğu, EK seçenekleri, Doğruluk çipi koda uygun; tek bulgu sahte API: Hakkında mevzuat listesi (sahte 4 satırlık kesit) yeni satırı taşımıyordu — eklendi (canlıda liste kaynak_service.MEVZUAT'tan gelir).

**Yapılmayan / sonraya.** Emre amadelik oranı hesabı (ölçüm yöntemi bulununca); hibrit akış ayrımı (üretim / şarj / deşarj / şebekeden şarj — ayrı sayaç akışı); uzlaştırma dışı veriş miktarı; Takvim'e %85→%80 geçiş tarihi; 15 dk program biçimi (dengeleme birimi işareti zaten 15 dk satır üretir); kapasite mekanizması (2027 GES yok).

**Kanıt.** tests/test_depolama_v2543.py 6 (doğrulama, 30 MW eşiği 29,9/30, %85→%80 sınır günü ve 29 Şubat, segment bloğu, dayanak/sicil, API PUT/GET + 422); künye bekçisi 4; tam takım 893 geçti / 1 atlandı + rapor dosyaları ayrı 86 (toplam 979); web build + lint + 103; sahte önizleme kare `kanit/p9-*-2026-11-05.jpg`.

**Mühür.** b709ad2 (05.11 09:13 TSİ), CI #699 yeşil; ssh dağıtım api+worker+web 09:23 TSİ (gece turu 08:16’da bitmişti, pencere dışı); göç yok; canlı 25/25 birebir; healthz ok. Raporlar: 02 M57, 00 kırk üçüncü paket, 04 E satırı; kanıt `kanit/p9-santralim-depolama-1440-2026-11-05.jpg`.

## Kırk dördüncü paket — v2.544 (08.11.2026): dalga 3 kalanları — açık-gök kirlenme göstergesi, veri yolu beyanı ve protokol hazırlığı, P6 karar notu

**Kaynak.** YOL-HARITASI dalga 3'te P8/P9 kapandıktan sonra kalanlar: performans katmanının kirlenme/sensör kirliliği satırı (IH-090, IH-092; uydu akışı ve kirlenme sensörü yok), P4 (b) kademesi protokol/inverter canlı alımı (IH-023, IH-088; ayrı yatırım kararı, cihaz erişimi yok), P6 lisanssız mahsuplaşma (stratejik karar). Bulgular: 04-01/04-05 (IEC 61724-1 kirlenme, SolarPower Europe Modbus önerisi), 04-19 (kirlenme oranı yerel değil), 04-24h (IEC 104 RTU hattı), 06-13/06-44/06-46/06-49 (inverter bulutları, OSOS/MASS, LOGGMA), 07-12 (Karar 14531), 02-16 (LÜY m.26 saatlik mahsup), 08-14 (AYM 10.12.2026).

**(A) Kirlenme göstergesi (`kirlenme_service`, saf + DB).** Uydu yerine açık-gök modeli: pvlib Ineichen (Linke bulanıklığı aylık iklim tablosu), güneş konumu saat ortası, Hay-Davies düzlem dönüşümü santral eğim/azimutuna (`iklim_service.poa_serisi` yeniden kullanıldı). Açık saat: açık-gök POA ≥ 200 W/m², oran 0,5–1,35, komşu saatlerle fark ≤ 0,08; günde ≥ 3 açık saat → açık gün; günün açık-gök endeksi (AGE) = açık saat oranlarının medyanı; aynı saatlerde PR_açık = ΣE / (P0 × ΣPOA/1000). Son 30 takvim günündeki açık günlerde (≥ 8) doğrusal eğim %/ay (AGE ve PR_açık ayrı). Yorum çaprazı: AGE ↓ ve PR_açık ↑ ya da sabit → «ışınım sensörü kirleniyor olabilir» (sensör düşük okuyunca PR yapay yükselir); AGE sabit, PR_açık ↓ → «modüller kirleniyor olabilir»; ikisi ↓ → «birlikte ya da bulanıklık; ayrım yapılamaz»; |eğim| < %2/ay → kararlı; açık gün < 8 → yetersiz. Son yağış: meteo arşivi (hava tahmini arşivi, ≤ 24 sa öncü) günlük toplam ≥ 1 mm. Durumlar: `egim_yok` (eğim/azimut kayıtlı değil), `poa_yok`, `acik_gun_yok`, `ok`. Dürüstlük: GÖSTERGE — kirlenme oranı/kaybı (kWh, TL) hesaplanmaz (04-19 yerel oran yok), bulanıklık mevsimselliği oranı oynatır, temizlik kararı eğilim + yağış sonrası sıçrama + saha gözlemi. Model çekirdeğine girmez. API GET `/plants/{id}/kirlenme?gun=30–365`. Web: Santralim «Kirlenme göstergesi» kartı (4 KPI: AGE 7 açık gün, 30 gün eğilim, açık gün PR + eğilim, son yağış; yorum rozeti; son 10 açık gün tablosu; not).

**(B) Veri yolu ve protokol hazırlığı (`veri_yolu_service`).** Yedi yol sözlüğü: canlı (SCADA dosyası, Şeffaflık akışı, sayaç dosyası) ve hazırlık (inverter bulutu API, Modbus TCP/SunSpec, IEC 60870-5-104, OPC UA) — her birinde PVQuant'ın isteyeceği girdiler (salt-okuma anahtarı/erişim, sahip onayı, kayıt haritası / ASDU-IOA / düğüm listesi, örnek çıktı, alarm kodu sözlüğü) ve not (IEC 104: TEİAŞ RTU hattına dokunulmaz; Modbus: SolarPower Europe önerisi). `etkin_yollar()` DB'den: son SCADA dosyası (ingestion_batches), Şeffaflık kimliği + son çekiş (epias_realtime partisi), sayaç yüklemeleri (sayac_yukleme kaynak bazında son `olusturma`). Beyan `params_json.veri_yolu` {tur, saglayici, periyot_dk 1–1440, salt_okuma_onayi, not, beyan_zamani}; GET/PUT `/plants/{id}/veri-yolu` (422), denetim `veri_yolu_ayar`. Web: Santralim «Veri yolu ve protokol hazırlığı» kartı — etkin yollar (canlı rozeti, son geliş), hedef yol formu, seçilen yolun gerekenler listesi ve notu. Dürüstlük: hazırlık yolları BAĞLI DEĞİL; liste ne gerektiğini söyler, tarih vermez; bağlayıcı cihaz/anahtar/onay gelince ayrı paket.

**(C) P6 karar notu.** `docs/P6-LISANSSIZ-MAHSUPLASMA-KARAR-NOTU-2026-11-08.md`: bugün var olanlar tablosu ((i) yolu fiilen tamam: toplayıcı KÜPST payı v2.511, lisanssız SCADA durumu v2.523/v2.538, 10 yıl/alım süresi takvimi v2.524, LÜY rejimi v2.541, GTŞ ödeme zinciri v2.518), mevzuat zemini (LÜY m.26 saatlik mahsup 1.5.2026 RG 02.04.2026-33212; Karar 14531 üç sanal sayaç/limit/01.06.2026 bildirim; AYM E.2024/133 K.2025/233 RG 10.03.2026-33192 → 5346 md.6(2) 1–2. cümleler 10.12.2026'da kalkar, 3. cümle korundu; CK 11415), (ii) yolunun kalemleri ve girdileri (tüketim verisi, LÜM, GTŞ belgesi, fatura biçimleri, 10 yıl sonrası rejim belirsiz), karar soruları ve öneri ((i) ile sürdür; (ii) pilot müşteri + OSOS dışa aktarımı + GTŞ fatura örneği olmadan açılmaz). Karar sahibine; kod yazılmadı.

**Göç.** Yok (params_json).

**Brif turu (08.11; kirlenme + veri yolu doğrulama brifi, üç geçiş).** Teknik: yorum matrisi fizikle hizalandı — AGE↓ PR sabit artık «sensör» değil «atmosfer/model: kirlenme kanıtı yok» (ışınım ve üretim birlikte azalır, sensör kirlenmesine işaret etmez), AGE↑ «toparlanma»; her yorum «ölçüm sapması ≠ üretim kaybı» etiketi taşır (tur/uretim_kaybi); veri tazeliği (`tazelik`: son ölçüm > 7 gün → «veri N gündür güncellenmedi», gösterge o tarihe kadar); yağış «hava tahmini arşivi (ölçülen yağış değil)»; `yontem` satırları ekranda «Yöntem ve sınırlar» açılırında. Veri yolu: «canlı» sözü kaldırıldı — kaynak türü (dosya kaynağı / platform bağlantısı), tanımlı mı, son başarılı geliş ve tazelik (güncel ≤ 48 sa / gecikmiş / veri gelmedi) ayrı alanlar; durum anahtarları `mevcut` / `kurulmadi` («uygulamada mevcut» / «bağlantı henüz kurulmadı»); dosya kaynağı «geçmişe dönük, sürekli bağlantı değil» cümlesi. Dil: başlıklar «Kirlenme ve ölçüm tutarlılığı», «Veri kaynakları ve bağlantı durumu»; «Veri kaynağı seçilmedi», «yalnızca veri okuma izni onayı», «Hedeflenen veri kaynağı», «Seçimi kaldır». Arayüz: mobilde açılır liste kart dışına taşıyordu (max-width), seçim kaldırılınca form sıfırlanmıyordu — düzeltildi. Sahte veri: eğilim alanlarını yorum satırına düşüren hata düzeltildi, medyanlar tabloyla tutarlı.

**İnceleme (08.11, üç ekran).** Kod bulgusu yok; sahte verideki 7 günlük medyanlar tablonun son 7 günüyle tutarlı hâle getirildi (%92,2 / %85,8); hedef yol açılır listesinde çift tire yerine orta nokta ayracı.

**Yapılmayan / sonraya.** Kirlenme kaybı kWh/TL ve temizlik eşiği (yerel oran, kirlenme sensörü ya da uydu referansı gelince); hava arşivinde yağış yalnız tahmin arşivi (ölçülen yağış yok); protokol bağlayıcıları (ilk cihaz/anahtar gelince: önce inverter bulutu API ya da Modbus/SunSpec); inverter alarm kodu sözlüğü (IH-088); P6 (ii) kalemleri karar sonrası; vitrin «Kimin için» metni (K-02) karar sonrası ayrı mühür.

**Kanıt.** tests/test_dalga3_kalan_v2544.py 6 (açık/bulutlu gün ayrımı, sensör/modül/ikisi/kararlı/yetersiz yorumları, açık-gök POA ve yağış günlemesi, veri yolu doğrulama/sözlük, API kapıları); künye bekçisi 4; tam takım 898 geçti / 1 atlandı (+ rapor dosyaları ayrı koşu); web build + lint + 103; sahte önizleme kareleri `kanit/dalga3-kirlenme-koyu-2026-11-08.jpg`, `kanit/dalga3-veri-yolu-koyu-2026-11-08.jpg`; hedef yol akışı sahte PUT ile.

**Mühür.** 48ebbbd (08.11 19:08 TSİ), CI #701 yeşil; ssh dağıtım api+worker+web 19:25 TSİ (gece penceresi dışı); göç yok; canlı 25/25 birebir (canli-kiyas.sh scratchpad’de yine yoktu, yeniden yazıldı); healthz ok. Raporlar: 02 M58, 00 kırk dördüncü paket, 04 E satırı; kanıt `kanit/dalga3-*-2026-11-08.jpg`.

## Kırk beşinci paket — v2.545 (08.11.2026): dalga 3 kalanları II — kirlenme kaybı tahmini ve temizlik eşiği, Modbus TCP / SunSpec salt-okuma bağlayıcısı ve bağlantı sınaması

**Kaynak.** Dalga 3'te v2.544 sonrası kalan iki kalemin dış girdi olmadan ilerletilebilen kısımları: IH-090 (kirlenme kaybı tahmini, birikimli kWh/TL, temizlik maliyeti girdisi ve karar eşiği) ve P4 (b) ilk protokol bağlayıcısı (IH-023 Modbus/SunSpec; SolarPower Europe O&M v6.0 Modbus önerisi 04-05; IEC 104 RTU hattı 04-24h). P6 (ii) karar sahibinde (karar notu v2.544).

**(A) Kirlenme kaybı tahmini (`kirlenme_service.kayip_tahmini`, saf).** Temiz referans = pencere içindeki açık gün PR'larının %90 kantili; günlük oran r_d = PR_d/ref (≤ 1) açık günlerden ara günlere zamanla enterpolasyon; kayıp_d = E_d × (1/r_d − 1) (E_d tüm geçerli saatlerin günlük üretimi, POA'sız saatler dâhil); TL = kayıp × günlük ortalama satış fiyatı (`kayip_ayrisimi._fiyat_serisi`: tarife ya da PTF); son 30 gün kWh/TL, son 7 gün günlük ortalama yüzde, pencere toplamı. `temizlik_maliyeti_tl` (Santral ayarları, 0–100 M TL) girildiyse son 30 günün tahmini kaybı maliyeti karşılıyor mu + geri ödeme günü (maliyet / günlük TL kaybı). Geçerlilik: yorum «modül»/«ikisi» → anlamlı; «sensör»/«atmosfer» → zayıf (PR düşmediği için kayıp küçük çıkar; metin «karar için kullanmayın» der); yetersiz → belirsiz. Dürüstlük: TAHMİN etiketi, kirlenme sensörü/uydu yok, TL gelir tahmini (uzlaştırma kalemi değil). Web: Kirlenme kartında satır (rozet + kWh/TL/%/referans/temizlik karşılaştırması + geçerlilik cümlesi); Santral ayarlarına «Temizlik maliyeti (TL)» alanı ve ayrıntı maddesi; yöntem açılırına kayıp notu.

**(B) Modbus TCP / SunSpec bağlayıcısı (`io/canli/modbus_tcp.py`, `io/canli/sunspec.py`, `canli_alim_service`).** Bağımlılıksız asgari Modbus TCP istemcisi: yalnız FC3 (Read Holding Registers), MBAP başlığı, 125 kayıt parçalama, istisna kodları Türkçe; yazma fonksiyonları yapısal olarak yok. SunSpec: «SunS» keşfi (40000 / 50000 / 0), model zinciri, ortak model 1 (üretici, model, seri no), inverter 101–103 (tam sayı + ölçek faktörü) ve 111–113 (float32): akım/gerilim/güç/frekans/VA/VAr/PF/enerji/DC/sıcaklık/durum (St 1–8 Türkçe) /olay bitleri (Evt1). `canli_alim_service.sina()`: hedef doğrulama (host ≤ 253, port 1–65535, birim 0–247), ana makine adı çözümleme, adres kuralı — loopback/link-local/multicast/ayrılmış/belirsiz RED, özel ağ (VPN) ve genel İZİN (webhook SSRF kuralından bilinçli fark, saha cihazları özel ağdadır); onay yoksa sınama yok; sonuçlar ok / onay_yok / adres_reddedildi / ayar_hatasi / baglanti_hatasi. Veri yolu beyanına `baglanti {host, port, birim}` (parola yok). API POST `/plants/{id}/veri-yolu/sinama` (yazma yetkisi; yalnız hedef Modbus ve bağlantı ayarı varken; denetim `veri_yolu_sinama`). Web: hedef Modbus seçilince cihaz adresi/port/birim alanları; kaydedildikten sonra «Bağlantıyı sına» (onay yoksa kapalı) → sonuç rozeti ve cihaz özeti (üretici, model, seri, anlık kW, sayaç MWh, durum, olaylar, ağ türü) + «yalnız fonksiyon 3, yazılmadı; veri çekişi başlamaz» notu. Düzenli örnekleme ve saatlik toplama (scada_hourly'ye yazım) BU PAKETİN DIŞINDA — sınama cihaz/ağ erişiminin çalıştığını kanıtlar.

**(C) 08.11 inceleme turu (brif: üç geçişli doğrulama).** Faz 1 — kayıp tahmininin güvenilirlik sınıfı yorum koduna bağlandı: modül/ikisi → «tahmin» (temizlik karşılaştırması yapılır); atmosfer/kararlı/toparlanma/yetersiz → «şartlı senaryo» (sayı gösterilir, temizlik karşılaştırması YAPILMAZ); sensör şüphesi → «askıda» (açık gün PR'ı yanlı ölçüldüğünden referans ve kayıp hesaplanmaz; sayı yok; «önce sensörü temizleyin»). Böylece güvenilmez ölçüm görünürde kesin bir temizlik önerisi üretemez. Son 30 gün penceresi tam 30 gün (`>` sınırı) ve son ölçüm gününe göre; etiketler «Son ölçüme kadar 30 gün», «son ölçüm gününe göre» (yağış). Faz 2 — eğim birimi «göreli yüzde (puan değil)» yöntem maddesine yazıldı; yağış «gün önce» referansı açıklandı. Faz 3 — dosya kaynaklarında 48 saat ölçütü kaldırıldı («dosya yüklemesi» bilgi; 30 günden eski yükleme uyarı), «son yükleme/çekiş» ile «son ölçüm» ayrıldı (scada_hourly × ingestion_batches), EPİAŞ çekiş durumu jobs_log'dan: hata ≠ yeni kayıt yok ≠ SCADA öncelikli ≠ başarılı (worker gece_epias_uretim artık sonucu döner → jobs_log.detail); hedef bağlantı aşamaları ayrı: seçildi → ayar girildi → sınama başarılı → veri alınıyor. Faz 4 — sınama sonucu beyana yazılır (`veri_yolu.son_sinama`), sayfa yenilenince kalır; dosya kaynağı seçilince sağlayıcı/aralık/onay alanları gizlenir; onay kutusu cümle («yalnızca veri okunmasını onaylıyorum»). Faz 5 — karar notu ve yol notlarından «P4 (b)», «ayrı yatırım kararı», «bağlayıcı yazılmaz» çıkarıldı; «Hedef bağlantı seçilmedi». Faz 6 — açık gün tablosunda tarihler Türkçe ve mono değil (v2.497 kuralı).

**Göç.** Yok (params_json).

**Yapılmayan / sonraya.** Düzenli Modbus/SunSpec örnekleme işi (örnek tablosu + RLS göçü + worker + saatlik toplama + kaynak etiketi); inverter bulutu API bağlayıcıları (anahtar/örnek çıktı gelince); IEC 104 / OPC UA; kirlenme kaybı için kirlenme sensörü/uydu referansı; temizlik tarihi girişi (referans PR'ı temizlik sonrası döneme bağlamak); P6 (ii) karar sonrası.

**Kanıt.** tests/test_dalga3_kalan_v2544.py +1 (kayıp tahmini: modül senaryosunda kWh/TL/%, temizlik eşiği ve geri ödeme; sensör senaryosunda küçük kayıp + «zayıf»; yetersiz durumlar); tests/test_canli_alim_v2545.py 4 (sahte Modbus TCP sunucusuyla FC3 okuma + 125'lik parçalama + istisna 2; SunSpec keşif/ortak/inverter 103 ölçek çözümü ve olay biti; sınama onay/adres/ayar/başarı/kopuk; API kapıları 422/onay_yok/ok); tam takım; web build + lint + 103; sahte önizleme 1440/375 (`kanit/dalga3-kirlenme-kayip-1440-2026-11-08.jpg`, `kanit/dalga3-modbus-sinama-1440-2026-11-08.jpg`); sınama akışı sahte POST ile.

**Mühür.** v2.545 0dd66d4 CANLI (08.11 20:55 TSİ): CI #703 yeşil; api+worker+web ssh dağıtımı; göç yok; canlı bayt kıyası 25/25 birebir; healthz ok. Üç inceleme turu (ekran, brif üç geçiş, ekran).

## Kırk altıncı paket — v2.546 (08.11.2026): dalga 3 kalanları III — Modbus TCP / SunSpec düzenli örnekleme + saatlik toplama (göçlü), son temizlik tarihi referansı, dosya yükleme sıklığı beyanı

**Kaynak.** v2.545 «Sonraya» listesinin dış girdi gerektirmeyen üç kalemi: P4 (b)-2 düzenli örnekleme işi (IH-023), temizlik tarihi girişi (IH-090 referansı), dosya yükleme sıklığı (08.11 inceleme turunda «30 gün varsayım» notu). Bulut API bağlantıları (anahtar), IEC 104 / OPC UA (cihaz) ve P6 (ii) (karar) dış girdiye bağlı kalır.

**(A) Düzenli örnekleme (`canli_ornekleme_service`, göç `v2546_canli_ornek`).** Şartlar birlikte: hedef Modbus, bağlantı ayarı, yalnızca okuma onayı VE sahibin ayrıca işaretlediği «düzenli veri çekişini başlat» (`ornekleme_acik`; `dogrula` yalnız bu üçü varken kabul eder) — bağlantı sınaması çekiş başlatmaz (v2.545 sözü). Örnek: inverter modelinden anlık güç W, sayaç Wh, DC güç, durum kodu, olay bitleri → `canli_ornek` (RLS; SELECT/INSERT; ham, silinmez). Worker `canli_ornekleme` 5 dk aralıklı, sessiz sarmal (`_logla_tek_sessiz`: uygun santral yoksa jobs_log'a satır düşmez); periyot beyandaki veri aralığı (varsayılan 15 dk). Saatlik toplama (`saatlik_ozet`, SAF): ≥ 2 örnek ve ≥ 40 dk kapsama; enerji önce sayaç farkı (monoton), yoksa ortalama güç × kapsanan süre; `scada_hourly`'ye ayrı batch (`format_json.kaynak = modbus_sunspec`), var olan saat üzerine YAZILMAZ (dosya/EPİAŞ korunur). Veri kaynakları kartında «Modbus TCP / SunSpec · saha protokolü · örnekleme N dk · son 24 saatte n örnek · son çekiş/son ölçüm» satırı; tazelik eşiği 3 × periyot (en az 1 saat). Aşamalara «düzenli veri çekişi açık / başlatılmadı» eklendi; «veri alınıyor» ilk örnekle dolar.

**(B) Son temizlik tarihi (`son_temizlik_tarihi`, Santral ayarları).** `kayip_tahmini(temizlik_tarihi=…)`: temizlik sonrası ≥ 3 açık gün varsa temiz referans o günlerin %90 kantili, yoksa pencere kantili ve `referans_kaynak` bunu söyler. Kirlenme kartında «Son temizlik dd Mon (son ölçüm gününe göre N gün önce); temiz referans …» satırı. API doğrulama: ISO tarih, gelecekte olamaz.

**(C) Dosya yükleme sıklığı (`dosya_yukleme_sikligi_gun`, 1–90).** Dosya kaynağı tazelik eşiği = 2 × sıklık (beyan yoksa 30 gün); etiket «yükleme N günden eski»; SCADA satırında «beyan edilen yükleme sıklığı N gün».

**(D) 08.11 inceleme turu II (brif: altı faz, üç tur).** Faz 1 — Santral ayarları › «Üretim programı sınırları» alt bölümü «İşletme ayarları» oldu ve alanlar beş gruba ayrıldı (Üretim programı ve piyasa / Performans ve üretim hedefleri / Bakım ve temizlik / Veri güncelliği / Risk ve arıza kayıtları); anahtarlar, doğrulama, hesaplar ve kayıt davranışı değişmedi; Ayrıntı listesi aynı gruplarla; «Temizlik maliyeti» → «Santral temizlik maliyeti (TL, bir temizlik)» — hesapta santral geneli bir temizlik işleminin toplam bedeli olarak kullanılır (geri ödeme = bedel / günlük TL kaybı), modül başına değil; düğme «Ayarları kaydet». Faz 2 — kirlenme kartına «Değerlendirme {an}; veri {son ölçüm} gününe kadar» satırı; eğilim KPI altına «göreli değişim, puan değil». Faz 3 — bağlantı sağlığı ile veri tazeliği ayrı rozetler: EPİAŞ «bağlantı: son sorgu başarılı» + «veri: 11 gündür yeni veri yok» (`epias_baglanti`, `veri_etiketi`); Modbus satırında «son örnek alındı / örnek alınamıyor / henüz örnek alınmadı»; dosya kaynağında tek rozet. Faz 4 — sınama durumları ayrıldı: `baglanti_hatasi` (cihaza ulaşılamadı), `veri_modeli_yok` (cihaza erişildi, SunSpec/Modbus okunamadı → kayıt haritası gerekir), `kismi` (ortak model var, inverter modeli yok), `ok`; aşama etiketi buna göre; «Ayarları kaydet» mesajı «bağlantı henüz sınanmadı» der. Faz 5 — düğme/rozet adları; Faz 6 — grup başlığı mevcut jetonlarla (`.ayar-grup`), yeni renk yok.

**Göç.** `v2546_canli_ornek` — tablo `canli_ornek` (RLS, SELECT/INSERT pvq_app). Canlıda DB sahibiyle.

**Yapılmayan / sonraya.** Inverter bulut API bağlantıları (anahtar + örnek çıktı); IEC 60870-5-104 ve OPC UA (cihaz/uç nokta); kirlenme sensörü/uydu referansı; örnek tablosu saklama süresi (şimdilik silinmez); P6 (ii) karar sahibinde.

**Kanıt.** tests/test_canli_ornekleme_v2546.py 6 (şartlar + periyot; saatlik özet sayaç farkı / ortalama / sıfırlama / yetersiz; tur: periyot, uygun yok → None, hata izolasyonu (kopuk cihaz + reddedilen adres); dogrula ornekleme şartı + aşamalar; tazelik eşik + dosya sıklığı; temizlik referansı). Tam takım; ağır dosyalar ayrı; web build + lint + 103; sahte önizleme 1440/375.

**Mühür.** v2.546 e69d5b0 CANLI (08.11 22:28 TSİ): CI #705 yeşil; api+worker+web ssh dağıtımı; GÖÇ v2546_canli_ornek DB sahibiyle uygulandı; canlı bayt kıyası 25/25 birebir; healthz ok. İki inceleme turu (ekran; brif altı faz / üç tur) + son kontrol.

## Kırk yedinci paket — v2.547 (09.11.2026): dalga 3 kalanları IV — inverter bulutu bağlayıcıları (FusionSolar, SolarEdge) + anahtar saklamayan sınama, IEC 60870-5-104 ulaşılabilirlik sınaması, OPC UA kararı

**Kaynak.** v2.546 «Sonraya» listesinin son üç kalemi; dış girdi (anahtar, cihaz) gelmeden yapılabilen kısımları yazıldı, kalan kısımları açıkça etiketlendi. P6 (ii) karar sahibine sunuldu (kod yok).

**(A) Bulut bağlayıcıları (`io/bulut/`).** Üreticinin herkese açık belgelerinden, yalnız okuma: FusionSolar Northbound (login → xsrf-token → getStationList → getKpiStationHour; bölge sunucuları sabit liste intl/eu5/la5/sg5/au1) ve SolarEdge Monitoring API (sites/list, site/{id}/energy HOUR, Wh→kWh). Uç adresleri sabittir (kullanıcıdan URL alınmaz). GERÇEK HESAPLA DOĞRULANMADI — not metinlerde ve kart notunda yazar. Diğer üreticiler (iSolarCloud, Sunny Portal, SolisCloud, SEMS) «henüz yok» listesinde.
**Sınama (`bulut_sinama_service.sina`, POST `/veri-yolu/bulut-sinama`).** Kimlik (Northbound kullanıcı + systemCode ya da API anahtarı) istek gövdesinde gelir, sınama süresince bellekte tutulur, beyana ve denetim izine YAZILMAZ (test: anahtar hiçbir çıktıda yok); sonuç özeti (santral sayısı, ilk santral, kapasite, saat dilimi) `son_sinama`'ya düşer. Durumlar: ok · kimlik_hatasi · saglayici_desteklenmiyor · ayar_hatasi · baglanti_hatasi · onay_yok. Düzenli çekiş için kimlik bilgisinin ŞİFRELİ saklanması gerekir — ayrı karar; bu pakette saklama yok.
**Web.** Hedef inverter bulutu seçilince sağlayıcı seçimi (FusionSolar / SolarEdge / Diğer), FusionSolar'da bölge + kullanıcı + systemCode (parola alanı), SolarEdge'de API anahtarı (parola alanı; «kaydedilmez»); «Bulut bağlantısını sına» kimlik girilmeden kapalı; sınama sonrası kimlik alanları boşaltılır.

**(B) IEC 60870-5-104 ulaşılabilirlik (`io/canli/iec104.py`, `canli_alim_service.sina_iec104`).** TCP + STARTDT act → STARTDT con beklenir → STOPDT; hiçbir ASDU/komut (genel sorgulama dâhil) gönderilmez, veri okunmaz. Adres kuralı Modbus ile aynı. Durumlar: ok (con alındı) · protokol_yaniti_yok (TCP var, con yok — başka hizmet ya da istemci IP izni) · baglanti_hatasi · adres_reddedildi · ayar_hatasi · onay_yok. `/veri-yolu/sinama` türe göre dağıtır (Modbus → okuma sınaması, IEC 104 → ulaşılabilirlik; OPC UA → 422). Web: IEC 104 hedefinde istasyon adresi/port (varsayılan 2404), «Ulaşılabilirliği sına». Gerçek RTU ile doğrulanmadı; sahte sunucuyla sınandı.

**(C) OPC UA.** İstemci için kitaplık (asyncua) gerekir; bağımlılık eklenmedi (karar sahibine). Kart notu bunu söyler; sınama ucu 422 döner.

**(D) P6 kararı (i) — 09.11.2026.** Sahip (i) yolunu seçti: tek tesisli lisanssız dilimine girilmez; lisanssız santraller yalnız toplayıcı / görevli tedarik portföyü üzerinden kapsanır. Uygulanan tek değişiklik (K-02): vitrin Hero «Kimin için» künyesine «lisanssız santraller toplayıcı portföyü üzerinden» maddesi. Karar notu §6'ya işlendi; 04 P6 satırı güncellendi. (ii) kalemleri kapalı; yeniden açılması pilot müşteri + OSOS dışa aktarımı + GTŞ fatura örneğine bağlı.

**(E) 09.11 inceleme turu III (brif: yedi faz, üç tur — Veri kaynakları kartı).** Faz 1 — tek bağlantı durum kodu `baglanti_durumu` (yapılandırılmadı / dosya / mevcut / sınanmadı / sınama başarılı / çekiş açık / sınama başarısız / kimlik hatası / desteklenmiyor / veri akışı; eski veri bağlantıyı bozmaz, başarılı sınama veri akışı demek değildir) ve veri durumu kodu `veri_kodu` (güncel / gecikmiş / ölçüm bilinmiyor / dosya / dosya eski / yüklenmedi / gelmedi); «kaynakta yeni kayıt yok» yalnız servis yanıtı veri_yok dediğinde; dosya satırı «geçmişe dönük dosya». Faz 2 — sağlayıcı matrisi: FusionSolar/SolarEdge «bağlantı yazıldı, gerçek hesapla doğrulanmadı», dört üretici «Planlandı», Diğer «desteklenmiyor — talep olarak not edilir»; Diğer için sınama düğmesi yok, serbest ad alanı «talep». Faz 3 — «Ayarları kaydet» / «Bağlantıyı sına» ayrımı korundu; sonuç durumları tam. Faz 4 — `YETENEKLER` matrisi (sınama türü, veri okuma, düzenli çekiş, doğrulama: canlı / sahte / yok) her yolda; arayüz rozetleri bunu okur; IEC 104 «ulaşılabilirlik sınaması (veri okunmaz)». Faz 5 — kart açıklaması müşteri cümlesi, «salt okuma» → «yalnızca okuma», «ayrı pakette» çıkarıldı, protokol notları «Teknik ayrıntılar» açılırında. Faz 6 — üç bölüm: Mevcut veri kaynakları / Yeni veri bağlantısı / Bağlantı gereksinimleri (`.alt-bolum`, mevcut jetonlar). Faz 7 — kimlik beyana ve denetim izine yazılmaz (test), tür değişimi kaydetmeden hiçbir şey değiştirmez.

**Göç.** Yok.

**Yapılmayan / sonraya.** Bulut kimlik bilgisinin şifreli saklanması + düzenli bulut çekişi; bulut bağlayıcılarının gerçek hesapla canlı sınaması; IEC 104 veri çekişi (ASDU adresi + IOA listesi); OPC UA (kitaplık kararı); diğer bulut üreticileri.

**Kanıt.** tests/test_bulut_iec104_v2547.py 6 (FusionSolar giriş/liste/saatlik/305; SolarEdge liste/saatlik/403; sınama durumları + anahtar sızmaz; IEC 104 sahte sunucu con/yanıtsız/kapalı port; sina_iec104 durumları + aşama etiketi; API kapıları — anahtar beyanda ve denetim izinde yok, OPC UA 422). Tam takım; ağır dosyalar ayrı; web build + lint + 103; önizleme 1440/375.

**Mühür.** v2.547 fa3b113 CANLI (09.11 10:47 TSİ): CI #707 yeşil; api+web ssh dağıtımı (worker değişmedi); göç yok; canlı bayt kıyası 25/25 birebir; healthz ok. Üç inceleme turu (ekran; ekran; brif yedi faz / üç tur) + P6 kararı (i).

## Kırk sekizinci paket — v2.548 (09.11.2026): Aşama 0 hijyen — SolarEdge V1 devre dışı, IEC 104 varsayılan TCP, FusionSolar uç/bölge düzeltmesi, Veri kaynakları notları (mühürlendi: v2.563, 10.11)

**Kaynak.** İki dış araştırmanın (Opus «Inverter Pazar» 2 tur; Codex «Invertör Entegrasyon» 3 faz) bütünleşik değerlendirmesi: `~/Desktop/PVQuant_Entegre_Degerlendirme_2026-11-09/` (00–05). Yol haritası 04 §1 Aşama 0 kalemleri H1–H4; dış girdi gerektirmeyen tek paket. Dayanaklar: Opus 07 SE-1…SE-5 ve HW-3/HW-18/HW-19 [K77][K81][K353][K354][K364]; Opus 00 «Acil uyarı 3» ve 08 §5.9 (lib60870 tek yedeklilik grubu davranışı) [K387]; Codex 07 (Faz 3) U04 birim şüphesi.

**(H1) SolarEdge V1 devre dışı (`io/bulut/__init__.py`, `bulut_sinama_service`, `veri_yolu_service`, web).** Üretici V1 Monitoring API'yi 3 Kasım 2026'da kapattı; PVQuant'ın istemcisi V1 köküne, `api_key` sorgu parametresine, `/sites/list` ve `timeUnit=HOUR`'a yazılmıştı (beşi de geçersiz). Sicilde `durum: kapandi` + etiket; `AKTIF_SAGLAYICILAR` yalnız FusionSolar; sınama `saglayici_kapandi` döner (açıklama: V1 kapandı, V2 talep gelince); bağlantı durumu «bu sağlayıcı için bağlantı yok»; arayüzde seçenek «— devre dışı» ve seçilemez, API anahtarı alanı yok, kapanış notu görünür; «Planlandı» listesine «SolarEdge Monitoring API V2» eklendi. `solaredge.py` sınıfı referans olarak duruyor (`KAPANDI = "2026-11-03"`), çağrılmıyor.

**(H2) IEC 104 varsayılan TCP (`io/canli/iec104.py`, `canli_alim_service.sina_iec104`, `veri_yolu_service.dogrula`, API, web).** Yaygın IEC 104 slave uygulaması (lib60870 varsayılanı) yeni istemcinin STARTDT'sinde mevcut aktif bağlantıyı kapatıyor; üretici cihazlarının davranışı doğrulanmadı. Varsayılan sınama artık yalnız TCP bağlantısı açar (`startdt_gonderildi: False`, `ozet.yontem: "tcp"`, not: istasyonun 104 konuştuğu kanıtlanmaz). STARTDT yalnız beyandaki `startdt_onayi` (yalnız iec104 hedefinde ve okuma onayıyla anlamlı) ile gönderilir; web'de ayrı kutu «istasyonda PVQuant için ayrı istemci yuvası tanımlandı; STARTDT gönderilmesini onaylıyorum» + risk açıklaması; düğme başlığı ve sonuç metni kipe göre («TCP bağlantısı kuruldu; STARTDT gönderilmedi» / «STARTDT onayı alındı»). `protokol_yaniti_yok` yalnız STARTDT kipinde.

**(H3) FusionSolar düzeltmeleri (`io/bulut/fusionsolar.py`).** Santral listesi sayfalı `/thirdData/stations` (`pageNo`, `pageSize` ≤100; `plantCode/plantName/capacity` kWp, sayfalar birleşir); eski `getStationList` yalnız yeni uç `failCode 401` döndüğünde yedek (o uçta capacity MWp → kWp). Bölge listesi: `au1` (DNS'te yok) kaldırıldı; `au5`, `jp5`, `kr5` eklendi; ek olarak yalnız `*.fusionsolar.huawei.com` deseniyle ana makine adı kabul edilir (başka alan adı `ValueError`; SSRF yüzeyi yok). Hata eşlemesi: 305 oturum, 401 yetki, 407 sıklık, 20618 günlük tavan; HTTP 403/429 «1 dk bekleyin». Sınama özeti `uc` alanı (stations / getStationList). Birim semantiği (`inverter_power`) gerçek yanıtla doğrulanana kadar sabitlenmedi; sınıf alanı olduğu gibi döner.

**(H4) Veri kaynakları metinleri (`VERI_YOLLARI`, `YETENEKLER`, `NOT`).** İnverter bulutu: FusionSolar sınanabilir, SolarEdge V1 kapandı; Modbus/SunSpec: «okuyucu SunSpec 1xx (101–103, 111–113) tanır; yalnız 7xx sunan cihazlarda ve üreticiye özel haritalarda veri gelmez»; IEC 104: gerekenlere «ayrı istemci yuvası» eklendi, not ve yetenek özeti TCP/STARTDT ayrımını anlatır. Sahte API (`sahte-api-panel.mjs`) YOLLAR/bulut/NOT motordan yeniden üretildi; bulut ve IEC 104 örnek uçları yeni durumları döner.

**Göç.** Yok (beyan `params_json.veri_yolu.startdt_onayi` yeni alan, JSON içinde).

**Yapılmayan / sonraya (yol haritası Aşama 1+).** Saatlik toplama kapanış örneği ve tam/kısmi ayrımı (D1); tipli SunSpec codec (D2); MBAP unit/uzunluk (D3); cihaz/kaynak/ölçüm sınırı kimliği göçü (D4); kaynak seçimi + revizyon gölge görünüm (D5); SunSpec 7xx (S1); Modbus üretici profilleri (S2); CSV/SFTP ucu (S3); IEC 104 salt-okur istemci (S4); kimlik saklama kararı (K1) ve FusionSolar düzenli çekiş (K2); SolarEdge V2 talep üzerine (K4).

**Kanıt.** tests/test_bulut_iec104_v2547.py 8 (FusionSolar sayfalı liste + eski hesap 401 yedeği + bölge deseni/ret + 429/20618; SolarEdge kapandı sicil; sınama `saglayici_kapandi` ve alan adı dışı bölge reddi; IEC 104 sahte sunucu varsayılan TCP / STARTDT con / yanıtsız; sina_iec104 kipleri ve `ulas` çağrı sırası; API: `yontem` tcp→startdt, `startdt_onayi` yalnız iec104'te), test_veri_yolu_durum_v2547 3 (solaredge → desteklenmiyor), test_canli_alim_v2545, test_dalga3_kalan_v2544, test_dil_f09 — ilgili 22 geçti; tam takım mühürde. Web tsc + build + lint (16 eski uyarı) + 103 test. Sahte API önizlemesinde üç senaryo doğrulandı: SolarEdge seçeneği devre dışı ve kapanış notu; IEC 104 varsayılan TCP sonucu «TCP bağlantısı kuruldu; STARTDT gönderilmedi»; STARTDT onay kutusuyla «STARTDT onayı alındı».

**İnceleme turu (09.11 akşam, iki ekran).** (1) TCP kipinde «bağlantı sınaması başarılı» ifadesi fazla iddialıydı: yeni bağlantı durum kodu `tcp_ok` («TCP bağlantısı açıldı; IEC 104 sınanmadı, veri çekişi yok»), aşama etiketi «TCP bağlantısı açıldı (STARTDT sınanmadı)», sonuç rozeti nötr «TCP bağlantısı açıldı»; STARTDT kipi eskisi gibi «başarılı». Motor + sahte API + arayüz aynı kural. (2) IEC 104 hedefinde «Cihaz / sistem» alanı «SCADA / kayıt cihazı (isteğe bağlı)» oldu (yer tutucu Inavitas, SmartLogger3000). (3) Protokol sınama düğmesi yalnız formdaki tür kayıtlı türle aynıyken görünür (bulut düğmesiyle tutarlı; tür değiştirilince kayıtlı hedefin düğmesi altta kalmıyor). Testler: durum kodu ve aşama etiketi için 3 yeni iddia; ilgili 22 geçti; web tsc/build/lint 16/103; önizlemede TCP kipi başlık–aşama–rozet üçlüsü ve düğme gizlenmesi doğrulandı.

## Kırk dokuzuncu paket — v2.549/v2.550 (09.11.2026): Aşama 1 veri doğruluğu çekirdeği — saatlik toplama, tipli SunSpec, MBAP, cihaz/sınır kimliği, gölge görünüm (mühürlendi: v2.563, 10.11)

**Kaynak.** Entegre değerlendirme 04 §1 Aşama 1 (D1–D7); Codex Faz 2/3 sentetik kayıtları 07a (saat sınırı 75/100 kWh), OFF01–OFF08 (tipli sentinel, MBAP), L10 (cihaz anahtarı), C06 (negatif kırpma), C07 (sabit zaman aşımı); Codex 07/08 veri sözleşmesi (ölçüm sınırı, tamlık, revizyon). Dış girdi yok.

**(D1) Saatlik toplama (`canli_ornekleme_service.saatlik_ozet`).** Saat enerjisi E = C(saat_sonu) − C(saat_başı), KAPANIŞ ÖRNEĞİ dâhil (bir sonraki saatin açılış örneği; çift sayım yok). İki sınır da yoksa `measured_partial`. Sınır örneği tam saatte değilse ve sınırı saran iki örnek bir periyot içindeyse sayaç sınıra doğrusal interpolasyonla taşınır (`sinir_interpolasyon`). Güç zaman ağırlıklı ortalama (yamuk); sayaç yoksa ya da geri sayıyorsa enerji güç eğrisinin yamuk entegrali («entegrasyon»), yalnız iki sınır varsa tam. Kısmi saat asgari 10 dk kapsama ile kaydedilir ama üretim serisine girmez. Codex 07a vektörü: 100 kW, 0/25/50/75/100 kWh → 100 kWh tam; kapanışsız → 75 kWh kısmi (eski kod tam saat «valid» yazıyordu). pandas 3 `datetime64[us]` için zaman tabanı `total_seconds`.

**(D2) Tipli SunSpec çözücü (`io/canli/sunspec.py`).** int16/sunssf 0x8000, uint16/enum16/bitfield16 0xFFFF, int32 0x80000000, uint32/bitfield32 0xFFFFFFFF, acc32/acc64 0 (= birikmemiş; sıfır ölçüm değil), uint64 0xFFFF…FFFF, float32 sonlu değil (NaN/∞) → None. Ölçek bilinmiyorsa değer uydurulmaz; `uygulanmayan` alan listesi ve `enerji_durumu` (ok / birikmemis / olcek_yok / uygulanmamis) döner. OFF01: int16 0xFFFF = −1 W; OFF02: uint16 0x8000 = 32768; OFF03: acc32 0xFFFFFFFF geçerli; OFF04: acc32 0 → enerji yok; OFF05: ∞ karantina.

**(D3) MBAP sertleştirme (`io/canli/modbus_tcp.py`).** Yanıt başlığında işlem kimliği, protokol, BİRİM kimliği (OFF06) ve uzunluk (2–253) doğrulanır; byte-count = 2×adet ve gövde boyu birebir; kısa/uzun/parçalı çerçeve yapısal `ModbusHata(kod='protokol_hatasi')` (OFF08: IndexError yok) ve bağlantı kapatılır (eski cevap yeni isteğe bağlanmaz). Hata sınıfları: protokol_hatasi · cihaz_istisnasi(kod) · cihaz_mesgul (5/6) · zaman_asimi · baglanti_kapandi · ayar_hatasi. Zaman aşımı bağlantı başına (`baglanti.zaman_asimi_sn` 1–60; varsayılan 5; Fronius DM ≥10 önerir) — API, web alanı, sahte API.

**(D4) Cihaz / kaynak / ölçüm sınırı kimliği (göç `v2550_kaynak_saatlik`, DB sahibiyle).** `canli_ornek` + `cihaz_id` (SunSpec seri no ya da 'santral'), `sinir` (inverter_ac | plant_gross_ac | pcc_net | settlement), `profil`; birincil anahtar (plant_id, cihaz_id, ts_utc) — iki inverter aynı anda çakışmaz. Yeni `kaynak_saatlik`: kaynak × cihaz × sınır × saat × REVİZYON; tamlık (measured_complete | measured_partial | estimated), yöntem (sayac | entegrasyon), kapsama, örnek sayısı, interpolasyon bayrağı; eklemeli (eski silinmez); RLS.

**(D5) Kaynak seçimi ve gölge görünüm (`kaynak_secim_service`, GET `/v1/plants/{id}/golge-saatlik?bas&bit&sinir`).** Evrensel sıra yok: önce aynı ÖLÇÜM SINIRI, sonra tamlık, sonra santralın kaynak önceliği (`params_json.kaynak_onceligi`; varsayılan dosya/sayaç 3 > canlı 2 > EPİAŞ 1), eşitlikte ad; her kaynağın yalnız son revizyonu aday; düşük öncelikli «alternatif» olarak döner, seçim nedeni yazılır. Görünüm: seçilen saat ile `scada_hourly`'deki saat (batch kaynağıyla) yan yana, fark kWh, kısmi/tam sayımları. Tahmin, doğruluk ve kalibrasyon bu görünümü OKUMAZ; kabul sonrası ayrı iş (DEV10). `saatlik_topla`: her saat (kısmi dâhil) gölgeye, değişen değer yeni revizyon; `scada_hourly`'ye yalnız tam saatler, cihazlar toplanarak, var olan saat korunur (batch `n_cihaz`, `tamlik`). Veri kaynakları satırı: cihaz sayısı ve «kısmi saat (üretim serisine yazılmadı)».

**(D6) Negatif kırpma (`io/ingestion/validate.py`).** Küçük negatif güç 0'a kırpılmaya devam eder (karne/kalibrasyon davranışı değişmez) ama ham değer `power_kw_ham` kolonunda korunur ve kırpılan satır sayısı karneye uyarı düşer; üretim serisine girmez.

**(D7) Testler.** tests/test_asama1_dogruluk_v2549.py 9 (07a vektörü, interpolasyon, zaman ağırlıklı güç; OFF01–05; MBAP birim/uzunluk/byte-count/istisna/zaman aşımı sahte sunucuyla; bağlantı başına zaman aşımı; kaynak seçimi tamlık/öncelik/revizyon/sınır; negatif ham). tests/test_asama1_db_v2550.py 1 (test DB: iki cihaz, tam+kısmi, DO NOTHING ham, revizyon 1→2, scada_hourly toplamı, gölge görünüm). test_canli_ornekleme_v2546 yeni semantiğe uyarlandı. Test DB göçü uygulandı (`v2550_kaynak_saatlik (head)`); RLS/rol testleri geçti.

**Yapılmayan / sonraya.** Gölge görünümün arayüzü (Aşama 5 V4 ile); dosya/EPİAŞ saatlerinin gölgeye yazılması (bugün yalnız canlı toplama yazar; dosya/EPİAŞ scada_hourly'de); tüketime geçiş (DEV10); gerçek cihazla doğrulama.

## Ellinci paket — v2.551–v2.554 (09.11.2026): Aşama 2 saha yolları — SunSpec 7xx, üretici Modbus profilleri, üretim dosyası itme, IEC 104 salt-okur istemci (mühürlendi: v2.563, 10.11)

**Kaynak.** Entegre değerlendirme 04 §1 Aşama 2 (S1–S4); Opus 08 §2 (7xx register tabloları, sunspec/models JSON), 05 sıra 2 (üretici haritaları K380/K381/K382 yerel kopyaları pdftotext ile okundu), 05 sıra 5 (itme yolları), 08 §5 (IEC 104 APCI/ASDU, k/w/t, salt-okur küme); Codex T35/T40 (Huawei 150K-MG0 1/701/702/714). Dış girdi: gerçek cihaz yok; haritalar üretici belgesinden, DOĞRULANMADI etiketiyle.

**(S1) SunSpec 7xx (`io/canli/sunspec.py`).** 701 DERMeasureAC (ACType, St, InvSt, ConnSt, Alrm bitleri, W/VA/Var/PF/A/LNV, Hz uint32, TotWhInj uint64, sıcaklıklar, ThrotPct, 10 SF; MnAlrmInfo okunmaz), 702 DERCapacity (WMaxRtg, VAMaxRtg, VarMaxInjRtg), 714 DERMeasureDC (toplam + NPrt port bloğu 25 kayıt; cihazın bildirdiği L esas). Öncelik 701 > 103/102/101 > 113/112/111; aynı cihazda çift sayım yok; `enerji_yolu` 701 | 1xx | yok (701'de TotWhInj isteğe bağlı → 1xx WH yedeği → yoksa toplayıcı güç entegrasyonu «entegrasyon» niteliğiyle). 701.InvSt → 103.St +1 eşlemesi; InvSt yoksa St/ConnSt'den. Keşif 40000 → 0 → 50000; L=0 ya da adres taşmasında zincir biter. Sınama özeti `profil`, `enerji_yolu`, `uygulanmayan` taşır; kümülatif enerji yoksa not düşer.

**(S2) Üretici Modbus profilleri (`io/canli/profiller.py`; FC04 `modbus_tcp.oku_giris`).** Profil sicili: belge adı/sürümü, fonksiyon, adres tabanı, kelime sırası, geçersiz-değer kuralları, alanlar. Huawei SmartLogger 3000 (FC3; 40525 I32 aktif güç W, 40521 giriş gücü, 40560/40562 E-Total/E-Daily ×100 Wh, 40543 santral durumu; birim 0; sınır santral toplamı), Sungrow dizi inverteri (FC4; belge adresi −1; U32 KÜÇÜK uçlu; 5031 aktif güç W, 5004 toplam üretim kWh, 5003 günlük 0,1 kWh, 5017 DC W, 5036 Hz, 5038 çalışma durumu Appendix 1 kodları, 5001 anma, 4990 seri; 0xFFFF/0x7FFF/0x7FFFFFFF geçersiz), Growatt (FC4; 0 durum, 1 Ppv, 35 Pac 0,1 W, 37 Fac 0,01 Hz, 53/55 günlük/toplam 0,1 kWh; yüksek kelime önce). Beyan `baglanti.profil` (varsayılan sunspec); `hedef_dogrula` doğrular; `cihaz_oku` sınama ve örneklemede dallanır; web «Kayıt haritası» seçimi (profilin varsayılan birimini önerir) ve belge/sınır/doğrulama notu. Saatlik toplama: aynı saatte santral toplamı (plant_gross_ac) varsa inverter satırları toplanmaz. FC04 yine okuma; yazma fonksiyonu yok.

**(S3) Üretim dosyası itme (`itme_service`, dış API `POST /v1/dis/santral/{id}/uretim-dosyasi`, worker `itme_klasoru`).** Yeni kapsam `gerceklesen:yaz` (sicil + Kuruluş kartı etiketi + dış API belgesi). HTTP itme ve `PVQ_ITME_DIZIN/<santral>/gelen/` klasör taraması (SFTP hesabı işletim tarafında, chroot; parola müşteride) aynı işleyiciden geçer: mevcut alım hattı (biçim/eşleme algılama, kayıtlı şablon, doğrulama karnesi) → scada_hourly (dosya kaynağı). Tekrar politikası `params_json.itme.tekrar` (sum | mean | error). Güvenlik: klasör adı = santral kimliği, yol kaçışı reddi, ≤50 MB, .csv/.xlsx/.xls, son 60 sn'de değişen dosya beklemede; işlenen → islenen/, hatalı → hatali/ + .hata.txt; denetim izi. Yeni tablo yok.

**(S4) IEC 104 salt-okur veri istemcisi (`io/canli/iec104_istemci.py`, `iec104_nokta_service`).** APCI I/S/U çerçeveleri, STARTDT/STOPDT/TESTFR, k/w/t0–t3 ve CA/IOA/COT boyları santral başına (`beyan.iec104`), genel sorgulama C_IC_NA_1 (QOI 20) — giden yönde yalnız 100 (ops. 101); 103 saat eşitleme ve tüm komutlar kod yolunda yok (`GIDEN_IZINLI`). Gelen ASDU 1/3/9/11/13/15/30/31/34/35/36/37/70, SQ=0/1, kalite bitleri IV/NT/SB/BL/OV, CP56Time2a (cihaz saati, UTC varsayımı işaretli). Nokta tablosu CSV (ioa, alan, carpan[, ad][, tip]) `POST /veri-yolu/iec104-nokta-tablosu` ile beyana; PUT'ta tür aynıysa korunur. Sınama: STARTDT onayı + nokta tablosu → GI ile okuma (`yontem: gi`; eşlenen alan, ikame, eksik, gelmeyen IOA, gönderilen tipler), yalnız onay → STARTDT ulaşılabilirlik, yoksa TCP. Düzenli çekiş: IEC 104 hedefi de örneklemeye uygun (STARTDT onayı + nokta tablosu + çekiş açık); örnek `cihaz_id: scada`, sınır beyandan (varsayılan santral toplamı), `canli_ornek.kaynak = iec104` (göç CHECK genişletildi), gölge ve scada_hourly aynı kurallarla. Aşamalara «nokta tablosu» eklendi; etkin satır IEC 104 için de.

**Göç.** `v2550_kaynak_saatlik` güncellendi (canli_ornek.kaynak CHECK: modbus_sunspec | iec104); test DB'de indirilip yeniden uygulandı.

**Kanıt.** tests/test_sunspec_7xx_v2551.py 4 (1+701+702+714 sahte cihaz; TotWhInj yok → 1xx yedeği / entegrasyon notu; InvSt/alarm; zincir savunması ve kısa 701), tests/test_modbus_profiller_v2552.py 5 (üç profil, FC4 çerçevesi, profil doğrulama/sınama/örnek), tests/test_itme_v2553.py 3 (klasör akışları, gerçek alım hattıyla dosya işleme ve cihaz bazlı tekrar politikası, dış API kapısı), tests/test_iec104_istemci_v2554.py 4 (çerçeve/ASDU çözücü, sahte istasyonla GI — giden yalnız tip 100, nokta tablosu CSV/eşleme/kalite, sınama GI kipi + beyan + örnekleme kapısı). İlgili 14 dosya 68 test + DB testi geçti. Web tsc/build/lint/test aşağıda.

**Yapılmayan / sonraya.** Üretici haritalarının ve 7xx'in gerçek cihazla doğrulanması (P-1xx/P-7xx pilotları); IEC 104 pilotu (sahibin ayrı istemci yuvası, nokta tablosu); SFTP hesabı açma (işletim); Sungrow/Huawei nokta tablosu dışa aktarım biçimlerinin dönüştürücüsü (biçim görülmedi); K1 kimlik bilgisi saklama kararı ve bulut çekişi (K2–K4); edge (E1–E2); V1–V5 ürün katmanı.

## Elli birinci paket — v2.555 (09.11.2026): Aşama 5 (kısmi) — gölge görünüm kartı ve cihaz durumundan olay adayları (mühürlendi: v2.563, 10.11)

**Kaynak.** Entegre değerlendirme 04 §1 Aşama 5: V1/V4 (üç kaynaklı tutarlılık ve kaynak niteliğinin görünürlüğü) ve V2 (cihaz durumundan olay adayı); Codex DQ01/DQ21 (iletişim kopukluğu üretim 0 değildir; alarm kodu uydurulmaz).

**(V1/V4) Kaynak kıyası kartı (Santralim «Kaynak kıyası ve cihaz durumu»; GET `/golge-saatlik`).** Son 7 günün gölge saatleri: seçilen kaynak (+ alternatif sayısı), tamlık (tam / kısmi rozetleri) ve yöntem, revizyon (r2…), kWh, üretim serisindeki saat (kaynağıyla), fark kWh, seçim nedeni; özet rozetleri (saat, tam, kısmi «üretim serisine yazılmadı», fark > 0,5 kWh). Kart yalnız API varken görünür; tahmin/doğruluğun bu görünümü kullanmadığı notu kartta.

**(V2) Cihaz durumundan olay adayları (`cihaz_olay_service`, GET `/olay-adaylari?saat=72`).** SAF: cihaz başına ardışık «arıza (durum 7) ya da alarm bitli» örnek koşusu (≥2 örnek, ya da koşu ≥10 dk; sürüyorsa şimdiye kadar), bitiş = normale dönen ilk örnek, kodlar birleşik; örnekleme açıkken 3 periyottan uzun boşluk «iletişim kopukluğu» (olay türü değil, bilgi). Mevcut olay kaydıyla çakışan aday «kayıtlı» işaretlenir, gizlenmez. Otomatik olay kaydı YOK; kart adayı listeler, kayıt Olay kaydı sayfasından elle. Tek arıza örneğiyle bitmiş koşu (gürültü) aday değil.

**Göç.** Yok.

**Kanıt.** tests/test_cihaz_olay_v2555.py 2 (koşu/boşluk/sürüyor/gürültü; çakışma ve cihaz ayrımı). Web tsc; sahte API `golge-saatlik` ve `olay-adaylari` örnekleri.

**Aşama 5 kalanları (dış girdi / tasarım kararı).** V3 toplayıcı portföyü toplu bağlantı (gerçek portföy envanteri), V5 kısıt sinyalinin sapma açıklamasına bağlanması (talimat verisi), rapor ve dış API'de kaynak niteliği sütunu (gölge görünüm kabul edildikten sonra, DEV10).

## Elli ikinci paket — v2.556/v2.557 (09.11.2026): Aşama 3 K1/K2 — şifreli kimlik kasası ve FusionSolar düzenli çekiş (mühürlendi: v2.563, 10.11)

**Kaynak.** Entegre değerlendirme 04 §1 Aşama 3 (K1 karar: uygulama içi KEK; K2 FusionSolar düzenli çekiş); Opus 05 §«Kimlik bilgisi saklama» [K407][K397][K393] (zarf deseni; TR bölgesi KMS yok), T2_04 (getKpiStationHour: stationCodes ≤100 tek çağrı, collectTime santral saat dilimi, günlük Roundup(n/100)+24), ek alıntı (hourly alanlar: inverter_power kWh); Codex U04/G07.

**(K1) Karar ve kasa (`guvenlik/kasa.py`).** Kayıt başına DEK (AES-256-GCM) gövdeyi, ortamdaki KEK (PVQ_KEK base64 32 bayt; PVQ_KEK_ID; dönüş için PVQ_KEK_ESKI) DEK'i sarar; AAD tenant:plant:saglayici (kayıt başka santrala/kiracıya taşınamaz); `yeniden_sar` dönüşte yalnız DEK'i yeniden sarar. KEK yoksa saklama reddedilir («kasa kapalı»; sınama sürer). Çözülmüş değer günlük/denetim izine yazılmaz; hata metinleri anahtar içermez. Bağımlılık `cryptography>=42` (pyproject; yerelde 48.0.1 wheel, imajda pip çözer). İşletim belgesi docs/guvenlik/KEK-ANAHTARI.md; .env.example güncellendi. KVKK md. 9 görüşü AÇIK (hukuki girdi).

**Tablolar (göç v2556_bulut_kimlik; RLS).** `bulut_kimlik` (UNIQUE plant+saglayici; kek_id/dek_sarili/sifreli/surum; maskeli etiket; onay_json iki onay metni+zaman+aktör; cekis_acik; birim_dogrulandi; kota_gun/kota_sayac; son_cekis/son_durum/son_hata) ve `bulut_saatlik_ham` (sağlayıcının saatlik dataItemMap'i jsonb, birim yorumlanmadan). Test DB'de uygulandı; canlı DB sahibiyle mühürde.

**Akış ve uçlar.** Sahip iki onayı işaretler («yalnızca veri okunmasını onaylıyorum» + «kimlik bilgisinin PVQuant'ta şifreli saklanmasını ve yalnızca düzenli veri çekişinde kullanılmasını onaylıyorum») → kimlik sınanır (giriş + santral listesi; geçmeden hiç yazılmaz) → sağlayıcı santralı seçilir (tek ise otomatik; çoksa `santral_secimi_gerekli` ile liste) → zarf şifreli kayıt. Uçlar GET/POST `/v1/plants/{id}/bulut-kimlik`, PATCH/DELETE `…/bulut-kimlik/{saglayici}` (CORS'a PATCH eklendi). Yanıt ve denetim izi (`bulut_kimlik_kaydet/ayar/sil`) yalnız maskeli etiket ve santral kodu taşır. params_json.veri_yolu.bulut_kimlik aynası (gizli yok) → aşama rozeti «kimlik şifreli kayıtlı · çekiş açık/kapalı», bağlantı durumu `cekis_acik`, etkin satırda hesap/kota/ham saat notu; ayar PUT'unda tür aynıysa ayna korunur.

**(K2) Düzenli çekiş (`bulut_cekis_service`, worker `bulut_cekis` saatlik).** Hesap başına tek giriş (login 5/10 dk), hesabın tüm santral kodları tek çağrıda (≤100), bugün + yerel 01:xx'te dün; kota sayacı hesaptaki kayıtlara yazılır, 24'te durur (25'in biri yedek). Hata sınıfları kimlik_hatasi/kota/hata/kasa_hatasi; metinde kimlik yok. Ham tabloya upsert; `birim_dogrulandi` işaretliyse kaynak_saatlik'e (kaynak fusionsolar, cihaz bulut, sınır inverter_ac, yöntem saglayici; yalnız tamamlanmış saat; değişen değer yeni revizyon). scada_hourly'ye YAZILMAZ (D5 kabul sonrası). Kaynak önceliği fusionsolar=1 (doğrudan okumaların altında). `FusionSolar.saatlik` çoklu kod + ham data[] döner.

**Ekran.** Santralim › Veri kaynakları, FusionSolar bölümü: ikinci onay kutusu (kasa kapalıysa devre dışı + açıklama), «Sına ve şifreli kaydet», santral seçimi, kayıt satırı (hesap etiketi, bölge, sağlayıcı santralı, son çekiş durumu, bugün x/24 çağrı, «Düzenli çekişi başlat/durdur», «birim doğrulandı», «Kimliği sil»), son ham saatler tablosu (belgeye göre alan etiketleri + birim notu). systemCode etiketi güncellendi; «zarf» müşteri yüzünden çıkarıldı (dil bekçisi).

**Kanıt.** Yeni testler: test_kasa_v2556 (3: gidiş-dönüş/AAD, KEK yok/bozuk, dönüş), test_bulut_kimlik_v2556 (3: onaylar/kasa/kapanan sağlayıcı, sınama geçmeden yazılmaz + santral seçimi, zarf düz metin içermez + worker çözer), test_bulut_cekis_v2557 (3: satır/gün/kota/sınıf, tek giriş-tek çağrı + birim kapısı, kota dolu + kimlik sızdırmaz), test_bulut_kimlik_db_v2556 (1: DB'de düz metin yok, RLS, güncelleme, çekiş turu ham/gölge/revizyon/kota, silme); 3 eski test güncellendi. pytest 957 geçti / 1 atlandı; web tsc/build/lint 16 (eski)/103 test; sahte API önizlemesinde uçtan uca akış (kayıt → santral seçimi → çekiş açık → 3/24 çağrı → ham tablo).

**Mühürde.** api+WORKER+web dağıtım; GÖÇ v2556 DB sahibiyle; `.env`'e PVQ_KEK (+ PVQ_KEK_ID) eklenip api+worker yeniden başlatılmadan kasa kapalıdır (UI bunu söyler).

**Aşama 3 kalanları (dış girdi).** Gerçek NBI hesabıyla birim semantiğinin doğrulanması (P-FS; «birim doğrulandı» ondan sonra işaretlenir); K3 Solis/Sungrow/Growatt ve K4 SolarEdge V2 yalnız müşteri talebiyle; KVKK md. 9 hukuki görüş.

**İnceleme turu (09.11 gece, ekran görüntüsü).** (1) Kimlik kaydı sınamayla geçtiği hâlde aşama «bağlantı sınanmadı» kalıyordu → kayıtta `son_sinama` yazılır (santral listesi params'a yazılmaz). (2) Başlık rozeti «ilk örnek bekleniyor» bulut için yanlış sözcüktü → «ilk veri bekleniyor»; mock'ta çekiş açılınca etkin satır eklenir, motor zaten ekliyordu (→ «veri alınıyor», bulut satırı «Mevcut veri kaynakları»nda). (3) Onay sırası: önce «yalnızca veri okunmasını onaylıyorum», sonra şifreli saklama onayı + «Sına ve şifreli kaydet», sonra kaydet düğmeleri. (4) Bulutta «Veri aralığı (dakika)» anlamsız (sağlayıcı saatlik) → gizlendi. (5) Işınım kWh/m² iki ondalık; «Alındı» ve son çekiş saatli. (6) «systemCode (kaydedilmez)» etiketi güncel durumla çelişiyordu → «systemCode», ipucu «sınamada gönderilir, yalnız onayla şifreli saklanır». (7) Kart açıklaması «henüz kurulmadı» → «gerçek cihaz ya da hesapla henüz doğrulanmadı». Kanıt: ilgili 22 pytest, web kapıları, sahte önizleme.

## Elli üçüncü paket — v2.558–v2.561 (09.11.2026): kalan aşamalar — V3/V5 (Aşama 5), V4, pilot kiti (Aşama 4), saha toplayıcısı (Aşama 6) (mühürlendi: v2.563, 10.11)

**Kaynak.** Entegre değerlendirme 04 §1: V3 toplayıcı portföyü, V4 kaynak niteliği raporda/API'de, V5 kısıt sinyali; Aşama 4 kapıları (Codex Faz 3 G01–G10, 09/15); Aşama 6 E1/E2 (Codex 07 §journal/ack, 10 pilot tasarımı, 08 §mTLS/scope). SunSpec 701 ThrotPct/ThrotSrc, 704 WMaxLimPct, 123 Immediate Controls (Opus 08 tabloları; yalnız okunur).

**(V3) Logger'da çoklu cihaz (v2.558).** `baglanti.cihazlar` — aynı adres/port arkasındaki ek birim kimlikleri (≤32, tekil, ad/profil isteğe bağlı; `hedef_dogrula`). `ornekler_al` ana + ek cihazları ayrı örnekler; bir cihazın hatası diğerlerini durdurmaz, kısmi başarı günlüğe düşer. Seri no yoksa kimlik «birim-N» (çakışma yok). Saatlik toplama cihaz bazında; santral toplamı cihazların toplamı (D5 kuralı). Ekranda «Ek cihazlar (birim kimlikleri)».

**(V5) Kısıt göstergesi (v2.558).** 701 `ThrotPct` + `ThrotSrc` bitleri (MAX_W, FIXED_W, …, HVRT); 704 ve 123 azami güç sınırı YALNIZ OKUNUR (PVQuant yazmaz) → `kisit_ozeti`: kısma yüzdesi, etkin, kaynak, model. canli_ornek.kisit_yuzde (göç v2558). Olay adayı türü «güç kısması (cihaz raporu)»: aynı eşik (≥2 örnek ya da ≥10 dk), ortalama/en çok yüzde, kaynak bitleri; notu açık: talimat (YAT/YAL) mı PPC ayarı mı cihaz koruması mı buradan bilinmez — Olay kaydında talimat türüyle işlenirse sapma açıklamasında ayrışır. Üretici haritalarında (Huawei/Sungrow/Growatt) kısıt kaydı yazılmadı (belge yok).

**(V4) Kaynak niteliği raporda ve dış API'de (v2.559).** `kaynak_secim_service.nitelik_ozeti`: dönemde üretim serisi saatlerinin kaynak dağılımı (parti kaynağı) + gölge tablonun son revizyon özeti (kaynak × tamlık, revizyonlu saat sayısı). Dönem raporu JSON'una `kaynak_niteligi`, HTML'e «Veri kaynağı niteliği» tablosu, kaynaklar notuna metin. Dış API `GET /v1/dis/santral/{id}/kaynak-saatlik?bas&bit&sinir` (gerceklesen:oku; ≤31 gün): her saatin kaynak / sınır / nitelik / revizyon kimliği, üretim serisiyle yan yana; «tahmin ve doğruluk bu görünümü kullanmaz; UEVM değildir». docs/api/dis-api.md satırı.

**(Aşama 4) Pilot kiti (v2.560).** `pilot_service.KAPILAR` G01–G10 (G01–G06, G10 ortak P0; G07–G09 markaya özgü): «kod» kapıları (G05, G06) PVQuant testleriyle kapalı; «saha» kapıları sahibin tarihli, notlu beyanıyla (params_json.pilot.kapilar; `PUT /pilot/kapi/{kod}`; kod kapısı elle değişmez). `sahaya_hazir` yalnız tüm P0 kapalıyken. Referans kıyası (`POST /pilot/referans`, CSV zaman+kWh, ≤5 MB): gölge görünümdeki TAM saatlerle saat saat; kısmi/tahmini ve gölgesiz saatler referans dışı; tolerans saat başına en çok(%2, 0,5 kWh); <24 ortak saat «yetersiz», ≥%95 toleransta «uyumlu», aksi «uyumsuz» (fark kaynağı: ölçüm sınırı, saat dilimi, kayıp, çift sayım). Ham referans saklanmaz, özet params'a. Ekranda «Pilot kapıları ve saha toplayıcısı» kartı.

**(Aşama 6) Saha toplayıcısı (v2.561).** E2 kimlik: `edge_toplayici` — santrala bağlı anahtar «pvqe_<önek>_<gizli>», sunucuda yalnız SHA-256 özeti, bir kez gösterilir, iptal edilebilir; gövdede santral yok (anahtar belirler → A kiracısı B santralına yazamaz). E1 alım: `POST /v1/edge/ornekler` (≤500; başlık X-Toplayici-Anahtar) — `edge_alim` defteri (santral, toplayıcı, sıra) içerik özetiyle; aynı sıra aynı içerik → yinelenen (ack ilerler), farklı içerik → çatışma (reddedilir); ack yalnız kalıcı yazım sonrası; örnekler canli_ornek'e `kanal='edge'`, saatlik toplama aynı motor (çift sayım yok — DB testi). Sunucu komut göndermez. Referans toplayıcı `scripts/edge_toplayici.py`: yalnız okur (pvquant profilleri), JSONL journal fsync, sıra/ack dosyaları, parti gönderim, geri çekilme, ack'lanmamış satır asla silinmez, eşik aşımında ALARM, mTLS istemci sertifikası seçeneği. İşletim belgesi docs/edge/TOPLAYICI.md (Caddy `client_auth` bloğu belgede; bu sürümde zorunlu değil). Veri kaynakları kartında toplayıcı veri gönderiyorsa canlı satır «saha toplayıcısı».

**Göç.** v2558_edge_kisit (canli_ornek.kisit_yuzde, kanal; edge_toplayici; edge_alim; RLS) — test DB'de uygulandı; canlı DB sahibiyle mühürde. CORS'a PATCH (v2.557 ile).

**Kanıt.** test_v3_v5_v2558 (4), test_pilot_edge_v2560 (5), test_edge_db_v2561 (1, DB: özet saklanır, defter, kanal edge, yeniden gönderimde çift sayım yok, iptal, pilot kapısı beyanı). pytest 967 geçti / 1 atlandı; web tsc/build/lint 16/103; sahte önizlemede kartlar (pilot kapıları + toplayıcı; kısıt adayı; ek cihaz alanı).

**Kalanlar (dış girdi).** Gerçek cihazla doğrulama (P-1xx/P-7xx/P-104/P-SFTP/P-FS): kapılar sahibin beyanını bekler; kısıt bitleri ve 704/123 okumaları gerçek cihazda görülmedi; mTLS/sertifika döndürme işletimi ilk çok sahalı müşteriyle; K3/K4 bulut bağlayıcıları yalnız talep; KVKK md. 9 görüşü; V3'ün UEVÇB bazlı portföy toplaması mevcut portföy altyapısında (v2.511) — yeni envanter gelince sıra güncellenir.

**İnceleme turu (09.11 gece, pilot kartı ekran görüntüsü).** (1) «Huawei'ye özgü (markaya özgü)» yinelemesi → kapı adları «Huawei/GoodWe/Sungrow bağlantısı», eki «(markaya özgü; P0 değil)». (2) Kod kapılarının etiketi «kod testleriyle kapalı; gerçek cihazda doğrulanmadı» (aşırı iddia yok). (3) Kutu/rozet sütunu sabit genişlik → satırlar hizalı. (4) Referans CSV ipucu (sütunlar, yalnız tam saatler) ve «uzlaştırma sayacı» sınır seçeneği. (5) Sıra numarası binlik ayracısız. (6) «kutu» → «saha bilgisayarı». Kapılar ve sahte önizleme yeniden koştu.

## Elli dördüncü paket — v2.562/v2.563 (10.11.2026): K3/K4 bulut bağlayıcıları, edge mTLS araçları, portföy bağlantı görünümü, KVKK taslağı (mühürlendi: v2.563, 10.11)

**Kaynak.** Entegre değerlendirme 04 §1 Aşama 3 K3 (Solis/Sungrow/Growatt) ve K4 (SolarEdge V2); Opus 08 §1 (SolarEdge V2 [K77][K351–K358]), §3 (iSolarCloud [K87][K88][K366]), §4 (SolisCloud [K93][K94][K367][K368]); Opus 04_api_grup_B §Growatt (ShowDoc v1/v4). Aşama 6 E2 (Codex 08 §mTLS/scope). V3 toplayıcı portföyü.

**(K3/K4) Bağlayıcılar — ortak arayüz (`io/bulut/temel.py`).** `giris(kimlik) → santraller() → saatlik_ham(kodlar, gun) → kapat()`; sınıf alanları sicile iner (kimlik alanları ve etiketleri, gizli alanlar, bölge sunucuları, günlük tavan, TOPLU, ham alan etiketleri, birim notu, durum «uygulandi_dogrulanmadi»). `alanlar.enerji_kwh_belge` = belgeye göre saatlik kWh (varsa); gölge görünüme yalnız «birim doğrulandı» ile. Çağrı sayacı ve `cagri_tahmini` kota defteri için.
- **SolarEdge V2** (`solaredge.py` yeniden): filo anahtarı `X-API-Key` BAŞLIKTA; `GET /v2/sites` sayfalı; `GET /v2/sites/{id}/energy?resolution=HOUR&unit=KWH` saat dilimli from/to (≤24 sa); 429'da `x-ratelimit-remaining-minute` ile CPM/kredi ayrımı; 401/403 alt türleri; site başına çağrı; günlük tavan 60 (Free kademe). Site sahibi OAuth yolu YOK (uygulama kaydı + geri dönüş ucu gerekir). V1 sicilde `solaredge_v1` «kapandi» olarak kaldı.
- **SolisCloud V2.0** (`solis.py`): HMAC-SHA1 imza (Content-MD5 Base64, Date GMT, imza dizesi, `Authorization: API id:sign` boşluksuz) — belgedeki örnek özet `kxdxk7rbAsrzSIWgEwhH4w==` testle birebir; taban www/v3 seçeneği (kanonik host doğrulanmadı); `userStationList`, `stationDay` (5 dk güç + kümülatif üretim → saatlik fark); uç başına 2/sn bekleme; yazma uçları (addStation, stationUpdate, addStationBindCollector, delCollector, addDevice) istemcide YASAK.
- **Sungrow iSolarCloud** (`sungrow.py`): POST gateway, `x-access-key` + `Authorization: Bearer`, gövdede appkey; E00003'te `refreshToken` ile yenileme, yeni belirteç çifti `kimlik_yenile` geri çağrısıyla zarf şifreli saklanır (atomik UPDATE; −2 → sahipten yeniden onay); `queryPowerStationList`; `getPowerStationPointMinuteDataList` 3 saatlik pencere × 8, ≤50 santral, p83022 kümülatif Wh → saatlik fark, p83033 güç. Bölge sahibin hesabına göre (TR bölgesi doğrulanmadı). Ticari kullanım Sungrow yazılı onayı (VIII(c)) — dış girdi. Sahip onayı yönlendirmesi PVQuant'ta yok (belirteçler girilir).
- **Growatt OpenAPI v1** (`growatt.py`): başlıkta `token` (kurulumcu/distribütör OSS başvurusu); `/v1/plant/list`, `/v1/plant/power` (5 dk güç, günde 1); saatlik kWh verilmez → yalnız ham (gölgeye yazılmaz); 10012 sıklık, 3 ay geçmiş, IP beyaz listesi notu.
- **FusionSolar** ortak arayüze uyarlandı (`giris(dict)` da kabul; `saatlik_ham`).

**Servis genellemesi.** `bulut_sinama_service` sicildeki her etkin bağlayıcı için tek akış; `bulut_kimlik_service.kimlik_guncelle` (token yenilemesi, aynı AAD); `bulut_cekis_service.tur` hesap başına gruplama (sağlayıcı, bölge, kimlik), TOPLU/santral başına çağrı, sağlayıcı tavanı, gölgeye `enerji_kwh_belge`, kaynak = sağlayıcı kodu; `saglayici_alanlari()` UI için; kaynak önceliği ve etiketleri yeni kaynaklarla. Ekran: kimlik alanları ve bölgeler sicilden (gizli alanlar parola), ham tablo sütunları sağlayıcının alanlarına göre, kota tavanı sağlayıcıya göre.

**(Aşama 6 E2) mTLS araçları.** `scripts/edge_ca.sh` (kök CA, istemci sertifikası ver/iptal/CRL/liste; openssl; kök anahtar yalnız yerelde) — ver/iptal akışı testle doğrulandı; `docs/edge/Caddyfile.edge-mtls.snippet` (ayrı alt alan adı, `client_auth require_and_verify`, CRL); TOPLAYICI.md döndürme adımları. Zorunluluk ilk çok sahalı müşteriyle; imzalı güncelleme yok (git etiketi/wheel).

**(V3-b) Portföy bağlantı görünümü.** `portfoy_service._baglanti` (SAF, beyan aynasından: hedef kaynak kısa adı, bağlantı durumu, sağlayıcı, çekiş açık, cihaz sayısı); Portföy tablosunda «Bağlantı» sütunu. Toplayıcı/GTŞ birden çok santralın durumunu tek bakışta görür; ayrıntı Santralim'de.

**KVKK.** docs/guvenlik/KVKK-BULUT-KIMLIK-DEGERLENDIRME.md — hukuki görüş DEĞİL; olgular, veri akışı, danışmana 6 soru, mevcut teknik tedbirler.

**Göç.** Yok (v2558 geçerli). **Kanıt.** test_k3_k4_v2562 (8: sicil, Solis imza vektörü + yasak uç, Solis/SolarEdge/Sungrow/Growatt sahte taşıyıcı akışları, genel sınama + çekiş + kota, portföy bağlantı); eski bulut testleri yeni sicile göre güncellendi. pytest 975 geçti / 1 atlandı; web tsc/build/lint 16/103; sahte önizleme.

**Kalanlar (dış girdi).** Gerçek hesaplarla doğrulama (dört yeni bağlayıcı + FusionSolar); Sungrow ticari onayı; Solis sahip bileti; Growatt kurulumcu belirteci + IP beyaz listesi; SolarEdge filo onayı/Associated Accounts; Sungrow/SolarEdge sahip OAuth yönlendirmesi (platform uygulama kaydı); KVKK danışman görüşü; mTLS zorunluluğu ve imzalı güncelleme (ilk çok sahalı müşteri); GoodWe/Deye/Sofar bağlayıcıları (planlandı).

**İnceleme turu (10.11, bulut formu ekran görüntüsü).** (1) «Diğer» seçiliyken açıklama her sağlayıcı için «(bağlantı yazıldı, gerçek hesapla doğrulanmadı)» ekini yineliyordu → tek parantez, adlar listesi. (2) Hedef «not», yetenek özeti ve kart dip notu hâlâ yalnız FusionSolar'dan ve «V2 talep gelince»den söz ediyordu → beş bağlantı, iki onaylı şifreli saklama, «hiçbiri gerçek hesapla doğrulanmadı», V1 devre dışı, GoodWe/Deye/Sofar planlandı. (3) Sağlayıcı adı yer tutucusu «ör. iSolarCloud» (artık destekleniyor) → «ör. Deye Cloud». Sahte API yol listesi ve dip notu motordan yeniden üretildi.

**Mühür.** v2.563 57fe359 CANLI (10.11 00:44 TSİ): tek commit, kırk sekizinciden elli dördüncüye yedi paket (v2.548–v2.563); CI #709 yeşil (5 dk 49 sn); ssh dağıtım api+worker+web (imaj 139 sn, cryptography bağımlılığıyla); GÖÇLER v2550_kaynak_saatlik → v2556_bulut_kimlik → v2558_edge_kisit DB sahibiyle uygulandı, canlı head v2558; `.env`'e PVQ_KEK (openssl rand, ekrana basılmadı) + PVQ_KEK_ID=k1, kasa canlıda açık ({var: True, id: k1}); canlı bayt kıyası 77/77 birebir; healthz 200; api günlüğünde hata yok, worker açılış yakalaması «taze»; web parçalarında yeni kart metinleri (Santralim, Portföy). Yerel tam pytest 975 + ağır 86; web 103. Dört inceleme turu (ekranlar).

## Elli beşinci paket — v2.564 (10.11.2026): dış girdi takibi, başvuru metinleri ve sahip onayı (OAuth) yönlendirme ucu (mühürlendi: v2.565, 10.11)

**Kaynak.** v2.563 sonrası kalan her kalem dış girdiye bağlı (gerçek hesap/cihaz, sahip izni, üretici onayı, hukuki görüş). Kullanıcı «dış girdiye bağlı kalanları sırayla yapalım» dedi;
iki araştırma klasörü (Opus `PVQuant_Inverter_Pazar_Arastirmasi` A, Codex `PVQuant_Turkiye_Invertor_Entegrasyon_Arastirmasi` B) başvuru usulleri için yeniden tarandı: hiçbir sağlayıcı için
başvuru süresi, ücret ya da ticari onay formu belgelenmemiş; üreticilere hiçbir başvuru yapılmamış. Sungrow uygulama başvurusu redirect URL istediği için (A 08 §3.1 [K87]) tek kod kalemi:
sahip onayı yönlendirme ucu. Kaynaklar: A 08 §1.2.2–1.2.3 (SolarEdge OAuth: authorize yalnız `client_id`+`external_id`, geri dönüşte `code`/`site_id`/`external_id`, token `/v2/oauth2/token`,
`GET /sites` Bearer kabul etmez [K77][K353–K358]); A 08 §3.2–3.3 (Sungrow onay adresi kalıbı yalnız ikincil kaynakta [K366], token `/openapi/apiManage/token`, result_code 1/2/5 [K87]).

**(A) Dış girdi takibi ve başvuru metinleri (`docs/entegrasyon/`).** `DIS-GIRDI-TAKIBI.md`: 11 kalem (D1 KVKK görüşü, D2 FusionSolar NBI, D3 pilot yazılı izni, D4 Sungrow geliştirici+VIII(c),
D5 SolarEdge geliştirici/filo, D6 Growatt belirteci, D7 Solis anahtarı, D8 pilotlar P-1xx/P-7xx/P-104/P-SFTP/P-ENV, D9 ortaklıklar, D10 mTLS eşiği, D11 GoodWe/Deye/Sofar) — her biri için
kim verir · nereye · biz ne göndeririz · ne alırız · kod durumu · sıradaki adım, kaynak numaralarıyla; önerilen sıra (PVQuant'ın tek başına başlatabildikleri önce). `BASVURU-METINLERI.md`:
§1 kurulumcuya NBI isteği, §2 pilot yetki ve kapsam beyanı (sahip+O&M+OT; FC03/04 süzgeci, ayrı IEC 104 yuvası, test penceresi, tolerans %2/0,5 kWh, geri alma), §3 Sungrow ticari onay
e-postası (EN), §4 SolarEdge filo/ilişkili hesap, §5 Growatt belirteci (+ sabit IP 178.18.206.130), §6 Solis sahip adımları + kapsam beyanı, §7 ilk görüşme envanter soruları.
`OAUTH-UYGULAMA-KAYDI.md`: akış, kayıt adımları, ortam değişkenleri, doğrulanmamış varsayımlar.

**(B) Sahip onayı (OAuth) ucu (`services/bulut_oauth_service.py`, göç `v2564_bulut_oauth`).** `POST /v1/plants/{id}/bulut-kimlik/oauth/baslat`: iki onay + kasa + platform uygulaması
(ortam: `PVQ_SUNGROW_APPKEY/ACCESS_KEY/APP_ID`, `PVQ_SOLAREDGE_CLIENT_ID/SECRET`, `PVQ_OAUTH_GERI_DONUS_KOK`) → rastgele `state` (tabloda yalnız SHA-256 özeti; santral, sağlayıcı, bölge,
onaylar, aktör, 15 dk) ve sağlayıcı onay adresi (Sungrow `https://{auth_server}/?state=…#/authorized-app?cloudId=…&applicationId=…&redirectUrl=…`, bölge→cloudId tablosu; SolarEdge
`connect.solaredge.com/authorize?client_id=…&external_id=<state>`). Tanımlı değilse `uygulama_yok` (eksik değişken ADLARI; sahte başarı yok). `GET /v1/bulut/oauth/{saglayici}/geri-donus`
kimliksiz: state özetle bulunur ve AYNI UPDATE'te kullanılmış işaretlenir (yeniden oynatma kazanamaz; süresi dolan bulunmaz), sağlayıcı uyuşmazlığı/`error`/kod yokluğu ayrı durumlar;
kod sunucuda belirteçle değiştirilir (`Sungrow.token_degis`, `SolarEdgeOAuth.token_degis` — site_id yoksa kod harcanmaz), `bulut_kimlik_service.kaydet(..., secim_ertele=True)` ile sınama
(santral listesi) + zarf şifreli yazım; hesapta birden çok santral varsa kayıt `dis_kimlik` BOŞ yazılır («kaydedildi_secim_bekliyor»), sahip panelden seçer (PATCH), çekiş turu seçilmemiş
kaydı sağlayıcıya çağrı yapmadan `santral_secilmedi` ile atlar. Tarayıcı panele `/?bulut_oauth=<sağlayıcı>:<durum>#santralim/<santral>` ile döner — yalnız durum KODU (metin yok; adres
kökü ortamdan). Kod/belirteç/gizli hiçbir yanıt, günlük, denetim izi (`bulut_oauth_baslat`, `bulut_oauth_donus`) ya da `sonuc` özetine yazılmaz. Geri dönüş aynası: `son_sinama`
(`uc: oauth`) ve `bulut_kimlik` özeti. Yeni sağlayıcı kaydı `solaredge_oauth` (Bearer; `/sites/{id}` + `/energy`; 401'de refresh ve yeni çift atomik; `ETIKET_ALANI=site_id` — belirteç
maskelenmez; `ELLE_GIRIS=False`); `SolarEdge._get` tek GET noktası. Sicile `oauth`, `etiket_alani`, `elle_giris`; HENUZ_YOK'tan «SolarEdge site sahibi OAuth yolu» çıktı. compose/`.env.example`
yeni değişkenler (api+worker). Web: «Sahip onayına git (sağlayıcı sayfası)» (uygulama yapılandırılmışsa elle alanlar gizlenir), dönüşte koddan Türkçe mesaj ve sorgu adres çubuğundan
silinir, kayıt satırında «Sağlayıcıdaki santral» seçimi (son girişimin listesinden), yapılandırılmamışsa «platform uygulaması tanımlı değil» (ortam adı gösterilmez; yalnız onayla kurulan
yolda elle alan/sınama düğmesi yok). Sahte API: baslat/geri-donus/PATCH dis_kimlik, sağlayıcı listesi motordan; `~/.claude/launch.json` «pvquant-sahte-api».

**Göç.** `v2564_bulut_oauth` — `bulut_oauth_durum` (RLS; pvq_app SELECT/INSERT/UPDATE/DELETE). Canlıda DB sahibiyle (mühürde). Test DB'ye uygulandı.

**Kanıt.** tests/test_bulut_oauth_v2564.py 8 (sicil/özet gizli yok; başlatma kapıları ve adresler — state `#` öncesinde, özet 64 hex, düz state/gizli hiçbir çıktıda yok; state tek kullanım,
sağlayıcı uyuşmazlığı, error/kod yok/uygulama yok/belirteç hatası; Sungrow sahte sunucuyla belirteç değişimi → kasa: AT/RT/access_key düz metin ne yanıtta ne satırda ne özette, kasa.coz_json
birebir; çok santralda seçim ertelenir + çekiş bekçisi sağlayıcıya çağrı yapmaz; SolarEdge OAuth: 400 invalid_request, site_id yoksa kod harcanmaz, Bearer ve X-API-Key yok, 401 → refresh →
kimlik_yenile yeni çift, geri dönüşte external_id/site_id ve etiket site'tan; yönlendirme adresi süzgeci; API: onay_yok, yonlendir + state izde yok, kimliksiz geri dönüş 303 durum koduyla,
tamam yolunda kasa yazımı + ayna + izde kod/belirteç yok), tests/test_bulut_oauth_db_v2564.py 1 (DB: özet, tek kullanım, RLS, sonuç, süresi dolan). Eski 2 test sicil kümesine `solaredge_oauth`
eklendi. İlgili 29 pytest + dil bekçisi geçti; tam takım (test DB ile) 1070 geçti / 1 atlandı. Web tsc/build/lint 16 (eski)/0 hata/103 test. Sahte önizlemede uçtan uca: hedef bulut → Sungrow → onaylar → «Sahip onayına
git» → sahte sağlayıcı dönüşü 303 → panelde «hesapta birden çok santral var» mesajı, kayıt satırı «kimlik şifreli kayıtlı · santral seçilmedi», seçim → «sağlayıcı santralı 5001»
(`docs/tasarim/kanit-2026-11-10/oauth-donus-secim-bekliyor-800-2026-11-10.jpg`, `…/oauth-santral-secildi-800-2026-11-10.jpg`; depoya girmez); SolarEdge sahip onayı yapılandırılmamışken not ve alan/sınama düğmesi yok.

**Dürüstlük.** Sungrow onay adresi kalıbı ve cloudId eşlemesi yalnız ikincil kaynakta; SolarEdge `state`'in `external_id` ile dönmesi belgeye dayalı varsayım; iki akış da gerçek hesapla
görülmedi — kayıt yapılıp ilk gerçek dönüşte doğrulanır, aksi hâlde ekran «durum_yok/durum_gecersiz» ile durur, hiçbir şey saklanmaz.

**Kalanlar (dış girdi).** D1–D11 takip belgesinde; kod tarafında eksik yok. Mühürde: göç DB sahibiyle, `.env`'e platform değerleri (kayıt yapılınca; yoksa yol kapalı kalır).

## Elli altıncı paket — v2.565 (10.11.2026): bulut birim kıyası — «birim doğrulandı» kanıta bağlandı (mühürlendi: v2.565, 10.11)

**Kaynak.** Dış girdi takibi D2 (FusionSolar gerçek hesap) doğrulama protokolünün 3. adımı: ilk gerçek hesap gelince `inverter_power`'ın kWh mi kW mi olduğu portal «saatlik
üretim» dışa aktarımıyla kıyaslanacak (B kapısı G07/U04: «inverter_power alanını kW veya kWh diye yayınlama»; A 02 [K81/H6] belgeye göre kWh, B 16/05 yorumu sabitlemiyor).
v2.557'den beri «birim doğrulandı» elle bir kutuydu; gerçek hesap gelmeden önce bu kutunun kanıt istemesi gerekiyordu (sahte doğrulama yolu kapanır).

**(A) Birim kıyası (`services/bulut_birim_service.py`).** SAF `kiyas(ham, referans)`: `bulut_saatlik_ham` satırlarındaki her sayısal alan beş yorumla (kWh doğrudan · Wh÷1000 · MWh×1000 ·
kümülatif fark kWh · kümülatif fark Wh) referansla (CSV: zaman, kwh; okuyucu pilot kitiyle ortak `pilot_service.referans_csv_oku`) aynı saatlerde kıyaslanır; tolerans %2 ya da 0,5
kWh/saat, en az 24 ortak saat; alan başına en iyi yorum, oran, MAPE, toplam fark. Karar: `belge_uyumlu` (belgeye göre alan `enerji_kwh_belge` kWh yorumuyla uyumlu) · `belgeyle_celisiyor`
(başka alan/yorum uyumlu, belge yorumu değil — işaret konamaz, bulgu geliştiriciye) · `uyumsuz` · `yetersiz`. Not: iki kaynak aynı sağlayıcıdan; bu bir BİRİM/ANLAM doğrulamasıdır, ölçüm
doğruluğu kanıtı değildir (metinde). `degerlendir`: referans aralığındaki ham saatler → kıyas → özet `bulut_kimlik.birim_kanit` (jsonb; ham referans saklanmaz).
**(B) Kanıt kapısı.** `bulut_kimlik_service.isaret_izinli` (SAF) ve `ayarla(birim_dogrulandi=True)` → kanıt yoksa ya da belge yorumu uyumlu değilse `BirimKanitiYok` → API 422 (mesaj:
önce dışa aktarım yükle). Uç: `POST /v1/plants/{id}/bulut-kimlik/{saglayici}/birim-kiyas` (dosya ≤5 MB; kayıt yoksa 404; okunamazsa 422; denetim `bulut_birim_kiyas` — dosya adı, sonuç, n).
Göç: v2564'e sütun eklendi (`bulut_kimlik.birim_kanit`; mühürlenmemiş göç genişletildi, test DB'de geri alınıp yeniden uygulandı). Çekiş turu `santral_secilmedi` etiketi `DURUM_ETIKET`'te.
**(C) Ekran.** Kayıt satırında «Portal dışa aktarımıyla birim kıyası (CSV)» yükleme; sonuç rozeti (belge yorumu uyumlu / çelişiyor / uyumsuz / yetersiz), metin, zaman, dosya adı, alan
tablosu (alan, en iyi yorum, ortak saat, toleransta, sonuç); «birim doğrulandı» kutusu yalnız `belge_uyumlu` iken etkin, ipucu nedenini söyler. Sahte API: kıyas ucu, PATCH kapısı (422).

**Kanıt.** tests/test_bulut_birim_v2565.py 5 (kWh doğrudan → belge_uyumlu, alan etiketi ve ışınımın uyumsuz kalması; Wh ölçekli belge alanı → belgeyle_celisiyor + kümülatif Wh alanı
`kumulatif_wh` ile uyumlu; yetersiz/uyumsuz/boş; işaret kapısı üç hâl; değerlendirme özeti ham referans saklamaz; API: kanıtsız PATCH 422, yabancı sağlayıcı 404, bozuk dosya 422, kıyas
200 + kayıt + iz, kanıt sonrası PATCH 200). Eski DB testi kapıya uyarlandı (kanıtsız → BirimKanitiYok, kanıt → işaret). İlgili testler + dil bekçisi geçti; tam takım (test DB ile) 1074 geçti / 1 atlandı / 1 kırmızı (aşağıdaki saat bağımlı eski test). Web tsc/build/
lint 16 (eski)/0 hata/103. Sahte önizleme: kayıt → kanıtsız PATCH 422 → CSV yükleme → «belge yorumu uyumlu» rozeti + tablo → kutu etkin → işaret sunucuda ve ekranda
(`docs/tasarim/kanit-2026-11-10/birim-kiyas-belge-uyumlu-1280-2026-11-10.jpg`, `…/birim-dogrulandi-isaretli-1280-2026-11-10.png`; depoya girmez).

**Not (test takımı).** `tests/test_olay.py::test_saatlik_etki_istisna_ve_dahili` 10.11.2026 09:30 TSİ'den sonra kendiliğinden kırmızı: `olay_service` satır 217 açık/kapalı sınıflamasında
`datetime.now()` kullanıyor ve testin 10.11.2026 sabit olayı bugün «başlamış» sayılıyor — saat bağımlı eski test, bu paketle ilgisiz; sabit `simdi` ile düzeltme ayrı küçük iş.

**Kalanlar (dış girdi).** Gerçek NBI hesabıyla kıyasın kendisi (D2); kıyas belge yorumuyla çelişirse bağlayıcı belgesi düzeltilir (kod işi, bulgu gelince).

**İnceleme turu (10.11.2026, kullanıcı ekran görüntüsü üzerine; YERELDE).** Kart ve arkasındaki kod birlikte gözden geçirildi; kesin kusurlar düzeltildi, yargı gerektirenler kullanıcıya bırakıldı.
(1) **Üretimsiz saat sahte doğrulama veriyordu.** Tolerans oranı tüm ortak saatler üzerinden ölçülüyordu; gece saatleri (0 = 0) her yorumla uyuştuğu için yalnız gece içeren bir dosya
«belge yorumu uyumlu» çıkarabiliyordu. Artık oran yalnız üretim olan ortak saatlerde ölçülür; karar için en az 8 üretimli saat gerekir (`MIN_URETIMLI_SAAT`), yoksa `yetersiz`. Özet ve
tabloya «Üretimli saat» eklendi. (2) **Kapı açıkları.** Doğrulamayan yeni bir kıyas eski işareti kaldırır (API `isaret_kaldirildi`, ekranda «işaret kaldırıldı… gölge görünüme yazım durdu»);
sağlayıcı santrali (`dis_kimlik`) değişince kanıt ve işaret sıfırlanır. (3) **Sunum.** Yüzdeler Türkçe ondalıkla (%95,5); belge alanı satırı her zaman gösterilir; belge alanıyla birebir aynı
ham alan ikinci satır olarak tekrarlanmaz; hiç saat çekilmemişken CSV girişi kapalı ve nedeni yazılı; bulut hedefinde «cihaza» yerine «hesaba»; gereksinim başlığı yalnız bağlayıcısı olan beş
bulutu sayar. (4) **Kök neden: dosyalı yazma GET belleğini düşürmüyordu.** `web/src/api/client.ts` `getir` 60 sn bellek tutar; `gonder` her yazmada boşaltır, `dosyaGonder` ve elle yazılmış
yedi FormData yükleyicisi boşaltmıyordu. Sonuç: yükleme sonrası sayfanın kendi yenilemesi 60 sn boyunca eski yanıtı gösteriyordu (kıyas sonucu ekrana gelmiyordu). Aynı sınıf kusur mühürlü
akışlarda da vardı (SCADA yükleme, bildirilen KGÜP/şablon, saatlik EPYS, mutabakat, sayaç, IEC 104 nokta tablosu, pilot referansı); düzeltme sekiz noktada `bellekte.clear()` — etkisi yalnız
bir fazladan GET. Önizleme ucu (`/preview`) veri yazmadığı için belleğe dokunmaz. Bekçi: `web/test/panel/senkron.test.ts` «dosyalı yazma GET belleğini düşürür». (5) **Sahte API** gerçek
servisle eşlendi: imkânsız durum (çekiş yokken ham saat) kalktı, yüklenen dosya adı yankılanır, işaret kalkınca kaynak satırı etiketi de döner (gerçek servis etiketi her GET'te kayıttan
hesaplar; `veri_yolu_service` — kusur yalnız sahte API'deydi).
**Kanıt (inceleme).** `tests/test_bulut_birim_v2565.py` 8 (üretimsiz saat → yetersiz, üretimli saat sayımı, işaretin kalkması dâhil); tam takım 1077 geçti / 1 atlandı / 1 kırmızı (aynı saat
bağımlı eski test); web 104/104, tsc 0, build tamam, lint yalnız eski uyarılar. Önizleme 1280 px üç durum: A çekiş yok → CSV girişi kapalı; B belge uyumlu → tablo 48 / 22 / %95,5, kutu
işaretli, kaynak satırı «birim doğrulandı»; C üretimsiz dosya → «kıyas için yetersiz saat», kutu boş ve kapalı, uyarı metni, kaynak satırı «birim doğrulanmadı»
(`docs/tasarim/kanit-2026-11-10/inceleme-A-…`, `inceleme-B-…`, `inceleme-C-…`; depoya girmez).
**İncelemede kullanıcıya bırakılan dört satır (10.11, kullanıcı onayıyla düzeltildi; yerelde, mühür bekliyor).**
(a) **Durum etiketi çelişkisi.** Aynı kartta üst rozet santrale özgü durumu («veri alınıyor») gösterirken hedef seçicisi ve gereksinim başlığı tür düzeyindeki «bağlantı henüz kurulmadı»
etiketini taşıyordu (v2.544–v2.547'den beri). Arka uç değişmedi: tür etiketi (`DURUM_ETIKET`) ve santral durumu (`baglanti_durumu`) iki ayrı katman olarak kalır. Ön yüzde `yolDurumu`
yardımcısı, santralin beyan ettiği türde tür etiketi yerine tek durum kodunun etiketini gösterir; diğer türlerde tür etiketi kalır (`web/src/features/santralim/Santralim.tsx`). Rozet rengi
yalnız `veri_akisi` kodunda olumlu. (b) **Bayat iki cümle.** «düzenli veri çekişi başlamaz» → «düzenli veri çekişini kendiliğinden başlatmaz» (çekiş açıkken de doğru); kıyas metnindeki
««Birim doğrulandı» işaretlenebilir» → «Bu kanıt «birim doğrulandı» işareti için yeterlidir.» (kutu işaretliyken de doğru; `bulut_birim_service`). (c) **İpucu.** «bağlantı yazıldı, gerçek
hesapla doğrulanmadı» → «uygulamada destekleniyor; gerçek hesapla henüz doğrulanmadı» (`io/bulut/temel.py` `DURUM_ETIKETI`; cümle başında büyük harfle); `veri_yolu_service` notu «belgelerine
göre hazırlandı»; sağlayıcı listesi başlığı «hiçbiri gerçek hesapla henüz doğrulanmadı». Dürüstlük kaydı aynı kaldı, yalnız söyleyiş netleşti. (d) **Pilot metinlerinde yüzde.**
`pilot_service.referans_kiyas` metinleri Türkçe ondalıkla (`_tr`): «…tanesi toleransta (%96,6; saat başına en çok %2 ya da 0,5 kWh)». Karar mantığı, eşikler ve sayılar değişmedi.
Sahte API aynı metinlere eşlendi.
**Kanıt (düzeltme).** `tests/test_pilot_edge_v2560.py` uyumlu metni birebir, uyumsuz metninde nokta ondalık yok; `tests/test_bulut_birim_v2565.py` yeni cümle sabitlendi; dört dil bekçisiyle
birlikte hedefli 26 geçti; tam takım 1077 geçti / 1 atlandı / 1 kırmızı (aynı saat bağımlı eski test). Derleme ve tarayıcıyla aynı anda koşan bir turda iki test daha kırmızı düştü (`test_edge_db_v2561`, `test_rapor_tutarlilik` D18); tek başlarına ve yalnız koşan tam turda geçtiler, yük altında kararsızlık olarak not edildi. Web 104/104, tsc 0, build tamam, lint yalnız eski uyarılar. Önizleme 1280 px üç durum, metinler sayfadan okundu: A çekiş yok → rozet ve seçenek «bağlantı sınaması
başarılı, veri çekişi yok»; B ve C çekiş açık → rozet, seçenek ve gereksinim başlığı üçü de «veri alınıyor»; bağlanmamış türler (Modbus, IEC 104, OPC UA) «bağlantı henüz kurulmadı» olarak
kalır (`docs/tasarim/kanit-2026-11-10/duzeltme-A-…`, `duzeltme-B-…`, `duzeltme-C-…`; depoya girmez).

**İkinci inceleme turu (10.11, kullanıcının geniş ekran karesi üzerine; yerelde, mühür bekliyor).** Kare sahte API ile 2300 px genişlikte, açık temada, «kıyas için yetersiz saat»
durumunda yeniden üretildi; kart metin ve düzen olarak okundu, net kusurlar düzeltildi, karar gerektirenler kullanıcıya bırakıldı. Arka uç değişmedi.
(1) **Sınıf adı çakışması (canlıda da var).** v2.547'de kart içi bölüm başlığı `.alt-bolum` adıyla yazılmıştı; aynı ad `web/src/index.css` içinde daha önce bölüm kapsayıcısı olarak
tanımlıydı (Ayarlar «Hesap ve ekip» `Kurulus.tsx`, yönetim `sayfalar.tsx`). Sonuç: Ayarlar kartlarında gövde metni 12,5 px yarı kalın ve altta fazladan çizgi, «Veri kaynakları»
kartında başlıkların üstünde ikinci çizgi. Başlık kuralı `.kart-bolum` adına taşındı, üç başlık bu sınıfı kullanır; kapsayıcı eski hâline döndü
(ölçüm: yazı kalınlığı 400, üst boşluk 20 px, üst çizgi 1 px, alt çizgi 0). (2) **Form satırı.** Etiket aralığı 8/12 px; sağlayıcı notu tam satır. (3) **İki tablo.** Kıyas kanıtı
tablosu `table.veri.dar` (2300 px ekranda 772 px), ham saat tablosu «Son çekilen ham saatler» başlığıyla ayrıldı. (4) **Yaş metni.** 24 saatten genç veri «(0 gün önce)» yerine
«(N saat önce)», bir saatten genç veri «(1 saatten az önce)». (5) **Satır boyu.** Açıklama satırları en çok 90ch (ölçüm 766 px). (6) **Dar ekran.** 390 px'te belge 533 px
genişliğe taşıyordu (rozetler tek satır, kanıt bloğu `min-width: auto`, seçim ve dosya girdisi kendi genişliğinde). Izgara `minmax(0, 1fr)`, rozet sarar, girdiler `maxWidth: 100%`,
tablolar kendi kaydırma kabında; 390 ve 320 px'te kart içerik kutusunu aşan öğe yok.
**Kullanıcıya bırakılanlar.** Bulut adımlarına «birim doğrulanmadı» bekleyen adımı; birim doğrulanmamışken kaynak satırındaki «veri» rozetinin yeşil olması; kimlik kayıtlıyken boş
kimlik alanları ve işaretsiz saklama onayı; «yetersiz» sonucun yanında «%100,0»; tür düzeyindeki «gerçek hesapla doğrulanmadı» cümlelerinin başarılı çekişle yan yana durması;
müşteri metninde «gölge görünüm» ve «şifreli kasada» deyişleri; çok geniş ekranda panel için azami içerik genişliği. Kapsam dışı gözlem: 320 px'te sayfa başka kartlar yüzünden
382 px («Sensörler ve kalibrasyon» tür seçimi, «Pilot kapıları» dosya girdisi, «Aylık üretim» tablosu).
**Kanıt (ikinci inceleme).** Web 104/104, tsc 0, build tamam, lint yalnız eski iki uyarı. Önce ve sonra kareleri `docs/tasarim/kanit-2026-11-10/inceleme2-…` (2300, 1280, 390, 320 px
ve Ayarlar «Hesap ve ekip» 1280 px; depoya girmez). Kalıp `emsaller.md`'ye yazıldı.

**İkinci incelemede kullanıcıya bırakılanlar uygulandı (10.11, «önerilenlerin hepsi»; yerelde, mühür bekliyor).** Altı madde uygulandı, yedincisi (çok geniş ekranda azami içerik
genişliği) somut öneri verilmediği için açık kaldı. (1) **Bekleyen «birim» adımı.** `veri_yolu_service.asamalar`: bulutta kimlik kayıtlıysa «veri alınıyor»dan sonra ayrı adım,
«birim doğrulanmadı» ya da «birim doğrulandı»; kimlik yokken adım yok (eski kod dizisi `secildi, ayar, sinama, kimlik, akis` aynı kalır). (2) **«Veri» rozeti.** Bulut satırı üç alan
taşır (`saglayici`, `birim_dogrulandi`, `son_cekis_ok`); veri güncel olsa da birim doğrulanmadıysa rozet nötr. (3) **Kayıtlı kimlik.** Kimlik kayıtlıyken bölge seçimi, kimlik
alanları, saklama onayı, «Sına ve şifreli kaydet» ve «Bulut bağlantısını sına» gösterilmez; kayıt satırındaki «Kimliği değiştir» açar, «Değiştirmekten vazgeç» kapatır ve girilenleri
temizler. Onay kutusu hiçbir durumda önceden işaretlenmez; kayıtlı kimlik yenisi kaydedilene kadar kullanılır. (4) **Yetersiz kıyas.** «Toleransta» sütunu yetersiz sonuçta tire.
(5) **Hesap durumu.** Yeni saf işlev `hesap_durumu`: son çekiş başarılıysa `bulut.hesap_durumu` döner («bu hesapta çekiş başarılı; birim doğrulaması bekliyor» ya da «…; birim
doğrulandı»). Ön yüz bunu üç yerde tür etiketinin yerine koyar: kart açıklaması, sağlayıcı notu, yetenek rozeti. Çekiş yoksa ya da son tur başarısızsa genel «gerçek hesapla henüz
doğrulanmadı» kaydı aynen kalır. «Teknik ayrıntılar» altındaki tür düzeyi notlar değişmedi. (6) **İç terimler.** Müşteri metninde «gölge görünüm» yerine kartın adı «kaynak kıyası»
(etiket, satır rozeti, birim notları, kayıt yanıtı, Modbus özeti, `kaynak_secim_service` metni, aylık rapor niteliği); «şifreli kasada» yerine «şifreli saklanır». İlk öneri
«üretim serisine yazılmaz» idi; birim doğrulanınca saatler üretim serisine değil kaynak kıyasına yazıldığı için olumlu cümlede yanlış olurdu, bu yüzden «kaynak kıyası» seçildi.
İş günlüğündeki «gölge N» sayaçları ve kod içi adlar değişmedi.
**Kanıt (karar maddeleri).** `tests/test_bulut_birim_v2565.py::test_birim_adimi_ve_hesap_durumu` (adım sırası, etiketler, hesap durumu üç durumu, iç terim yokluğu). Tam takım test
veritabanıyla 1077 geçti / 1 atlandı / 2 kırmızı; ikisi de sabit tarihli, zamana bağlı eski testler ve bu değişiklikle ilgisiz: `test_olay.py::test_saatlik_etki_istisna_ve_dahili`
(önceden biliniyordu) ve `test_asama1_db_v2550.py::test_toplama_tam_kismi_revizyon_ve_golge` (`canli_ornekleme_service.durum` `now() − 24 saat` sayar, testin örnekleri 9 Kas 07:45 UTC;
10 Kas 07:45 UTC'den sonra kırmızıya döndü). İkisi de CI'da kırmızı düşer; mühürden önce düzeltilmeleri gerekir, onay bekliyor. Web 104/104, tsc 0, build tamam, lint yalnız eski iki
uyarı. Önizleme: kimlik kapalı ve açık durumları 320, 390, 1280 ve 2300 px'te kart içinde taşma yok; kimliksiz durumda alanlar açık ve genel kayıt yerinde; birim doğrulanınca adım,
rozet ve hesap durumu olumluya döner (`docs/tasarim/kanit-2026-11-10/karar-…`; depoya girmez). Kalıp `emsaller.md`'ye yazıldı. Sahte API aynı kurallara eşlendi.

**Zamana bağlı iki test düzeltildi (10.11, kullanıcı onayıyla; yalnız test dosyaları, yerelde).** (1) `tests/test_olay.py::test_saatlik_etki_istisna_ve_dahili`: kayıtlar sabit 10 Kasım
tarihli, evre ve durum ise gerçek saate bağlıydı; 10 Kasım gelince «planlı» sayısı değişti. Test artık olay hizmetinin saatini 10 Kasım 08:00'e sabitliyor (`_saat_sabitle`; yeni
bağımlılık yok, `isinstance` denetimleri gerçek tarih nesnelerinde de doğru kalır). Tarihler sabit bırakıldı, çünkü «2026 olayı yürürlükten önce» doğrulaması yıla bağlı.
(2) `tests/test_asama1_db_v2550.py::test_toplama_tam_kismi_revizyon_ve_golge`: örnekler sabit 9 Kasım tarihliydi, hizmet «son 24 saat»i veritabanı saatiyle sayıyor. Başlangıç artık
şimdiki saatin altı saat öncesi; sabit tarih dizgesi de buna göre üretiliyor. Dokuz farklı saat kaymasıyla (3–21 saat; gece yarısı geçişleri dâhil) denendi, hepsi geçti.
Ürün kodu değişmedi. **Kanıt.** Tam takım test veritabanıyla 1079 geçti / 1 atlandı / 0 kırmızı (6 dk 48 sn).

**Mühür.** v2.565 cc06a12 CANLI (10.11 12:04 TSİ): tek commit, elli beşinci ve elli altıncı paket (v2.564–v2.565) ile iki inceleme turu, altı karar maddesi ve iki test düzeltmesi; CI #711 yeşil (6 dk 8 sn); ssh dağıtım api+worker+web (worker penceresi dışında); GÖÇ v2558_edge_kisit → v2564_bulut_oauth DB sahibiyle uygulandı, canlı head v2564 (`bulut_oauth_durum` satır güvenliği açık ve zorunlu, `bulut_kimlik.birim_kanit` sütunu var); canlı bayt kıyası 141/141 birebir; healthz 200; kasa açık ({var: True, id: k1}); sahip onayı geri dönüş ucu durum değeri olmadan 303 ile yalnız pvquant.com köküne döner; api ve worker günlüğünde hata izi yok. Sahip onayı ortam değerleri girilmedi: yol canlıda kapalı, sağlayıcı kayıtları yapılınca açılır. Yerel tam pytest 1079 / 1 atlandı; web 104.

**Mühür sonrası bağımsız inceleme (10.11, v2.565 farkı üzerinde; yerelde, mühür bekliyor).** Sekiz bulgu, sekizi de uygulandı. (1) Sahip onayı dönüşünde sağlayıcı
«cancel» hatası: durum ve açıklama aynı koşuldan türetilir (ikisi de «onay verilmedi»). (2) Tek kullanımlık durum değeri artık sağlayıcı süzgeciyle aranır
(`_bul_ve_isaretle_db(…, saglayici)`); yanlış sağlayıcı yoluna gelen dönüş geçerli değeri tüketmez (DB testinde sabitlendi). (3) SolarEdge OAuth istemcisinde
oturum bayrağı kaldırıldı; 401'de her çağrıda en çok bir yenileme yapılır, ikinci dolma da yenilenir. (4) Müşteri metninde kalan «gölge» ifadeleri temizlendi
(kıyas mesajı «Saatler kaynak kıyasına yazılmıyor», pilot «yalnız tam ölçülmüş saatler», «kaynak kıyasında olmayan N», `pilot_service` not metni). (5) Türkçe ondalık
yardımcısı tek yerde (`pilot_service._tr`). (6) Kayıt/sahip onayı durum satırları tek öğe (`bkDurumSatiri`). (7) Kıyas mesajı sağlayıcıya bağlı; yalnız ilgili
kayıt satırında görünür. (8) `db.sistem_baglami` kuralı güncellendi: özetle tek satır araması yapan kimliksiz uçlar (toplayıcı anahtarı, OAuth durumu) adlandırıldı,
sonrası kiracı bağlamı. Ayrıca dokuz paket başlığındaki bayat «YERELDE; mühürlenmedi» etiketi «mühürlendi: v2.563/v2.565» oldu.

**Mühür.** v2.566 a27b818 CANLI (10.11 12:58 TSİ): v2.565 incelemesinin sekiz düzeltmesi ve defter başlıkları; CI #713 yeşil (4 dk 5 sn); ssh dağıtım api+web (worker yeniden yaratılmadı, 53 dk'dır ayakta); göç yok, canlı baş v2564; canlı bayt kıyası 141/141 birebir; healthz 200; geri dönüş ucu durum değeri olmadan 303 ile köke dönüyor; api günlüğünde hata yok. Yerel tam pytest 1079 / 1 atlandı; web 104.

## Elli yedinci paket — v2.567 (10.11.2026): Faz 0 teknik doğrulama denetimi ve dört düşük riskli düzeltme

**Kaynak.** Kullanıcının ChatGPT'den aldığı «Faz 0 — teknik envanter, güvenilirlik ve sistem doğrulaması» brifi. Yedi paralel inceleme (envanter, araştırma–kod karşılaştırması,
veri/zaman, tahmin/kalibrasyon, mevzuat/DSG, güvenlik/izolasyon, panel/pilot) ve gerçek santral zinciri; çıktı `~/Desktop/PVQuant_Faz0_Teknik_Dogrulama/` (on belge + bulgu
matrisi + ek + kanıt; depoya girmez). Canlı veritabanı okunmadı (izin yok); canlıya dair her iddia dış teyit etiketli. 165 bulgu, CRITICAL yok, 6 HIGH (TK-05 karne 0–24
kovasında çoklu koşu çift sayımı, TK-03 hibrit holdout sızıntısı, TK-02 kalibrasyon KPI örneklem içi, GV-01 TOTP/webhook sırları düz metin, VZ-05 rapor gün sınırı UTC, VZ-07
PVDAQ sabit UTC−7 yükleme dilimi); hepsi ONAY GEREKLİ, uygulanmadı. ChatGPT hipotezlerinden ikisi CONTRADICTED (örnek kip PVDAQ değil ve canlıda kapalı; fiziksel saat ile
piyasa saati ayrımı kodda doğru), «%3,1 MAPE» depoda yok (UNVERIFIED). Gerçek santral: Solentegre GES (EPİAŞ 2108) UEVM 2025 (8760 saat, 12.563,9 MWh) test veritabanına içe
alındı; birim/zaman/provenans/veri yolu/aylık rapor adımları geçti, tahmin ayağı engelli → Faz 0 kararı TAMAMLANMADI, Faz 1 ŞARTLI HAZIR.
**Uygulanan düzeltmeler (düşük risk, çekirdeğe dokunmaz).** (1) `aylik_rapor_service` «Veri kaynağı niteliği» penceresi: `bit` HARİÇ sınırken +1 gün ekleniyordu, 744 saatlik
ayda 768 yazıyordu (zincirde bulundu; 744'e indi; `tests/test_aylik_rapor.py` yeni sabit). (2) `ingest_service`: dosya yüklemesi `format_json`'a açık `kaynak: scada_dosya`
yazar (önceden COALESCE ile çıkarılıyordu; okuyucular değişmedi). (3) Müşteri metni: «Gölge görünüm:» → «Kaynak kıyası:» (`kaynak_secim_service`), «koşu yok» → «henüz tahmin
üretilmedi» (`nowcast_service`, `paylasim_service`; `tests/test_paylasim.py` güncellendi). (4) `docs/entegrasyon/DIS-GIRDI-TAKIBI.md` D4/D5 bayat durum satırları.
**Kanıt.** pytest tam takım test veritabanıyla 1079 geçti / 1 atlandı / 0 kırmızı (düzeltme öncesi ve sonrası); hedefli 36; web 104/104, tsc 0 (web değişmedi). Göç yok; dağıtımda
api+worker (aylık rapor gönderimi ve nowcast worker'da), web değişmedi.

**Mühür.** v2.567 d9213d0 CANLI (10.11 18:08 TSİ): Faz 0 denetiminin dört düşük riskli düzeltmesi; CI #715 yeşil (6 dk 8 sn); ssh dağıtım api+worker (web değişmedi, imajı yenilenmedi; worker penceresi dışında, açılış yakalaması «taze»); göç yok, canlı baş v2564; healthz 200; api günlüğünde hata yok. Denetim çıktısı `~/Desktop/PVQuant_Faz0_Teknik_Dogrulama/` (depoya girmez). Test veritabanında Faz 0 kiracısı (Solentegre) duruyor.

## Elli sekizinci paket — v2.568 (10.11.2026): karne kuralı tek yerde — koşu seçimi, gün içi ve program kovaları, tek gündüz eşiği (Faz 0 onay paketi 1)

**Kaynak.** Faz 0 denetimi TK-05/06/07/12 ve TK-09 (`~/Desktop/PVQuant_Faz0_Teknik_Dogrulama/05_…`, öneri `onay/karne-tanimi-onerisi.md`); kullanıcı onayı 10.11.
Kusur: `gece_skill` koşu süzgeci ve saat tekilleştirmesi olmadan eşliyordu; sabah + iki gün içi koşu + önceki günün koşusu aynı saate düşüyor, kısa ufuklu satırlar baskın
çıkıp WMAPE'yi iyimserleştiriyordu (saf yeniden üretim %20 → %11). Üç yüzey üç farklı kural kullanıyordu (karne tekilleştirmez, rapor en kısa ufuk, Doğruluk ortalama).
**(A) `services/karne_kurali.py` (SAF, tek kural).** Geriye bakışlı koşular (`model='backtest'`, `meteo_source='open-meteo-arsiv'`) dışarıda; gün içi (`etiket='gun_ici'`)
koşular ana kovalardan çıkıp `gun_ici` kovasına (saat başına en son revizyon); ana kovalarda (saat, kova) başına en erken yayımlanan koşu; `program` kovası = teslim günü
(İstanbul) için D-1 KGÜP kesimi (2025'ten 15:30, öncesi 16:00; `kgup_kesim`) öncesi son koşu; `GUNDUZ_ORAN=0.02` tek sabit; `kova_etiketle` metin etiket döner.
**(B) Bağlantılar.** `apps/worker/main.py`: `gece_skill` SQL'ine model/meteo_source/etiket, `karne_satirlari` + `gunduz_maskesi`; `rapor_alanlari` aynı seçim (en kısa ufuk
kuralı kalktı). `accuracy_service` iki işlev: seçim + eşik. `konformal_service`, `backtest_service`: eşik. `skill_daily.horizon_bucket` artık `gun_ici` ve `program` da taşır
(metin sütun; göç yok). `/v1/plants/{id}/skill?bucket=program` zaten çalışır; istemci `api.karne` program kovasını da çeker (`Karne.program`); Doğruluk sayfasında
«Program doğruluğu» ölçüt grubu (WMAPE, gün, referansa göre iyileşme; yoksa «—»), ilk KPI etiketi «gün başı tahmini». Yöntem metni: «sabah erken saatte (05:00 TSİ)
üretilir… gün içi güncellemeler ayrı sayılır; her saat için karneye yalnızca en erken yayımlanan tahmin girer».
**(C) Yeniden hesap.** `scripts/karne_yeniden_hesapla.py`: `skill_daily_eski_<tarih>` yedeği + her santral için arşivin başından `gece_skill`; DB sahibiyle koşulur.
`docs/VERI-SOZLUGU-KARNE.md`: kural, sütunlar (`mape` = WMAPE; ad değişmedi, göç yok), değişmeyen kalibrasyon eşikleri (TK-12 ayrı paket).
**Kanıt.** `tests/test_karne_kurali.py` 6 test (çift sayım %11 → %20, en erken koşu, geriye bakışlı dışlama, sütun yoksa eski davranış, program kesimi 15:30/16:00, bütün
kovalar + eşik); mevcut karne testleri (kova, nrel hakem, sfa, olasılıksal, eşik, kapsama, dogrulama_v2532, api_skill) yeşil; web tsc 0, 104/104, lint 0 hata, build.
Tam takım test veritabanıyla 1085 geçti / 1 atlandı / 0 kırmızı (ilk koşuda `backtest_service` eşik içe aktarması eksikti, iki test NameError; düzeltildi; `test_edge_db_v2561` yük altında bir kez kırmızı, tek başına ve ikinci tam koşuda geçti). Yeniden hesap betiği test veritabanında prova edildi (yedek tablo alındı; tahmin arşivi olmayan santral atlandı). Canlıda dağıtım sonrası: yeniden hesap betiği DB sahibiyle (yedek alır), 30 gün eski/yeni kıyası, Hakkında'ya tarihli not (sonraki paket).

**Mühür.** v2.568 11494f7 CANLI (10.11 19:13 TSİ): CI #717 yeşil (7 dk 50 sn); ssh dağıtım api+worker+web (worker penceresi dışında, açılış yakalaması «taze»); göç yok;
canlı bayt kıyası 141/141; healthz 200; api günlüğünde hata yok. **Canlıda yeniden hesap** (`scripts/karne_yeniden_hesapla.py`, DB sahibiyle): yedek `skill_daily_eski_20261110`
449 satır; üç EPİAŞ santralı 42 günlük arşivden yeni kuralla yeniden yazıldı (kova başına 32–40 gün; `gun_ici` ve `program` kovaları doldu); PVDAQ Golden 33 ve Format Lab'da
gerçekleşenle eşleşen koşu olmadığından karne satırı yok (önceden de yoktu). **Eski/yeni kıyası (son 30 gün, üç santral, günlük WMAPE ortalaması):** 0-24 %30,4 → %30,0;
24-72 %43,8 → %51,0; 72-168 %54,5 → %54,9; 168+ %59,7 → %73,4; yeni kovalar gun_ici %28,8, program %32,5. Yorum: en erken koşu kuralı uzak kovaları beklendiği gibi
kötüleştirdi (daha dürüst); 0-24 neredeyse değişmedi (bu santrallarda gün içi koşular ana kovayı az etkiliyormuş); program doğruluğu (%32,5) gün başı tahmininden (%30,0)
biraz kötü, KGÜP ufkunun bedeli. Kalan: Doğruluk sayfasında gün içi satırı, Hakkında'ya tarihli not, `karne_dustu` alarmı için yeniden hesap gecesi gözlemi (11.11 sabahı).

## Elli dokuzuncu paket — v2.569 (10.11.2026): karne paketinin kalanı — Doğruluk'ta gün içi satırı, Hakkında'ya tarihli not

`api.karne` `gun_ici` kovasını da çeker (`Karne.gun_ici`); Doğruluk sayfasında «Gün içi güncelleme» ölçüt grubu (12:30 ve 18:30 TSİ revizyonları, WMAPE ve gün; yoksa «—»).
Hakkında › «Veri kaynakları ve lisanslar» kartına yöntem metninin altına tarihli not: karne tanımı 10.11.2026'da düzeltildi, en erken tahmin sınava girer, gün içi ve
program ayrı, geçmiş yeni tanımla yeniden hesaplandı, önceki değerler yedekte. Yalnız web; arka uç değişmedi. Not: `skill_daily`'de santral başına 9 satırlık «d1» kovası
yalnız worker yazdığı hâlde bugünkü kodda üretilmiyor; 11.10 geri alınan v2.396–424 («D-1 kesiti») döneminden kalma eski satırlar olduğu düşünülüyor, araştırılmadı.

**Mühür.** v2.569 408f4d8 CANLI (10.11 19:30 TSİ): CI #719 yeşil (7 dk 57 sn); ssh dağıtım yalnız web (api ve worker dokunulmadı); göç yok; healthz 200, ana sayfa 200; canlı bayt kıyası 141/141. Karne paketi (v2.568 + v2.569) böylece tamamlandı; kalan yalnız 11.11 sabahı `karne_dustu` alarmı gözlemi.

## Altmışıncı paket — v2.570 (10.11.2026): sır kasası ve TOTP tekrar koruması (Faz 0 onay paketi 2, GV-01/GV-02)

**Kaynak.** Faz 0 denetimi 07 belgesi GV-01 (TOTP ve webhook sırları düz metin) ve GV-02 (TOTP tekrar koruması yok); öneri `onay/sir-kasasi-totp-onerisi.md`, kullanıcı onayı 10.11.
**(A) `guvenlik/sir.py` (tek yer).** `sakla(duz, aad)`: KEK varsa kasa zarfı (JSON: kek_id, dek_sarili b64, sifreli b64, surum) ve düz sütun NULL; KEK yoksa bugünkü düz
davranış. `oku(zarf, duz, aad)`: geçiş dönemi çift okuma. `totp_dogrula(sir, kod, son_adim)`: ±1 adımda eşleşen adımı bulur, son kabul edilenden yeni değilse reddeder,
kabulde adımı döner; servisler adımı atomik yazar (`UPDATE … WHERE totp_son_adim IS NULL OR totp_son_adim < :adim`, 0 satır = eşzamanlı tekrar → red).
AAD bağları users:<id>:totp, platform:<id>:totp, webhooks:<tenant>:<id>.
**(B) Göç `v2570_sir_kasasi`** (geri alınabilir): users ve platform_kullanicilar `totp_zarf JSONB`, `totp_son_adim BIGINT`; webhooks `secret_zarf JSONB`. Düz sütunlar
geçiş döneminde kalır (sonraki sürümde ayrı onayla düşer). **(C) Bağlantılar.** `iki_adim_service` (baslat, dogrula_ve_ac, giris_dogrula, kapat, yonetici_sifirla),
`platform_service` (giris, yeniden_dogrula, iki_adim_baslat, iki_adim_dogrula, operator_guncelle sıfırlama), `webhook_service` (oluşturma zarf + kimlik istemcide
üretilir, gönderimde çift okuma). Eski `pyotp.TOTP(...).verify(valid_window=1)` çağrısı kalmadı (test sabitlendi). **(D) `scripts/sirlari_kasaya_tasi.py`**: düz → zarf
(ilk kaydı çözerek doğrular), `--geri` zarf → düz, `--kuru` yalnız sayar; DB sahibiyle ve PVQ_KEK ile koşulur.
**Kanıt.** `tests/test_sir_v2570.py` (zarf gidiş-dönüş ve bağlam, KEK yokken düz, tekrar reddi ve pencere, servislerin tek yardımcıyı kullanması);
`test_platform_db::test_uctan_uca` sahte saatle adım adım (aynı kodla ikinci giriş artık doğru olarak reddediliyor); hedefli 41 geçti. Göç test DB'de uygulandı. Tam takım 1089 geçti / 1 atlandı / 0 kırmızı. Dönüşüm betiği test DB'de gerçek kayıtla ileri ve geri prova edildi (users 1, webhooks 1:
zarflandı → çözüldü → düz metne döndü); ilk provada `webhooks.secret NOT NULL` kısıtı dönüşümü ve KEK'li yeni webhook oluşturmayı kırıyordu, göçe `DROP NOT NULL`
eklendi (downgrade boş dizeyle geri koyar). Canlıya alma: önce kod + göç (çift okuma, kimse etkilenmez), sonra dönüşüm betiği DB sahibiyle, sonra platform
girişiyle doğrulama; eski pg_dump yedekleri düz sırları taşımaya devam eder (öneri §2.5).
