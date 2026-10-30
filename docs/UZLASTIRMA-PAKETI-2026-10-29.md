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
