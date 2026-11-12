# Tahmin arşivi sözleşmesi (Faz 4 F4-B, v2.597)

Tarih: 11 Kasım 2026. Göç: `alembic/versions/v2597_arsiv_kunye.py`. Testler: `tests/test_arsiv_kunye_v2597.py` (DB),
`tests/test_karne_kurali*.py`, `tests/test_cekirdek_siniri.py` (yazıcı bekçisi). Çekirdek sınırı: `docs/CEKIRDEK-SINIRI.md`.

## İlke

Tahmin arşivi (`forecast_runs` + `forecast_values`) yalnız-ekleme bir kayıttır. Bir koşu yayımlandığı anda ne üretildiyse o
kalır; sonradan düzeltme, silme, «yeniden kurma» yoktur. Düzeltme gerekirse YENİ koşu yazılır ve etiketi bunu söyler.
Bu ilke v2.176'dan beri kod disipliniydi; v2.597'den itibaren şemada zorlanır.

## Koşu künyesi (`forecast_runs`)

| Sütun | Anlam | Kaynak |
|---|---|---|
| `run_at` | koşu anı (`tahmin_uret` `simdi`; ufuk ve konformal kovası aynı anla hesaplanır) | `arsive_yaz` |
| `mode` / `model` | A/B/C; `barhdadi_bennis` / `hybrid_residual` (hibrit koşmadıysa C yazılmaz, bkz. CEKIRDEK-SINIRI M2) | `tahmin_uret` |
| `etiket` | sözlük (aşağıda); NOT NULL, varsayılan `yayin` | çağıran |
| `meteo_source`, `nwp_kosu_zamani`, `nwp_bilesenler_json` | NWP kaynağı, yayın zamanı, bileşen → koşu zamanı (`meteo_kosu_kunye`'den; göç öncesi koşularda NULL) | `MeteoData` |
| `kalibrasyon_id`, `ml_model_id`, `artefakt_sha16` | aktif kalibrasyon, yüklenen ML kaydı, artefakt dosyasının SHA-256 ilk 16 hex'i | `girdileri_topla` |
| `spec_json` | kullanılan PlantSpec anlık görüntüsü (kalibre katsayılar işlenmiş) | `plant_spec_kur` |
| `konformal_q_json`, `sapma_oran_json`, `ufuk_sigma_json` | uygulanan katman ayarları — bant arşivden yeniden kurulabilir | katman `ayar_getir` |
| `ensemble_kosu_zamani` | bant GEFS üyelerinden geldiyse üye koşusu | `uyeler_getir` |
| `ufuk_saat` | **ileri saat sayısı** (son tahmin saati − run_at). v2.597 öncesi bu sütun satır sayısıydı; göç eski değeri `satir_sayisi`'na taşıdı ve `ufuk_saat`'i değerlerden yeniden kurdu | `arsive_yaz` |
| `satir_sayisi`, `cozunurluk_dk` | yazılan değer satırı sayısı; çözünürlük (arşiv saatlik = 60) | `arsive_yaz` |
| `veri_kalitesi_json` | `meteo_yas_saat`, `kalibrasyon_yas_gun`, `konformal_yas_gun`, `ensemble_yas_saat`, `eksik_saat`, `bant_kaynagi`, `sapma_aktif`, `geri_dusus` — bilinmeyen NULL | `arsive_yaz` |
| `meteo_ozet_json` | eski özet (kaynak, bant, sapma özeti, günler, `geri_dusus`) — geriye uyum | `arsive_yaz` |

### Etiket sözlüğü (`forecast_runs.etiket` CHECK)

| Etiket | Anlam | Yayımlanmış sayılır mı | Karne |
|---|---|---|---|
| `yayin` | gece/program koşusu (eski NULL) | evet | ana kovalar + program |
| `gun_ici` | gün içi revizyon (09:30 / 15:30 UTC) | evet | `gun_ici` kovası + program |
| `elle` | panelden tetiklenen koşu | evet (son koşu, program) | yalnız program |
| `backtest` | geçmiş tarihli koşu (analiz meteosu; `scripts/dev_skill_backtest.py`, eski `model='backtest'` / `meteo_source='open-meteo-arsiv'`) | hayır | hiç |
| `simulasyon` | geriye dönük simülasyon (`scripts/faz1_solentegre_simulasyon.py`) | hayır | hiç |
| `sentetik` | sentetik tohum (`scripts/seed_sentetik.py`, `meteo_source='sentetik_tohum'`) | hayır | hiç |
| `demo` | gösterim verisi | hayır | hiç |
| `yeniden_kurma` | arşivden yeniden kurulan bant/koşu (araştırma) | hayır | hiç |

Göç geri doldurması: `sentetik_tohum` → `sentetik`; `model='backtest'` ya da `open-meteo-arsiv` → `backtest`; NULL → `yayin`.

## Yayımlanmış koşu süzgeci — tek yer

`karne_kurali.yayin_kosu_sql(alias, elle_dahil=True)` SQL parçası; pandas tarafı `karne_kurali.geriye_bakisli(df)` (aynı küme:
etiket ∪ eski damgalar). Kullananlar (v2.597): `forecast_service.son_kosu` ve `yayimlanmis_kosu`, dış API `_son_kosu_kimligi`,
`kgup_service.kaynak_kosu_df`, `dengesizlik_service.program_df`, worker günlük beklenti geri doldurma, `guvenilirlik`, `hijyen` (2),
`kayip_ayrisimi`, `konformal.gecmis_band_df`, `kullanilabilirlik`, `performans`, `saglik`, `sapma`, `ufuk`, `uzlastirma`,
`finansal_etki` (fizik beklentisi), `report_service` (kimlik + evrim), `portfoy_service` (2), `ozet_service`.
Karne okuyucuları (worker `gece_skill`, `accuracy_service`, `bagimsiz_dogrulama`) satırları `karne_kurali`'ye verir; süzgeç oradadır.
Süzgeçsiz kalanlar bilinçli: `kullanim_service` (aktivite sayacı), `platform_service` / `sistem_service` (izleme: son koşu zamanı),
`damga_service` (değişim damgası), `forecast_service.kosu_gecmisi` (geçmiş listesi etiketi gösterir).

## Program seçimi — tek kaynak

Teslim günü D için D-1 kesimi `ext/turkiye/kurallar.kgup_kesim(gun)` (Python) ve `kgup_kesim_sql(gun_ifadesi)` (SQL) aynı kural
tablosundan üretilir. `program_df` (SQL), `kgup_service.kaynak_kosu_df` (SQL + Python) ve `karne_kurali.program_kovasi` (pandas)
aynı koşuyu seçer; üçlü denklik testi `tests/test_arsiv_kunye_v2597.py::test_program_secimi_uclu_denklik`.

## Değişmezlik ve bakım bağlamı

- `forecast_runs` / `forecast_values`: BEFORE UPDATE OR DELETE tetikleyicisi `pvq_arsiv_degismez()` → hata
  (`integrity_constraint_violation`), ancak `current_setting('app.arsiv_bakim', true) = '1'` ise geçer.
- `pvq_api` ve `pvq_app` rollerinden UPDATE/DELETE yetkisi kaldırıldı (uygulama kodu zaten yazmıyordu).
- Bakım bağlamı: `pvquant.db.bakim_baglami()` (sahip rolü; bayrağı işlem düzeyinde basar). Kullananlar: test fixture temizlikleri
  (10 dosya), `scripts/seed_sentetik.py` (oturum düzeyi bayrak), gelecek göçler. Üretim kodu çağırmaz; bekçi: `test_cekirdek_siniri`.
- `scripts/seed_sentetik.py` (bulgu M3): yalnız kendi `sentetik` izini siler; gerçek koşulara dokunmaz (sayar, bildirir);
  `--santral <ad>` ve `--onay` zorunlu.

## Yardımcı tablolar

- `konformal_ayar_gecmis` (RLS, yalnız ekleme): her gece q̂ hesabı bir satır ekler (`kaynak='gece'`); göç mevcut ayarı
  `goc_v2597` kaynağıyla ilk satır yaptı. `konformal_ayar` güncel tek satır olarak kalır.
- `meteo_kosu_kunye` (kaynak, koşu zamanı, nokta → `bilesenler_json`): `kosu_cek_ve_arsivle` yazar, `arsivden_tahmin` okur →
  `MeteoData.bilesenler`; `nwp_model` etiketi harmana gerçekten giren modellerden kurulur (künye yoksa eski sabit etiket).
- `skill_daily.hesap_zamani`, `yeniden_hesap_sayisi`: karne satırı yeniden hesaplanırsa (ölçüm yeniden yüklendi, hijyen yeniden
  bayrakladı) sayaç artar; yalnız-ekleme karne AYRI karar.

## Arşiv sorgusu

`GET /v1/plants/{id}/tahmin-arsivi?hedef=<ISO>&yayin_oncesi=<ISO>` → `hedef` saati için `yayin_oncesi` anında yayımlanmış
(run_at ≤ yayin_oncesi) son koşunun değeri + künyesi (`forecast_service.yayimlanmis_kosu`). Geriye bakışlı etiketler hiç dönmez.
«Yayımlandı» iddiası yalnız `run_at` ile kurulur; yoksa 404.

## Betik yazıcıları

`forecast_values` yazan üretim yolu yalnız `forecast_service.arsive_yaz`. Betikler: `dev_skill_backtest.py` (`backtest`),
`faz1_solentegre_simulasyon.py` (model `backtest`, meteo `open-meteo-arsiv` → göçte `backtest`; yeni satırlar `simulasyon`
etiketi almalı — ayrı rötuş), `seed_sentetik.py` (`sentetik`). Liste `tests/test_cekirdek_siniri.py::BETIK_YAZICILAR`'da kilitli.
