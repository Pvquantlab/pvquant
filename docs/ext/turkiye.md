# pvquant.ext.turkiye — Türkiye pazarı modülleri (rapor 3.4; entegrasyon öncesi paket)

3.4 tablosunun dört başlığının bağımsız kodları. Depoya ve model çekirdeğine bağlı değildir. Mevzuat dayanağı:
DUY (RG 29/12/2025) md. 69, 69/A, 110, 111; LÜY (RG 02.04.2026); EPİAŞ SMF sayfası (k,l = 0,03, 1 Mayıs 2015'ten beri).
Kurul kararıyla belirlenen her katsayı (k, l, KÜPST n/tolerans, YEKDEM içi pay) **parametredir**, sabit kodlanmamıştır.

| 3.4 satırı | Modül | Ne yapar |
|---|---|---|
| KGÜP/DUY dengesizlik simülasyonu | `dengesizlik` | Saatlik DUY formülü (pozitif/negatif), KÜPST, referans-gelire göre maliyet, aylık karne (TL, gelir oranı, TL/MWh), iki program kıyası ("kurtarılan TL"), DSG netleşme, teminat, SMF spread senaryosu, optimal teklif kantili (newsvendor) |
| YEKDEM / serbest segmentasyon | `segment` | 6 segment (lisanslı serbest/YEKDEM/YEKA, iletim-lisanssız, dağıtım-lisanssız, öz-tüketim saatlik mahsup): KGÜP yükümlülüğü, dengesizlik sahibi, gelir formülü; saatlik gelir; dengesizliğin santrale düşen payı |
| EPİAŞ Şeffaflık entegrasyonu | `epias` | TGT (önbellekli), 12 uç nokta, 429/401 yeniden deneme, İstanbul→UTC hizalama, gün-bazlı CSV önbellek, `fiyat_paketi` (PTF/SMF/yön), gerçekleşen üretim → SCADA sözleşmesi adaptörü, ağsız test için sahte taşıyıcı |
| KGÜP bildirim dosyası | `kgup` | 24 saatlik program (KGÜP ≤ EAK ≤ kurulu güç), ≥200 MWh sıçramada 15 dk dilimleme, TPYS CSV (kolonlar parametrik — resmi şablon teyit edilemedi), 14:00–15:30 teslim durumu, GİP+30 dk revizyon penceresi, doğrulama |

## Kurulum ve test
```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
pytest -q     # 9 test, ağ gerektirmez (EPİAŞ testi MockTransport ile)
```

## Örnek: 10 MW santral, bir ay
```python
from pvquant.ext.turkiye import dengesizlik as d
s = d.saatlik(kgup_mwh, gerceklesen_mwh, ptf, smf, d.Katsayilar(k=0.03, l=0.03))
print(d.aylik_karne(s)[["toplam_maliyet", "maliyet_gelir_orani", "tl_per_mwh"]])
print(d.kiyas(naif_kgup, pvquant_kgup, gerceklesen_mwh, ptf, smf))      # "PVQuant X TL kurtardı"
```

## Teyit edilemeyenler (parametre bırakıldı)
- KÜPST katsayısı n ve tolerans; YEKDEM portföyü içinde dengesizliğin santrale dağılımı; TPYS CSV resmi kolonları;
  EPİAŞ yanıt alan adları uç noktaya göre değişebilir (`seri(..., alan=...)` ile aşılır).
- Fiyatlar: EPDK 2025 yıllık PTF 2.651,81 / SMF 2.524,09 TL/MWh (örneklerde), canlıda `epias.fiyat_paketi`.

## Gizlilik Anayasası
Modül adları ve mevzuat maddeleri UI'da geçebilir (yöntem değil, kural); tahmin yöntemi adları geçmez.
