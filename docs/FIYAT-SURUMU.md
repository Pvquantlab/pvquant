# Fiyat sürümü ve finansal motor sınırı (v2.601, Faz 4 F4-G)

## Sorun (bulgu M6)

`piyasa_fiyat` saatlik PTF/SMF/yön tablosu üzerine yazılır: gün öncesi PTF (`epias_gop`, SMF/yön yok) gece tam satırla değişir, geri doldurma ve
EPİAŞ düzeltmeleri satırı günceller. Kayıtlı bir finansal sonucun hangi fiyatla hesaplandığı kaybolur; aynı dönemin yeniden hesabı eski sonucu
üretmeyebilir.

## Çözüm

- **`piyasa_fiyat_surum`** (göç v2601, yalnız ekleme): `piyasa_service.kaydet` güncel tabloyu yazdıktan sonra, saatin güncel satırı son sürümden
  **farklıysa** yeni sürüm ekler (`SURUM_EKLE_SQL`; aynı değer tekrar yazılmaz, günlük 3 günlük yeniden çekim tabloyu şişirmez). Tek seferlik doldurma:
  mevcut satırlar `alinma = guncelleme` ile ilk sürüm. Uygulama rolü UPDATE/DELETE yapamaz.
- **`fiyatlar(index, itibariyle=None)`**: `itibariyle` verilirse o anda geçerli sürüm (`DISTINCT ON (ts_utc) … alinma <= T`); sürümü olmayan saat
  «senaryo» (uydurulmaz). None → güncel görünüm; mevcut okuyucular değişmez.
- **`fiyat_sha16(df)`**: içerik damgası (saat, ptf, smf, yön, kaynak; 1e-6). `surum_tarihcesi(ts)` bir saatin sürümleri.

## Sonuç meta'sı (FEM `ozet`, `cikti_surumu` 1.1)

- `hesap_durumu`: `tam` (beklenen saatlerin hepsi ölçülü, hepsi EPİAŞ fiyatlı) · `kismi` (ölçüm ya da fiyat eksik, yön varsayımı) · `senaryo`
  (pozisyon senaryosu ya da fiyatın tamamı senaryo) · `hesaplanamadi` (ölçüm yok).
- `girdi`: `olcum {tablo, saat, son_alinma, kaynaklar, sha16, sinir, sayac {saat, son_alinma, kaynaklar} | null}` (sayaç girdisinde sayaç künyesi de), `program {sha16, kaynak, bildirilen/öneri/tamamlanan saat, kosular (Faz 1 program
  kuralı seçicisinin koşu kimlikleri; seçim `girdiler` içinde BİR kez okunur, öneri tamamlama aynı seçimi kullanır), not}`, `fiyat {sha16, itibariyle, epias_saat, senaryo_saat}`, `ayar_sha16` (tarife, segment, katsayılar,
  pozisyon, LÜY, arıza sayısı, üretim girdisi), `sozlukler {fem, finans, kalite, kural_sicili_sha, kural_sicili_surumu}` (fem = derleme sürümü; düzeltme sonrası sha değişir, gece işi yeniden yazar), bileşik `sha16`.
- `fiyat` özeti `sha16` ve `itibariyle` taşır. `gecmis()` satırları `girdi_sha16`, `hesap_durumu`, `cikti_surumu` verir.
- **Deterministiklik**: aynı girdi → aynı sonuç (hesap zamanı hariç bayt eşit) ve aynı `girdi.sha16` (`tests/test_fiyat_surumu_v2601.py`).
- **Yeniden kurma**: `ozet(..., itibariyle=kayit.meta.hesap_zamani)` fiyatı o andaki sürümle okur (M6 kapandı). Ölçüm ve program için sürüm tablosu
  yok; `olcum.son_alinma` ve `program.kosular` referanstır (arşiv değişmez: F4-B).

## Tekrar edilmeyen hesap

- `gece_finansal_etki`: `ayni_girdili_kayit` — aynı dönem sonu/üretim girdisiyle son kaydın `girdi.sha16` aynıysa yeni satır yazılmaz
  («girdi değişmedi, kayıt … geçerli»).
- `gece_portfoy`: DSG dönemi **bir kez** hesaplanır (`sd.donem`), hem `dsg` kaydına hem `pfs.donem(dsg_sonuc=…)` finans satırına verilir
  (Faz 3 inceleme 5–6). `fe.portfoy()` ve `pfs.donem` zaten `son()` kaydını kullanır (v2.594).
- Portföy finans meta: `cikti_surumu`, `hesap_durumu` (en zayıf üye; DSG senaryo/kismi ise o), `girdi {santraller {kaynak, kayit_id, girdi_sha16,
  hesap_durumu}, dsg_fiyat, sha16}`. DSG meta: `fiyat.sha16`, `hesap_durumu`, `cikti_surumu`.

## API

- `GET /v1/piyasa/fiyat?bas&bitis&itibariyle=` (ISO zaman; verilirse o andaki sürüm) ve `GET /v1/piyasa/fiyat-surumleri?ts=` (bir saatin sürümleri).
- `GET /v1/plants/{id}/finansal-etki?...&itibariyle=` kayıtlı sonucun fiyat sürümüyle yeniden hesap (kaydedilmez).

## Yapılmayan

- Ölçüm ve program girdileri için sürüm tablosu (arşiv zaten değişmez; SCADA geri doldurma `alinma_zamani` ile izlenir).
- Eski kayıtlar (`cikti_surumu` yok = 1.0) geriye dönük damgalanmaz; `gecmis()` boş alan döner.
