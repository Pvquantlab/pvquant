"""pvquant.ext.turkiye — Türkiye pazarı modülleri (rapor 3.4; entegrasyon öncesi, çekirdeğe dokunmaz).

  dengesizlik  → KGÜP/DUY dengesizlik + KÜPST simülatörü (PTF/SMF, k,l=0,03), senaryo/kıyas, teminat, TL karnesi
  segment      → YEKDEM / serbest / lisanssız (GTŞ-toplayıcı) / öz-tüketim segmentasyonu: dengesizlik kimde, gelir formülü
  epias        → EPİAŞ Şeffaflık entegrasyonu: TGT, PTF/SMF/yön/KGÜP/gerçek zamanlı üretim, önbellek, UTC hizalama
  kgup         → KGÜP saatlik program dosyası (TPYS CSV), 15:30 kuralı, ≥200 MWh 15 dk bayrağı, EAK, gün içi revizyon, teklif kantili
Saat dilimi: piyasa günü Europe/Istanbul (2016'dan beri sabit +03, yaz saati yok → her gün 24 saat).
Mevzuat: DUY (RG 29/12/2025 sürümü) md. 69, 69/A, 110, 111; katsayılar Kurul kararıyla — hepsi parametre.
"""
__version__ = "0.1.0"
