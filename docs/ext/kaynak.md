# pvquant.ext.kaynak — veri kaynağı modülleri (entegrasyon öncesi paket)

Rapor 3.1 tablosundaki başlıkların (ticari lisans satırı hariç) bağımsız kodları. Hiçbiri PVQuant
deposuna bağlı değildir; ortak sözleşme `MeteoCerceve` (saatlik UTC; `ghi, dni, dhi, temp_air,
wind_speed_10m, cloud_cover`) mevcut `MeteoData` ile bire bir eşlenir. Model çekirdeğine dokunmaz.

| Rapor satırı | Modül | Kaynak · lisans | Ağ / anahtar |
|---|---|---|---|
| Çoklu NWP harmanı | `nwp_ecmwf`, `nwp_icon`, `nwp_gfs`, `harman` | ECMWF Open Data CC BY 4.0 · DWD ICON-EU CC BY 4.0 · NOAA GFS/GEFS kamu malı | anahtar yok; GRIB için eccodes |
| Uydu türevli ışınım | `uydu_isinim` | CAMS (CC BY 4.0, e-posta kaydı) · PVGIS SARAH-3 (kayıt yok) · NASA POWER | pvlib.iotools |
| Uydu nowcasting (0–6 s) | `nowcast` | ölçüm/uydu persistansı + NWP rampalı harman; OCF tarzı sapma düzeltme | — |
| ERA5 arşivi + belirsizlik | `era5`, `belirsizlik` | Copernicus CDS (ücretsiz kayıt, `~/.cdsapirc`) | cdsapi |
| Bankable TMY/P90 | `tmy` | ISO 15927-4 / Sandia FS yöntemi; PVGIS TMY karşılaştırması | — |
| EPİAŞ gerçekleşen üretim | `epias` | Şeffaflık Platformu (kayıtlı kullanıcı; TGT) | `EPIAS_KULLANICI`, `EPIAS_SIFRE` |
| Kaynak atfı | `atif` | Anayasa istisnası (v2.245): künye üç yerde | — |

## Kurulum
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
brew install eccodes        # macOS; GRIB okuma için (Linux: apt install libeccodes0)
pytest -q                   # ağ gerektirmeyen testler
```

## Hızlı kullanım
```python
from pvquant.ext.kaynak import nwp_ecmwf, nwp_icon, nwp_gfs, harman, nowcast, atif
lat, lon = 37.87, 32.49                         # Konya
e = nwp_ecmwf.oku(nwp_ecmwf.indir("veri/ecmwf"), lat, lon)
i = nwp_icon.oku(nwp_icon.indir("veri/icon")[0].parent, lat, lon)
g = nwp_gfs.oku(nwp_gfs.indir("veri/gfs", lat, lon)[0].parent, lat, lon)
h = harman.harmanla({"ecmwf": e, "icon": i, "gfs": g})   # h.df: ghi (P50), ghi_p10, ghi_p90, ...
print(atif.kunye(["ecmwf", "icon", "gfs"]))
```
Örnekler `ornekler/` dizininde; her biri ağ ister ve tek başına çalışır.

## Tasarım notları
- **Harman kt üzerinde**: GHI değil gök açıklığı endeksi ağırlıklanır; ağırlık = son N günün ters-MSE'si.
- **Kaba adım → saatlik**: 3–6 saatlik ortalama, açık gök profiliyle saatliğe indirilir (enerji korunur).
- **Ensemble**: ENS/GEFS üyeleri varsa ampirik P10/P90; yoksa modeller arası yayılım × 1,28.
- **Nowcast**: gerçek uydu CMV yerine akıllı persistans + `exp(−h/τ)` rampa; uydu GHI kancası hazır.
- **Belirsizlik**: σ² = yıllar-arası² + kaynak² + model² + ölçüm²; P90 = P50·(1−1,282σ), N-yıl için σ/√N.
- **EPİAŞ**: `dengesizlik_maliyeti()` DUY md. 110–111 (k,l = 0,03); KÜPST ayrı — Kurul katsayıları parametre.
- **Atıf**: yalnız Hakkında paneli / rapor künyesi / README; çalışma ekranları "profesyonel meteoroloji verisi".

## Bilinen sınırlar
- ECMWF yalnız son ~2–3 günü tutar → `nwp_ecmwf.kosu_arsivle()` cron'u şart.
- GFS DSWRF bazı adımlarda 6 saatlik ortalama gelir; `kaba_adimi_saatlige_indir` bunu ele alır.
- CAMS ~2 gün gecikmeli — gerçek zamanlı nowcast girdisi değildir; nowcast SCADA/piranometreyle beslenir.
- ERA5 ışınımı uyduya göre sapabilir; `belirsizlik.kaynak_sapmasi(era5, sarah3)` ile σ_kaynak ölçülür.
- Bu paket entegrasyon kararından ÖNCE yazıldı: PVQuant `io/meteo.py` arayüzüne uydurma (`MeteoData`) ayrı dalgadır.
