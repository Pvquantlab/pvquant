# 14 — Eylem planı ve dış eylem izin listesi (Faz 8, F8-I — 13.11.2026)

> İki liste: **iç eylemler** (izin gerektirmez; çoğu bitti) ve **dış eylemler** (her biri **kullanıcının açık iznini bekler**; hiçbiri yapılmadı). Dış eylem = e-posta, arama, form,
> taahhüt, özel sisteme erişim, gizli belge paylaşımı, kullanıcı hesabıyla veri okuma, reCAPTCHA. Kişi adı hiçbir satırda yok; kuruluşlar `03` AD kimliğiyle.

## 1. İç eylemler (Faz 8 kapsamı; masa başı)

| # | Eylem | Çıktı | Durum (13.11.2026) |
|---|---|---|---|
| İ1 | Kanıt sicili + hazırlık denetimi | 13 + kanit_sicili.csv (65 satır; K-65 F8-I), 01 taslak | **Tamamlandı** (F8-A; öz inceleme 4/4) |
| İ2 | Pazar araştırması güncellemesi (19.10.2026 paketi, EPDK Eylül, toplayıcılar, şirket sinyalleri) | 02 | **Tamamlandı — Kısmen**: YEKDEM dışı ≈97 lisans sahibi adıyla yok; Şeffaflık santral listesi okunamadı (F8-B yeniden; öz inceleme 9/9) |
| İ3 | Aday havuzu 40 + kısa liste 15 | 03 + aday_havuzu.csv | **Tamamlandı — Kısmen**: 15 satır «ek araştırma» (F8-C; öz inceleme 5/5) |
| İ4 | Görüşme protokolü + kayıt şablonu | 04, 05 + gorusme_kayit_sablonu.csv | **Tamamlandı** (F8-D; 6/6) |
| İ5 | Pilot protokolleri, eşikler önceden | 06, 07 | **Tamamlandı — Doğrulama gerekiyor**: eşikler ÖNERİ, canlı 30 gün sayılarıyla kalibrasyon + kullanıcı onayı (F8-E; 5/5) |
| İ6 | Finansal doğrulama yöntemi + şablon | 08 + finansal_dogrulama_sablonu.csv | **Tamamlandı** (F8-F; 4/4) |
| İ7 | Fiyat/ödeme istekliliği programı (sayısız) | 09 | **Tamamlandı** (F8-G; 3/3) |
| İ8 | Dönüşüm süreci, puan kartı, risk sicili | 10, 11 + puan_karti.csv, 12 | **Tamamlandı** (F8-H; 4/4) |
| İ9 | Eylem planı, nihai rapor, 01 nihai, 3 kalite turu | 14, 15, 01; `kanit/F8-I_kalite_turlari…` | bu paket |
| İ10 | Canlı bağımsız doğrulama 30 gün okuması için SQL (kullanıcı prod'da çalıştırır; üretim DB okuması araçtan engelli) | `kanit/F8-I_canli_dogrulama_okuma.sql` | hazır; **çıktı bekleniyor** → 06 §4 kalibrasyonu |
| İ11 | Haftalık RG tarama rutini bitiş tarihi (kullanıcı isteği 1.11–31.12.2026; cron'da bitiş yok) | rutin güncellemesi | **karar kullanıcıda** (ayrı iş; dış eylem değil) |
| İ12 | Tek «Rapor:» commit'i (docs/ticari-dogrulama + CSV'ler; kod yok; CI docs işi; dağıtım gerekmez) | commit | **karar kullanıcıda** («commitle»/«gönder» deyince) |

## 2. Dış eylemler — İZİN BEKLİYOR (hiçbiri yapılmadı)

| # | Eylem | Kime / neye | Taslak / araç | Bağımlılık | Zaman penceresi | Risk | Durum |
|---|---|---|---|---|---|---|---|
| D1 | Görüşme talebi e-postası (kurumsal adres; kişi adı yok) | kısa liste 15 kuruluş (03 §2), kuruluş kuruluş onay | 04 §9 taslağı (A/C/D ve B varyantı) | — | **A segmenti 30.11 öncesi** (YEKDEM kararı); diğerleri Kasım–Aralık | R1 erişim | izin bekliyor |
| D2 | Arama (kurumsal santral/iletişim hattı) | D1 yanıt vermeyenler | 04 §9 90 sn senaryo | D1 sonrası 7 gün | — | R1 | izin bekliyor |
| D3 | Kamu/OSB lisanssız teyit görüşmesi (LL; 1 kamu + 1 OSB) | bilgi edinme / resmî yazı | 04 §1; taslak yok (kurum seçimi önce) | — | — | — | izin bekliyor |
| D4 | EPDK EPVYS üretim lisansı sorgusu (kaynak: güneş) — YEKDEM dışı ≈97 lisans sahibi | lisans.epdk.gov.tr | tarayıcı paneli; **reCAPTCHA kullanıcı işaretler** | — | — | 03 havuz A segmenti büyür | izin/işaret bekliyor |
| D5 | Şeffaflık lisanslı santral / organizasyon / UEVÇB listesi okuma (kullanıcı hesabı) | seffaflik.epias.com.tr | tarayıcı; 13.11 16:25 ERR_EMPTY_RESPONSE | kullanıcı girişi | — | toplayıcı portföyleri (hangi santral hangi toplayıcıda) | izin bekliyor |
| D6 | KAP Genel Bilgi Formu / ÖDA okuma (tüzel kişi ↔ grup bağları: Birleşim 3 şirket, Fergün/Fernas, Soleil/Margün, RA/Consus, Ilgaz/Kıvanç) | kap.org.tr (JS; kullanıcı tarayıcısı) | tarayıcı | — | — | — | izin bekliyor |
| D7 | Rönesans Reflex, Renoe, Pure Energy, Consus, Sanko siteleri (TLS/JS) tarayıcıyla | şirket siteleri | tarayıcı paneli | — | — | — | izin bekliyor (okuma; düşük risk) |
| D8 | Canlı `dogrulama_sonuc` 30 gün özeti (prod SQL) | üretim DB | `kanit/F8-I_canli_dogrulama_okuma.sql` | — | hemen | R5 | **kullanıcı çalıştırır** |
| D9 | Pilot: veri işleme sözleşmesi + pilot protokolü imzası + veri erişimi | pilot adayı (06/07 G1–G9) | 06/07; sözleşme taslağı yok (hukuki metin kullanıcıda) | D1 → sinyal ≥4 | pilot 60 gün; ilk 2 dönem raporu en erken Ocak 2027 | R3, R6 | izin bekliyor |
| D10 | Teklif mektubu gönderimi (sayılar doldurulmuş) | pilot kapanışı sonrası | 09 §6 şablonu | D9 + 09 §8 (≥5 kuruluş egzersiz) | kapanış + 14 gün (ÖNERİ) | R12 | izin bekliyor |
| D11 | Pilot ücreti kararı (ücretsiz/ücretli) ve eşik onayı (06/07 §4) | kullanıcı kararı | 09 §2, 06/07 | D8 (kalibrasyon) | pilot öncesi | — | **karar bekliyor** |
| D12 | Vitrin/panel metni değişikliği (SSS, 02 M1 KGÜP-YEKDEM uyarısı vb.) | kod/metin | Faz 6 04 §6 önerisi | ayrı mühür | — | — | **Faz 8 kapsamı dışı**; ayrı karar |

## 3. Sıra önerisi (izin verilirse)

1. D8 (SQL çıktısı) → 06 §4 eşik kalibrasyonu → D11 (eşik + pilot ücreti kararı).
2. D4 + D5 + D6 (okuma; düşük risk) → 03 havuzu büyür, grup bağları netleşir.
3. D1 A segmenti (Birleşim, Kıvanç, Margün, Akfen, Kalyon) **30.11 öncesi**; sonra C (Aksa, Zorlu, Zeros, Limak, Rönesans, CK) ve D (Akenerji, Enerjisa Üretim); B (Enerjisa MÇ, Eksim).
4. Görüşmeler (haftada 2 kuruluş, 6–8 hafta) → 05 kayıtları → 11 puan kartı canlı.
5. Sinyal ≥4 adaylarda D9 → pilot (60 gün) → 06/07 kabul → D10 teklif → 10 dönüşüm.
6. Aralık ortası: Y4 soruları; Ocak 2027: ilk 08 raporu (Kasım + Aralık dönemleri).

Hiçbir dış eylem bu belgeyle başlamaz; her biri için kullanıcı «gönder / çalıştır / işaretledim» der.
