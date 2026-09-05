# pvquant.ext.standart — standartlar ve metrik dili (rapor 3.3; entegrasyon öncesi paket)

3.3 tablosunun altı başlığının bağımsız kodları. Depoya ve model çekirdeğine bağlı değildir; önceki paketlerdeki
basit sürümlerin (pvquant.ext.tahmin.degradasyon.pr, pvquant.ext.tahmin.dogrulama.deterministik, pvquant.ext.kaynak.belirsizlik)
standarda tam uyan genişletilmiş halleridir. Seriler saatlik UTC; enerji kWh, ışınım W/m².

| 3.3 satırı | Modül | Standart / dayanak |
|---|---|---|
| IEC 61724-1 PR, PR′, Yr/Yf | `iec61724` | Y_r/Y_a/Y_f, PR, STC-düzeltmeli ve yıllık-ağırlıklı PR′ (IEC 61724-1 Ek), L_c/L_s, CF, %95 veri kuralı; Faiman T_c |
| nMAE/nRMSE/nMBE + skill | `sfa_metrik` | SFA `deterministic` sözlüğü: MAE/MBE/RMSE/MAPE/nMAE/nMBE/nRMSE/CRMSE/skill/r/R²/KSI/OVER/CPI; `karne_satiri` |
| P50/P90/P99 belirsizlik bütçesi | `belirsizlik_butcesi` | 7 bileşenli RSS (yıllar-arası σ/√N), P75/P95 dâhil, katkı yüzdeleri, lognormal Monte Carlo |
| PVsyst kayıp ağacı | `kayip_agaci` | 15 adımlı zincir (transpozisyon→…→kısıntı), saatlikten hesaplanan IAM/ışınım seviyesi/sıcaklık, 'açıklanamayan kalıntı', şelale verisi |
| IEC 61853 güç matrisi | `iec61853` | Matris → ADR verim modeli (pvlib), iki-doğrusal interpolasyon, veri sayfasından sentetik matris, CSER benzeri enerji derecesi |
| Availability | `kullanilabilirlik` | Zaman/enerji tabanlı (IEC 61724-3 / SPE O&M), hariç tutmalar, MTBF/MTTR, birim bazlı, sözleşme açığı |

## Kurulum ve test
```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
pytest -q     # 6 test, ağ gerektirmez
```

## Entegrasyon notları
- `iec61724.kpi` ve `sfa_metrik.karne_satiri` gece skill işine ve Santralım/Doğruluk kartlarına çekirdeğe dokunmadan girer.
- `kayip_agaci.agac` panelin mevcut şelale grafiğine (`selale`) doğrudan veri üretir; adım oranları kalibre fizikten ya da sabitlerden.
- `belirsizlik_butcesi` rapor künyesindeki "P50/P90" cümlesinin dayanağıdır; bileşen tablosu raporda gösterilebilir.
- `iec61853` modül η(G,T) çarpanını verir; zincirin neresine gireceği çekirdek kararı (★).
- Gizlilik Anayasası: bu modüllerin adları/yöntemleri (ADR, Faiman, Perez…) UI metnine çıkmaz; yalnız sonuçlar gösterilir.
