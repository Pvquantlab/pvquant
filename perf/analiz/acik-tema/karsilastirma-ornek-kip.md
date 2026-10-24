
### Örnek kip — acik (CPU 1×, tekrar ziyaret medyan/3; «önce → sonra»)

| Sayfa | hazır ms | görev ms | betik ms | stil ms | yerleşim ms | uzun görev |
|---|---|---|---|---|---|---|
| Portföy | 22 → 9 | 52 → 41 | 14 → 9 | 5 → 4 | 6 → 5 | 0 → 0 |
| Santralim | 55 → 36 | 77 → 59 | 35 → 24 | 6 → 5 | 10 → 7 | 0 → 0 |
| Veri yükleme | 22 → 9 | 32 → 23 | 15 → 5 | 3 → 3 | 2 → 2 | 0 → 0 |
| Kalibrasyon | 36 → 37 | 43 → 34 | 22 → 17 | 3 → 3 | 2 → 2 | 0 → 0 |
| Tahminler | 24 → 10 | 54 → 38 | 28 → 17 | 3 → 3 | 2 → 2 | 0 → 0 |
| Doğruluk | 19 → 21 | 80 → 93 | 39 → 40 | 4 → 5 | 6 → 5 | 0 → 0 |
| Aylık beklenti | 22 → 9 | 81 → 65 | 39 → 27 | 5 → 4 | 4 → 3 | 0 → 0 |
| Raporlar | 10 → 7 | 25 → 22 | 7 → 6 | 4 → 4 | 3 → 2 | 0 → 0 |
| Hakkında | 18 → 21 | 21 → 20 | 5 → 4 | 3 → 3 | 1 → 1 | 0 → 0 |

İlk ziyaret hazır ms: Portföy 42 → 34 · Santralim 35 → 45 · Veri yükleme 29 → 16 · Kalibrasyon 26 → 25 · Tahminler 33 → 27 · Doğruluk 37 → 29 · Aylık beklenti 29 → 21 · Raporlar 9 → 15 · Hakkında 8 → 19
Hızlı 3×9 süre/heap: önce 3383/14 · 3814/16 · 3800/18 → sonra 3415/14 · 3832/13 · 3879/12; konsol 0 → 0

### Örnek kip — koyu (CPU 1×, tekrar ziyaret medyan/3; «önce → sonra»)

| Sayfa | hazır ms | görev ms | betik ms | stil ms | yerleşim ms | uzun görev |
|---|---|---|---|---|---|---|
| Portföy | 12 → 19 | 31 → 40 | 7 → 8 | 2 → 4 | 3 → 4 | 0 → 0 |
| Santralim | 25 → 13 | 45 → 65 | 20 → 25 | 3 → 4 | 6 → 6 | 0 → 0 |
| Veri yükleme | 17 → 11 | 29 → 28 | 15 → 8 | 2 → 4 | 2 → 3 | 0 → 0 |
| Kalibrasyon | 25 → 25 | 23 → 21 | 11 → 6 | 2 → 2 | 1 → 2 | 0 → 0 |
| Tahminler | 21 → 25 | 45 → 54 | 16 → 19 | 2 → 4 | 1 → 2 | 0 → 0 |
| Doğruluk | 16 → 19 | 57 → 80 | 26 → 33 | 3 → 4 | 4 → 5 | 0 → 0 |
| Aylık beklenti | 13 → 19 | 48 → 70 | 23 → 30 | 3 → 5 | 3 → 4 | 0 → 0 |
| Raporlar | 11 → 9 | 20 → 25 | 4 → 6 | 2 → 4 | 2 → 2 | 0 → 0 |
| Hakkında | 26 → 21 | 18 → 21 | 6 → 4 | 2 → 3 | 1 → 1 | 0 → 0 |

İlk ziyaret hazır ms: Portföy 41 → 43 · Santralim 36 → 24 · Veri yükleme 32 → 21 · Kalibrasyon 26 → 21 · Tahminler 34 → 38 · Doğruluk 36 → 21 · Aylık beklenti 40 → 20 · Raporlar 11 → 22 · Hakkında 9 → 23
Hızlı 3×9 süre/heap: önce 3548/19 · 3894/17 · 3798/14 → sonra 3467/12 · 4013/12 · 3865/13; konsol 0 → 0
