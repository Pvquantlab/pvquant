# pvquant.ext.tahmin — tahmin bilimi modülleri (rapor 3.2; entegrasyon öncesi paket)

3.2 tablosunun on bir başlığının bağımsız kodları. Hiçbiri PVQuant deposuna ya da model çekirdeğine
(`models_v2/hybrid_residual.py`) bağlı değildir; ★'lı başlıklar bile burada yalnız *kütüphane* olarak
yazılmıştır — çekirdeğe bağlanmaları ayrı, onaylı dalgalardır. Tüm seriler saatlik (ya da 15 dk) UTC.

| 3.2 satırı | Modül | Yöntem / dayanak |
|---|---|---|
| Olasılıksal kalibrasyon doğrulaması | `dogrulama` | reliability (kantil), PIT histogramı, pinball, CRPS (kantil ve ensemble), PICP, aralık skoru; deterministik SFA seti (nMAE/nRMSE/nMBE/WMAPE/skill) — Yang 2020, Lauret 2019, Gneiting 2007 |
| Conformal / kantil regresyon ★ | `konformal` | CQR (Romano 2019) ufuk/saat gruplu; ACI (Gibbs 2021) çevrimiçi; bağımlılıksız doğrusal kantil regresyonu |
| Ensemble yayılımı → belirsizlik ★ | `ensemble_belirsizlik` | spread–skill katsayısı c(h); EMOS-lite (μ=a+b·m, σ²=c+d·v) ufuk kovalı; üyesizde ufuk σ(h) |
| Curtailment / clipping maskesi ★ | `kisitlama` | plato+seviye clipping; düz-düşük curtailment; kalibrasyon maskesi; "kısıtsız senaryo" kayıp muhasebesi (pvanalytics kalıbı) |
| Rolling-origin backtest + kayma ★ | `backtest` | zaman-sıralı katlar (fit_predict fabrikası), PSI/KS kayma denetimi, kaynak tutarlılık (ölçüm↔NWP) |
| İklimsel referans + konveks birleşim | `referans` | saat×ay iklimsel, akıllı persistans, kapalı-form optimal w (ufuk bazlı) — Yang 2019 |
| Clear-sky McClear + IAM + spektral ★ | `fizik_terimler` | Ineichen/McClear, physical/ashrae/martin_ruiz IAM + Marion difüz, First Solar spektral M; `etkin_isinim` çarpanı |
| Soiling / kar ★ | `kirlenme` | HSU, Kimber, NREL kar örtüsü; ölçümden ampirik soiling; birleşik çarpan |
| Degradasyon + PR trendi | `degradasyon` | IEC 61724-1 PR ve sıcaklık düzeltmeli PR′; RdTools YoY (bootstrap GA); PR eğimi |
| Alt-saatlik (15 dk) | `alt_saatlik` | kt-sabit açık gök profiliyle indirgeme (enerji korunur, isteğe bağlı değişkenlik); 15 dk uzlaştırma |
| Portföy / hiyerarşik uzlaştırma | `portfoy` | S matrisi, bottom-up, top-down, MinT (OLS/WLS/shrink) — Wickramasuriya 2019 |

## Kurulum ve test
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q          # 14 test, ağ gerektirmez (McClear/CAMS ağ ister, testte yok)
```

## Entegrasyon sınırları (bilerek)
- `dogrulama`, `referans`, `backtest`, `degradasyon`, `portfoy`: çekirdeğe dokunmadan bugün gece skill işine / karneye eklenebilir.
- `konformal`, `ensemble_belirsizlik`: mevcut P10/P90 çıktısını **sonradan** düzeltir; çekirdek değişmez ama "PVQuant'ın P10/P90'ı" tanımı değişir → ★ onay.
- `kisitlama`: kalibrasyon girdisini maskeler → kalibrasyon davranışı değişir → ★ onay.
- `fizik_terimler`, `kirlenme`: POA'ya çarpan; zincirin neresine gireceği çekirdek kararı → ★ onay.
- `alt_saatlik`: DUY 15 dk uzlaştırma 1/1/2027 hedefi için hazırlık; bugün yalnız görüntüleme/uzlaştırma yardımcısı.

## Bilinen sınırlar
- CRPS kantillerden yaklaşık (kantil ızgarası sıklığıyla doğruluk artar); tam CRPS için ensemble üyeleri.
- ACI çevrimiçi çalışır; toplu backtest'te sırayla beslenmeli.
- EMOS-lite normal varsayımı (kırpılmış); güçlü çarpıklıkta CQR tercih edilmeli.
- Kar modeli pvlib.snow'un NREL uygulamasıdır; Türkiye için eşikler sahaya göre ayarlanmalı.
- Curtailment tespiti şebeke kısıtını "düz ve düşük" imzasından çıkarır; SCADA'da kısıt sinyali varsa o üstün gelir.
