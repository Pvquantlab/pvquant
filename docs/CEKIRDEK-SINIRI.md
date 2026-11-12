# Korunan çekirdek sınırı (Faz 4 F4-A, v2.597)

Tarih: 11 Kasım 2026. Bekçi: `tests/test_cekirdek_siniri.py` (AST, DB'siz). Altın referanslar: `tests/test_altin_cekirdek.py`
+ `tests/data/altin/*.json`. Plan: `~/Desktop/PVQuant_Faz4_Mimari/00_Mimari_Denetim_ve_Plan.md` (F4-A).

## Neden

Tahmin çekirdeği (fizik zinciri, kalibrasyon, hibrit artık modeli, bant katmanlarının saf uygulayıcıları) ürünün
doğrulanmış değeridir. Platform katmanları (DB, API, worker, dış API, portföy, finans) onun ÜSTÜNE kurulur; çekirdeğin
onlardan haberi olmaz. Sınır belgeyle değil testle korunur: korunan modül servis/DB/uygulama içe aktarırsa CI kırmızı.

## Korunan modüller (servis/DB/uygulama içe aktarmaz)

| Bölüm | İçerik | Stabil arayüz |
|---|---|---|
| `pipeline/forecast.py` | fizik zinciri (GHI→POA→hücre sıcaklığı→DC→AC), `PlantSpec`, `ForecastResult` | `forecast_7day(meteo, spec)`, `PlantSpec` alanları |
| `pipeline/calibration.py`, `pipeline/utils.py` | SCADA ile kalibrasyon, yardımcılar | `calibrate_from_scada` |
| `pipeline/hybrid_ui.py` | hibrit model köprüsü | `hybrid_forecast_hourly(model, meteo)` (başarısızlıkta `None`) |
| `models/*` | ışınım, sıcaklık, güç, bifacial modelleri | — |
| `models_v2/*` | Barhdadi–Bennis, hibrit artık (lightgbm), sözleşmeler | `HybridResidualModel.predict/calibrate`, `contracts.*` |
| `ext/tahmin/*` | saf tahmin uzantıları (doğrulama, konformal, portföy belirsizliği, kirlenme, kısıtlama, …) | modül işlevleri |
| `io/meteo.py` | `MeteoData` veri sınıfı + Open-Meteo istemcisi | `MeteoData` alanları (`kaynak`, `nwp_model`, `kosu_zamani`) |

Yasak içe aktarımlar: `pvquant.services`, `pvquant.db`, `pvquant.surum`, `apps`, `sqlalchemy`, `psycopg`, `alembic`.
İzinli: `pvquant.config` (ayar okuma, DB değil), `pvquant.io.*`, `pvquant.validation`, `pvquant.ext.turkiye` (saf).

`io/` katmanı: servis içe aktarmaz. İki bilinen istisna adıyla listelidir ve kapanışları planlıdır:
- `io/acik_nwp.py` → `pvquant.db` (meteo arşivi okuma/yazma; v2.597'de bileşen künyesi `meteo_kosu_kunye` de buradan). Hesap kısmı
  (`harmanla`, `_cerceve_to_meteodata`, üye türetme) ile erişim kısmının ayrılması sonraki paketlere kaldı (F4-B kapsamına alınmadı).
- `io/bulut/solaredge_oauth.py` → `pvquant.services.bulut_oauth_service.uygulama`. F4-I (dış API/bulut) kapanışı.
İstisna kapanınca bekçi «ölü istisna» diye uyarır; liste küçülür, büyümez.

## Saf katman işlevleri (DB/ağ adı geçmez; zaman parametredir)

| Modül | Saf işlevler | DB/ağ eşlikçisi |
|---|---|---|
| `services/forecast_service.py` | `tahmin_uret(plant, meteo, girdi, simdi)`, `eksik_saatleri_kirp`, `kosu_cercevesi_denetle` | `girdileri_topla` (DB/disk), `arsive_yaz` (DB), `uret_ve_kaydet` (orkestratör) |
| `services/plant_spec_service.py` | `plant_spec_kur(plant, kalibrasyon_params)`, `params_json` | — |
| `services/ensemble_service.py` | `uye_kantilleri`, `uye_meteodata`, `bant_hesapla(plant, spec, meteo, h, uyeler)` | `uyeler_getir` (DB), `bant_uret` = ikisi |
| `services/ufuk_service.py` | `uygula_df(h, ayar, run_at, tavan)`, `sigma_hesapla_df` | `ayar_getir`, `gece_ufuk_sigma` |
| `services/sapma_service.py` | `uygula_df(h, ayar, tz)`, `oranlar_hesapla` | `ayar_getir` |
| `services/konformal_service.py` | `uygula_df(h, ayar, tavan, run_at)`, `q_hat_hesapla_df`, `q_dizisi` | `ayar_getir`, `q_hat_hesapla`, `gecmis_band_df` |

Kural: `*_hesapla*` işlevleri ürettikleri ayara `hesap_zamani` damgası basabilir; uygulayıcılar (`uygula_df`, `q_dizisi`,
kantiller, kurucu) saat okumaz. `tahmin_uret` yalnız `simdi` verilmezse koşu anını alır.

## Koşu akışı (v2.597)

```
uret_ve_kaydet(tenant, plant, etiket)
  meteo  = OpenMeteoClient().get_forecast(...)                       # ağ (ya da acik-nwp arşivi)
  girdi  = girdileri_topla(tenant, plant, days)                      # DB: kalibrasyon, ML satırı(+artefakt), GEFS üyeleri, katman ayarları
  sonuc  = tahmin_uret(plant, meteo, girdi, simdi)                   # SAF: fizik→hibrit→ensemble→ufuk→sapma→konformal→kırp→bekçi
  run_id = arsive_yaz(tenant, plant, meteo, sonuc, kalibrasyon_id, etiket)   # DB: forecast_runs + forecast_values (tek işlem, sayım bekçisi)
```

`TahminGirdisi` alanları: `mode`, `kalibrasyon_id`, `kalibrasyon_params`, `ml_model_id`, `model`, `uyeler`, `ufuk_ayar`,
`sapma_ayar`, `konformal_ayar`, `geri_dusus`. `TahminSonucu`: `h` + künye parçaları (`mode`, `model_adi`, `ml_model_id`,
`bant`, `sapma`, `ufuk`, `konformal_ayar`, `n_eksik`, `geri_dusus`, `simdi`).

### Künye dürüstlüğü (M2 düzeltmesi)

Hibrit yol gerçekten koşmadıysa koşu Mod C diye yazılmaz:

| Durum | mode | model | ml_model_id | konformal | `meteo_ozet_json.geri_dusus` |
|---|---|---|---|---|---|
| artefakt yüklü, predict başarılı | C | hybrid_residual | dolu | uygulanır | null |
| artefakt yüklü, `hybrid_forecast_hourly` → None | B | barhdadi_bennis | null | atlanır | `hibrit_basarisiz` |
| kalibrasyon C, artefakt diskte yok (v2.80 vakası) | B | barhdadi_bennis | null | atlanır | `hibrit_artefakt_yok` |
| kalibrasyon C, aktif ML kaydı yok | B | barhdadi_bennis | null | atlanır | `hibrit_artefakt_yok` |

Eski davranış (v2.596 ve öncesi): ikinci ve dördüncü satırda künye C/hybrid_residual kalıyor, konformal q̂ fizik bandına
uygulanıyordu. Kalibre edilmiş q̂ başka bir modelin bandına ait olduğundan bu, bandın anlamını bozuyordu. Geçmiş koşular
değiştirilmez; `geri_dusus` yeni koşularda dolar (eski koşularda anahtar yok = bilinmiyor).

### PlantSpec tek kaynak

`plant_spec_service.plant_spec_kur(plant, kalibrasyon_params)`: santral satırı → `PlantSpec`; kalibre `eta_bos` BoS
verimine, `bg` geometrik BG'ye (`bifacial_gain_geometric`), BF panel teknolojisinden (0,7 bifacial). Eski adlar
`calib_service._plant_spec` / `_pj` kalibrasyonsuz hâli döndüren ince sarmalayıcılardır (testlerin yamaları için).
Kapanan kusur: `scripts/dev_skill_backtest.py` `bg`'yi `bifacial_factor` yuvasına yazıyordu (v2.133 kuralına aykırı).

## forecast_values yazan yollar

Üretimde tek yol `forecast_service.arsive_yaz` (bekçi: `src` + `apps` içinde başka `INSERT INTO forecast_values` yok).
Betikler (üretim yolu değil, adıyla listeli): `scripts/dev_skill_backtest.py`, `scripts/faz1_solentegre_simulasyon.py`,
`scripts/seed_sentetik.py` (M3: gerçek koşuları siler — F4-C'de üretimde kilit). Yeni bir yazıcı bekçi listesine ve bu
belgeye eklenmeden giremez.

## Altın referanslar

| Dosya | Ne dondurur | Tolerans |
|---|---|---|
| `tests/data/altin/forecast_7day.json` | 3 gün sentetik meteo × bifacial 1 MWp (AC 900 kW, IAM ashrae, spektral first_solar, kalibre η_bos 0,9 / BG 0,1): `p_ac_kw`, `p_dc_kw`, `poa_global`, `temp_cell`, toplam kWh | rel 1e-6 |
| `tests/data/altin/katman_zinciri.json` | `tahmin_uret` saf yolu: 8 sentetik GEFS üyesiyle ensemble bandı → ufuk σ (20/45/70 kW) → sapma oranı (sabah 0,92 / öğleden sonra 1,04) → kırpma; `p50/physics/p10/p25/p75/p90/p10_ham/p90_ham` | rel 1e-6 |
| `tests/data/altin/konformal_uygula.json` | aynı ham bant + saat gruplu q̂ (genel 12, 06:20, 09:30, 12:35, 15:25) → servis bandı | rel 1e-6 |
| `tests/data/altin/hibrit_predict.json` | 90 gün deterministik sentetik eğitim (lightgbm `random_state=42`, veri zarı seed 7) → 3 gün `p50/p10/p90` | rel 1e-6; lightgbm sürümü farklıysa test ATLANIR (meta) |

Kasıtlı çekirdek değişikliği: `PVQ_ALTIN_YENILE=1 .venv/bin/python3 -m pytest tests/test_altin_cekirdek.py` ile referans
yenilenir; commit NEDEN'inde hangi referansın neden değiştiği yazılır. Referans sessizce yenilenmez.

## Açık işler (ayrı onay)

- Çekirdekteki 33 `.bak` dosyası (`pipeline/`, `models_v2/`) silinmemiştir; silme ayrı onay.
- `models_v2/{selector,registry,storage,protocol}` ve `api/routes` ölü kod adayı; rapor + silme ayrı onay.
- `io/acik_nwp.py` hesap/erişim ayrımı (sonraki paket), `solaredge_oauth` servis bağı (F4-I).
