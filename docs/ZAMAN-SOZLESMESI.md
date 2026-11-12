# Zaman sözleşmesi (Faz 4 F4-D, v2.599)

Tarih: 12 Kasım 2026. Kod: `src/pvquant/zaman.py` (saf, tek yer). Testler: `tests/test_zaman_v2599.py`. İlgili: `docs/VERI-KALITESI.md`
(`scada_hourly.kaynak_damga_tipi`), `docs/TAHMIN-ARSIVI.md`.

## Kurallar

1. **Saklama UTC, tz-aware.** `scada_hourly.ts_utc`, `forecast_values.ts_utc`, `sayac_saatlik.ts_utc`, `meteo_*.ts_utc` hep UTC. Yerel
   gösterim arayüzde; hesap yerel güne ihtiyaç duyarsa `zaman.santral_gunu` / `zaman.piyasa_gunu` kullanır.
2. **Aralık başı.** Saatlik satır damgası aralığın BAŞIdır: 10:00 = 10:00–11:00 üretimi/tahmini. Bu, arşivin tek konvansiyonudur.
   Kaynak başka konvansiyon kullanıyorsa yükleme yolunda çevrilir ve kaynağın konvansiyonu künyeye yazılır (`kaynak_damga_tipi`:
   `aralik_basi` | `aralik_sonu` | `anlik`; `TransformSpec.damga_duzeltme`: `saat-1`, `adim_geri`).
   - Hour-ending dosya (saat kolonu 1–24): saat−1 (24 → 23:00 aynı gün). Eskiden `mod 24` 24'ü günün 00:00'ına yığıyordu (hata).
   - «24:00» damgası = ertesi gün 00:00 (sayaç OSOS kuralıyla aynı; `transform._yirmi_dort_sifirla`).
   - Aralık sonu damgalı 15 dk/saatlik dosya: `damga_tipi="aralik_sonu"` → bir adım geri. API: `POST /v1/plants/{id}/scada` form alanı
     `damga_tipi` (varsayılan `aralik_basi`).
   - Anlık ölçüm (`anlik`): kaydırılmaz; o anı izleyen aralığın temsilcisi sayılır, künye bunu söyler.
3. **Piyasa dilimi tek tanım.** `zaman.PIYASA_TZ = "Europe/Istanbul"`; `IST` / `IST_AD` / `PIYASA_TZ` adları (12 modül) buna bağlıdır.
   Bekçi: kodda başka `= "Europe/Istanbul"` ataması yok (SQL içindeki `AT TIME ZONE 'Europe/Istanbul'` metinleri ayrı; F4-D sonrası rötuş).
   Türkiye 2016'dan beri yaz saati uygulamaz; DST mantığı yalnız yabancı dilimli kaynak dosyalar içindir (Europe/Berlin testi).
4. **Günler.** Piyasa günü (uzlaştırma, KGÜP, DGP, program kesimi) İstanbul takvim günüdür: `zaman.gun_basi_utc(gun)`,
   `zaman.program_kesimi(gun)` (D-1 15:30; 2024 ve öncesi 16:00 — `kurallar.kgup_kesim`). Santral günü (`plants.tz`) rapor/dönem
   kırpması içindir. **`skill_daily.date` UTC günüdür** (worker `df.ts_utc.dt.date`): karne günü = UTC günü; piyasa gününe geçiş
   AYRI karar (geçmiş satırlar yeniden hesaplanmadan karşılaştırılamaz).
5. **Dönem kodları** tek çözümleyiciden: `ext/platform/finans.donem_cozumle` (gün/hafta/ay/çeyrek/yıl; süren dönem bugüne kırpılır;
   gelecek dönem hata; yerel dilimde 23/25 saatlik gün). `aylik_rapor_service.donem_cozumle` ona devreder (yalnız ay/çeyrek/yıl kabul eder).
6. **15 dakika politikası.** Arşiv saatliktir; gerçek 15 dk tahmin ÜRETİLMEZ ve iddia edilmez. `ext/tahmin/alt_saatlik.saatlikten_15dk`
   saatlik değeri açık gök profiliyle DAĞITIR; çıktı `attrs["yontem"]` = «saatlik dağıtım (açık gök profili) — 15 dk ölçüm ya da tahmin
   değildir»; saatlik girdide olmayan saat 0 değil EKSİK (NaN) kalır (eski `fillna(0)` kaldırıldı). Toplayıcı 15 dk tablosu
   `attrs["dagitim_yontemi"]` taşır. Piyasanın 15 dk'ya geçişi doğrulanınca (kural sicili bayrağı, F4-F) tahmin çözünürlüğü ayrı paketle açılır.
7. **Yaz saati geçişi** (yabancı dilim): satır düşmez, bayraklanır (`dst_ambiguous`; v2.598 M4).
8. **Enerji korunur.** Saatliğe indirgemede enerji TOPLANIR, güç ORTALANIR; boş saat enerjisi 0 değil NaN (`eksik`).

## Bilinen açık noktalar

- SQL metinlerinde `AT TIME ZONE 'Europe/Istanbul'` literal'leri (dengesizlik, kgup) — F4-D'de dokunulmadı; `kgup_kesim_sql` gibi
  üretici bir yardımcıya taşınması sonraki rötuş.
- `skill_daily.date` UTC günü (madde 4) — belgelendi, değiştirilmedi.
- Web yükleme sihirbazında `damga_tipi` seçimi yok (API alanı var); F4-K.
