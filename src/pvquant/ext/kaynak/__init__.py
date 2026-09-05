"""pvquant.ext.kaynak — PVQuant için bağımsız veri-kaynağı modülleri (entegrasyon öncesi).

Rapor 3.1 tablosundaki başlıklar (ilk satır hariç):
  nwp_ecmwf / nwp_icon / nwp_gfs + harman  → Çoklu NWP harmanı (ECMWF + ICON + GFS)
  uydu_isinim                              → Uydu türevli ışınım (CAMS / PVGIS-SARAH)
  nowcast                                  → Kısa ufuk (0–6 s) katmanı
  era5 + belirsizlik                       → Uzun homojen iklim arşivi + belirsizlik bütçesi
  tmy                                      → Bankable TMY / P50-P90-P99
  epias                                    → EPİAŞ Şeffaflık gerçekleşen üretim ve fiyatlar
  atif                                     → Kaynak atfı (lisans künyesi)

Ortak çıktı sözleşmesi: ``ortak.MeteoCerceve`` — saatlik UTC DataFrame, kolonlar
ghi, dni, dhi (W/m²), temp_air (°C), wind_speed_10m (m/s), cloud_cover (%).
"""
from .ortak import MeteoCerceve, KaynakBilgisi

__all__ = ["MeteoCerceve", "KaynakBilgisi"]
__version__ = "0.1.0"
