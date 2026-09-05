"""pvquant.ext.standart — standartlar ve metrik dili (rapor 3.3; entegrasyon öncesi, çekirdeğe dokunmaz).

  iec61724         → IEC 61724-1 KPI seti: Yr/Ya/Yf, PR, sıcaklık düzeltmeli PR′ (yıllık ağırlıklı), Lc/Ls, CF
  sfa_metrik       → Solar Forecast Arbiter deterministik sözlüğü: MAE/MBE/RMSE/MAPE/nMAE/nMBE/nRMSE/CRMSE/skill/r/R²/KSI/OVER/CPI
  belirsizlik_butcesi → bankable P50/P75/P90/P95/P99: bileşen tablosu, RSS, N-yıl, Monte Carlo (lognormal)
  kayip_agaci      → PVsyst tarzı kayıp ağacı (GHI→POA→IAM→soiling→gölge→spektral→sıcaklık→…→availability), şelale verisi
  iec61853         → IEC 61853-1 güç matrisi: interpolasyon, ADR verim modeli uydurma, matris üretimi, enerji derecesi
  kullanilabilirlik → zaman/enerji tabanlı kullanılabilirlik, hariç tutmalar, MTBF/MTTR, sözleşme hesabı
"""
__version__ = "0.1.0"
