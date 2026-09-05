# NREL "Solar Power Data for Integration Studies" — hakem fikstürü (v2.250)

Kaynak: NREL, https://www.nrel.gov/grid/solar-power-data.html (2006 sentetik PV santralleri; kamuya açık, ABD federal
kurumu veri seti — atıf: National Renewable Energy Laboratory). Üç santral, yalnız Haziran 2006:
`Actual_5_Min` (gerçekleşen, 5 dk), `DA_60_Min` (gün-öncesi tahmin), `HA4_60_Min` (4 saat öncesi tahmin); güç MW.

| Klasör | İklim | Kapasite |
|---|---|---|
| az_31.85_-110.85_UPV_100MW | kuru/açık | 100 MW |
| ca_32.65_-115.15_UPV_75MW | kıyı/çöl geçişi | 75 MW |
| ny_41.25_-73.55_UPV_38MW | kıtasal/bulutlu | 38 MW |

Referans değerler (`tests/test_nrel_hakem.py`) docs/research/nrel_hakem_metrik.py ile aynı tanımla üretildi:
5 dk → saatlik ortalama; gündüz = gerçekleşen ya da tahmin > %1 kapasite; WMAPE, nMAE, nRMSE, nMBE.
Amaç: karne motorunun metrik tanımları değişirse CI kırmızıya döner — sayıların bağımsız kanıtı.
