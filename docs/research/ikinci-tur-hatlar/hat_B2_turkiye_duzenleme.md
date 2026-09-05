# Hat B2 — Türkiye düzenleme ve piyasa mekaniği (ajan raporu özeti, 5 Eyl 2026)
Birincil kaynak: DUY (mevzuat.gov.tr PDF, son değişiklik RG 29/12/2025-33122) https://www.mevzuat.gov.tr/MevzuatMetin/yonetmelik/7.5.12985.pdf

## (a) KGÜP
- Kim: tüm üretim UEVÇB'leri (md. 69(2)); toplayıcılar portföyleri için (69(8)-(9), RG 17/12/2024); iletim bağlı lisanssızlar da (69(10), RG 21/1/2025). MW eşiği yok; RES/GES dengeleme birimi olmaktan muaf (22(4)).
- Saatler: DGP 14:00'te başlar; 15:30'a kadar KGÜP + YAL/YAT (EPYS); 17:00'a kadar TEİAŞ maddi hata kontrolü/teyit (69(4)). EPİAŞ: https://www.epias.com.tr/kesinlesmis-gunluk-uretim-programi/
- Çözünürlük: saatlik; ardışık 2 saat farkı ≥200 MWh ise 15 dk (69(3)).
- Gün içi güncelleme: GİP kapı kapanışı (teslimattan 1 s önce) + 30 dk'ya kadar (69(1)); RG 29/12/2025: GİP güncellemesi TEİAŞ '1 kodlu' kısıt talimatlarını artıramaz.
- 15 dk: DGP uzlaştırma dönemi 15 dk (91(2)) ama Geçici md. 40 → altyapı en geç 1/1/2027; 2025-2026'da geçilmedi. Ölçüm Sist. Yön. değişikliği RG 21/1/2026-33144.
- 69/A (RG 29/12/2025): emre amade kapasite 15:30'a kadar; gerçeğe aykırı bildirim → Kanun md. 16.

## (b) Dengesizlik
- EDM = (veriş−çekiş) − ikili anlaşma − GÖP/GİP/VEP ± YAL/YAT (md. 111). Pozitif: min(PTF,SMF)×(1−l); negatif: max(PTF,SMF)×(1+k); k,l Kurul kararı 0–1. %3 = EPDK 01.05.2015 kurul kararı (ikincil kaynak) — 2026'da geçerliliği BİRİNCİL KAYNAKLA TEYİT EDİLEMEDİ; değiştiren karara rastlanmadı.
- Değişiklikler: RG 17/12/2024, 21/1/2025, 29/12/2025. md. 110(1)-(2) yeniden yazıldı: azami fiyat limiti, 15 dk SMF_N/SMF_P (2027 hazırlığı); V=150, B=100 TL/MWh birim fiyatlar.
- KÜPST (KGÜP'ten sapma tutarı, md. 110(3)-(6)): KGÜP bildirmekle yükümlü UEVÇB'ler için ayrı sapma tutarı; katsayı n ve tolerans katsayısı Kurul kararıyla; toplayıcı portföyünde topluluk veya münferit.
- YEKDEM: DUY'da ayrı dengesizlik havuzu hükmü yok; YEKDEM Yön. metni çekilemedi → TEYİT EDİLEMEDİ.
- Lisanssız: LÜY'de 'dengesizlik' hiç geçmiyor; ihtiyaç fazlası GTŞ satın alır; dağıtım bağlı lisanssızın doğrudan dengesizlik sorumluluğu YOK (GTŞ/toplayıcı taşır). İstisna: iletim bağlı lisanssız KGÜP; toplayıcı portföyünde KÜPST. RG 25/11/2025-33088.

## (c) EPİAŞ Şeffaflık API
- Doküman https://seffaflik.epias.com.tr/electricity-service/technical/tr/index.html ; swagger v1.15.15, 301 path, basePath /electricity-service
- POST endpoint'ler: /v1/markets/dam/data/mcp (PTF), /v1/markets/bpm/data/system-marginal-price (SMF), /v1/markets/bpm/data/system-direction, /v1/generation/data/dpp ve dpp-first-version (KGÜP), /v1/generation/data/realtime-generation, /v1/markets/imbalance/data/imbalance-quantity|imbalance-amount, /v1/markets/idm/data/weighted-average-price, /v1/renewables/data/imbalance-cost, /v1/renewables/data/res-generation-and-forecast; /export/ karşılıkları
- Kimlik: kayıt + TGT https://giris.epias.com.tr/cas/v1/tickets (11 Kas 2025: username/password body'de; 5 Oca 2026 query-string kaldırıldı)
- Rate limit CAS (23 Tem 2025): TGT 100/dk kullanıcı, IP 1000/dk; ST 1500/dk https://www.epias.com.tr/tum-duyurular/cas-token-request-limitleri/
- Python: eptr2 (Tideseed, 1.3.9.dev3, 24 Ağu 2026, 213+ servis) https://github.com/Tideseed/eptr2

## (d) GİP / DGP / fiyatlar
- GİP: 18:00 açılır, kapı kapanışı teslimattan 1 s önce, sürekli ticaret, saatlik kontratlar https://www.epias.com.tr/gun-ici-piyasasi/genel-esaslar/
- DGP: 14:00 / 15:30 / 17:00; teklifler 15 dk içinde gerçekleştirilebilir (md. 70); SMF md. 109
- 2025 ortalamaları (ikincil, grentistr): PTF 2.619,8 TL/MWh, SMF 2.525,6, GİP AOF 2.603 — EPİAŞ yıllık raporuyla teyit edilemedi. EPİAŞ aylık: Haz 2025 PTF 2.202,23; Kas 2025 hafta 48: 2.987,78; Oca 2026 saat 19 PTF 3.337,56 / SMF 2.919,16. Aylık bültenler https://www.epias.com.tr/elektrik-piyasasi-aylik-bulten/

## (e) MGM / GEPA / RİTM
- MGM: ücretli, MEVBİS https://mevbis.mgm.gov.tr/ ; 2026 fiyat listesi PDF (taranmış); kamuya açık REST API yok; ücretsiz HELIOSAT 2004-2021 haritaları
- GEPA https://gepa.enerji.gov.tr aktif (güncelleme tarihi belirsiz)
- RİTM Yönetmeliği RG 6/2/2026-33160: ≥10 MWe RES'ler için bağlantı belgesi zorunlu; GES KAPSAM DIŞI; güneş için benzeri zorunluluk yok. https://ritm.teias.gov.tr/basvuru

## (f) Yaptırım
- KGÜP sapması için ayrı ceza yok; mali sonuç = dengesizlik tutarı + KÜPST. İdari: KGÜP bildirmemeyi itiyat, talimata uymama, 69/A → TEİAŞ raporu → EPDK, Kanun md. 16. 2026 idari para cezaları: md.16(1)(a-c) 10.325.625 TL; (ç) 16.521.042 TL.
