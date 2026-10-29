# Uzlaştırma kuralı paketi — v2.501 (29.10.2026, canlı)

Commit `adafd74`, CI #610 (4 dk 22 s), dağıtım `ssh` ile api + worker + web imajları (alembic YOK). Canlı: 22/22 JS/CSS ve
index.html referans derlemeyle birebir; `/yontem` 200; canlı api kapsayıcısında `kurallar.kural(1.11.2026)` →
`edt-2026-V100-edta_ayrik+kupst-14907`; worker yeni cron ile başladı (12:35 UTC `kgup_teslim_kontrol`).

Ne değişti, neden, kanıt: commit mesajı. Ayrıntılı raporlar (depo dışı, ürün stratejisi klasörü):
`~/Desktop/PVQuant_GES_Piyasa_Arastirmasi/PVQuant_Urun_Stratejisi/PVQuant_Ilk_Uygulama/` — 01 bulgu doğrulama (birincil
kaynak tablosu), 02 uygulanan değişiklikler (08 paketi M1–M10), 03 test ve kabul (54 vektör, altın çıktı, üç motor),
04 açık konular ve sonraki paket, `kanit/` (kareler, kapı çıktıları, vektör betiği, SHA-256 manifesti).

## Canlıda bekleyen (dağıtım sonrası yapılacak)
- EPİAŞ kimliği tanımlıysa `piyasa_service.geri_doldur()` ile geçmiş fiyat + **sistem yönü** (önceki sürüm yön yazmıyordu).
- `kgup_teslim_kontrol` işinin ilk koşusu (12:35 UTC) `jobs_log`'da; kural seçili santralde alarm.
- F-06 arşiv göçü (`alembic/taslak/`) ayrı mühürde; F-08 DSG motoru sonraki paket.

## Dersler
- Yerel `pvquant-db-1` şeması depo göç geçmişiyle uyumsuz (silinmiş v2417'ye işaret) → DB testleri izole kapsayıcıda
  (`docker run postgres` + `PVQ_DB_URL` + `python -m alembic upgrade head`; `.venv/bin/alembic` shebang bozuk).
- EPİAŞ `system-direction` metindir; `seri()` sayıya çevirip NaN yazıyordu — bulgu kaynağı bekçi değil kod okuma.
- Playwright: scratchpad'e `playwright@latest`, `~/Library/Caches/ms-playwright`'taki mevcut tarayıcılarla; sürüm sabitlemek
  saatlerce indirme bekletti.
