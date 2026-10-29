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

---

# İkinci paket — v2.502 (29.10.2026 gece, canlı): KGÜP sürüm arşivi (F-06) + DSG netleşmesi (F-08)

Commit `b74cd8b`, CI #612 (4 dk 19 s). Dağıtım: api + web imajları + **`alembic upgrade head` → v2502_kgup_surum**. Canlı: 22/22 JS/CSS ve
index.html birebir; `kgup_surum` tablosu var, `pvq_app` yetkileri yalnız SELECT/INSERT (değiştirilemez), `pvq_api` S/I/U/D; api günlüğü hatasız.

**DERS (göç):** `docker compose run --rm api python -m alembic upgrade head` **pvq_api** ile koşar ve `permission denied for schema public` verir
(pvq_api'nin CREATE yetkisi yok, v2488 tasarımı). Göç veritabanı sahibiyle koşmalı:
`set -a; . ./.env; set +a; docker compose run --rm -e PVQ_DB_URL="postgresql+psycopg://pvquant:${DB_PASSWORD}@db:5432/pvquant" api python -m alembic upgrade head`
(.env'de 47. satır `PVQ_SMTP_FROM=PVQuant <…>` `source` ile sözdizimi hatası verir ama DB_PASSWORD ondan önce okunur; kalıcı çözüm: değeri tırnaklamak).
İlk denemede api yeni kodla göçsüz ayağa kalktı (CSV indirme o aralıkta 500 verirdi; ~1 dk).

Ayrıntı: `PVQuant_Ilk_Uygulama/02` M11–M12, `03` §7a, `04` (kalan: F-07 geri test maliyet tarafı, müşteri KGÜP içe alma, canlı EPİAŞ kimliği).

# Üçüncü paket — v2.503 (29.10.2026 gece, canlı): uzlaştırma kalemleri geri testi (F-07) + müşterinin bildirdiği KGÜP (F-06 tamamlayıcı)

Commit `2011556`, CI #614 (7 dk 34 s; test işi 7 dk 32 s — yeni C geri test takımı süreyi uzattı). Dağıtım: api + web imajları +
**`alembic upgrade head` DB sahibiyle → v2503_kgup_surum_kaynak** (ilk denemede temiz; v2.502 dersi uygulandı). Worker imajı yenilenmedi
(değişen modüller yalnız api yolunda; worker cron işleri dokunulmadı). Canlı: index.html ve 22/22 JS/CSS birebir; api günlüğü hatasız;
`backtest_service.maliyet_geri_test`, `kgup_arsiv_service.musteri_kaydet/kiyas` canlı kapsayıcıda; yeni uçlar kimliksiz 422 (başlık zorunlu),
sahte jetonla 401, olmayan yol 404.

**Ne:** `GET /v1/plants/{id}/dengesizlik/geri-test?gun=` (Doğruluk kartı «Uzlaştırma kalemleri geri testi — son 12 ay»; başlık «varsayımsal
yeniden hesap; EPİAŞ uzlaştırma sonucu değildir»); `kgup_surum.kaynak` (pvquant | musteri), `POST …/kgup/bildirilen?gun=` (CSV, editör),
`GET …/kgup/kiyas?gun=` (Tahminler «Bildirilen KGÜP ile kıyas»). Karşı-olgu: `parametre_cercevesi(karsi_olgu="2026"|"2026_V100")`.

**Kanıt:** `tests/test_c_geri_test.py` C T1 beş seviye (W15 911.844 = 420.732 + 388.115 + 102.997), T6 S3 (3.202.845 / 3.483.043 / 414.994 /
280.198), karşı-olgu (634.526 / 805.767 / 949.292) ±1 TL birebir; pytest 763 geçti / 1 atlandı (izole DB, göç ileri-geri temiz); web tsc 0,
102 test, oxlint 16/0, build ok. Kareler `PVQuant_Ilk_Uygulama/kanit/kareler/dogruluk-geritest-*`, `tahminler-arsiv-*`.

**Ders:** `.gitignore`'daki `data/` deseni `tests/data/` fixture'larını yok sayıyordu (eski fixture'lar `-f` ile girmiş); `!tests/data/` eklendi.

**Kalan:** canlı EPİAŞ kimliği/yön geçmişi kontrolü (üretim okuma izni); 24 ay saklama/temizlik işi; DSG üyelere dağıtım anahtarı; TPYS şablonu.
Ayrıntı: `PVQuant_Ilk_Uygulama/02` M13–M14, `03` §7b, `04`.
