
### Tema kipi: acik (CPU 1×, değerler «önce → sonra»)

**Soğuk ilk ziyaret**

| Sayfa | başlık (h1) ms | ilk içerik ms | tam ms | istek | CLS |
|---|---|---|---|---|---|
| Portföy | 70 → 23 | 350 → 310 | 1086 → 1035 | 10 → 10 | 0.0003 → 0.0003 |
| Veri yükleme | 33 → 25 | 33 → 25 | 33 → 25 | 2 → 2 | 0.0678 → 0.0678 |
| Kalibrasyon | 639 → 235 | 639 → 236 | 639 → 635 | 5 → 5 | 0 → 0 |
| Tahminler | 376 → 84 | 376 → 84 | 377 → 392 | 2 → 2 | 0 → 0.0018 |
| Doğruluk | 987 → 342 | 987 → 342 | 987 → 742 | 8 → 8 | 0 → 0.0143 |
| Aylık beklenti | 872 → 340 | 873 → 340 | 873 → 840 | 2 → 2 | 0 → 0.0005 |
| Raporlar | 24 → 25 | 24 → 25 | 24 → 25 | 0 → 0 | 0 → 0 |
| Hakkında | 8 → 10 | 175 → 177 | 175 → 177 | 1 → 1 | 0 → 0 |

**Sıcak tekrar (<60 sn, medyan/3)**

| Sayfa | başlık (h1) ms | ilk içerik ms | tam ms | istek | CLS |
|---|---|---|---|---|---|
| Portföy | 48 → 26 | 48 → 26 | 56 → 39 | 0 → 0 | 0.0003 → 0.0003 |
| Santralim | 55 → 23 | 55 → 23 | 55 → 23 | 0 → 0 | 0 → 0 |
| Veri yükleme | 25 → 10 | 25 → 10 | 25 → 10 | 0 → 0 | 0.0678 → 0.0678 |
| Kalibrasyon | 38 → 15 | 38 → 15 | 38 → 51 | 0 → 0 | 0 → 0.0127 |
| Tahminler | 46 → 51 | 46 → 52 | 46 → 61 | 0 → 0 | 0 → 0.0077 |
| Doğruluk | 13 → 18 | 13 → 18 | 13 → 22 | 0 → 0 | 0 → 0 |
| Aylık beklenti | 16 → 9 | 16 → 9 | 16 → 31 | 0 → 0 | 0 → 0.0013 |
| Raporlar | 14 → 10 | 14 → 10 | 14 → 10 | 0 → 0 | 0 → 0 |
| Hakkında | 12 → 12 | 27 → 12 | 27 → 12 | 0 → 0 | 0 → 0 |

**Bellek dolmuş dönüş (+61 sn)**

| Sayfa | başlık (h1) ms | ilk içerik ms | tam ms | istek | CLS |
|---|---|---|---|---|---|
| Portföy | 53 → 31 | 53 → 31 | 1065 → 1020 | 11 → 11 | 0.0003 → 0.0003 |
| Santralim | 283 → 20 | 283 → 20 | 283 → 20 | 11 → 8 | 0.0865 → 0 |
| Veri yükleme | 8 → 11 | 8 → 11 | 8 → 11 | 2 → 2 | 0.0678 → 0.0678 |
| Kalibrasyon | 671 → 7 | 671 → 7 | 671 → 623 | 5 → 5 | 0 → 0.0127 |
| Tahminler | 464 → 47 | 464 → 47 | 464 → 407 | 5 → 5 | 0 → 0.0018 |
| Doğruluk | 940 → 13 | 941 → 13 | 941 → 743 | 8 → 8 | 0 → 0.0523 |
| Aylık beklenti | 822 → 9 | 822 → 9 | 822 → 841 | 3 → 3 | 0 → 0.0011 |
| Raporlar | 10 → 9 | 10 → 9 | 10 → 9 | 1 → 1 | 0.0092 → 0.0092 |
| Hakkında | 9 → 13 | 176 → 14 | 176 → 14 | 1 → 1 | 0 → 0 |

**Geri dönüş (A → B → A)**

| Sayfa | başlık (h1) ms | ilk içerik ms | tam ms | istek | CLS |
|---|---|---|---|---|---|
| Doğruluk → Tahminler → Doğruluk | 48 → 13 | 48 → 13 | 48 → 14 | — | 0 → 0 |
| Kalibrasyon → Santralim → Kalibrasyon | 59 → 15 | 59 → 15 | 60 → 55 | — | 0 → 0.0127 |
| Aylık beklenti → Raporlar → Aylık beklenti | 11 → 12 | 11 → 12 | 11 → 41 | — | 0 → 0.0013 |
| Portföy → Hakkında → Portföy | 15 → 19 | 15 → 19 | 46 → 27 | — | 0.0003 → 0.0003 |

**Hızlı ardışık 3×9** — süre ms / heap MB: önce 14997/15 · 2982/18 · 3030/18 → sonra 15032/14 · 2980/16 · 2947/16

**Konsol/istisna**: önce 0 → sonra 0

### Tema kipi: oto (CPU 1×, değerler «önce → sonra»)

**Soğuk ilk ziyaret**

| Sayfa | başlık (h1) ms | ilk içerik ms | tam ms | istek | CLS |
|---|---|---|---|---|---|
| Portföy | 71 → 25 | 361 → 313 | 1086 → 1043 | 10 → 10 | 0.0003 → 0.0003 |
| Veri yükleme | 34 → 18 | 34 → 18 | 34 → 18 | 2 → 2 | 0.0678 → 0.0678 |
| Kalibrasyon | 638 → 233 | 639 → 234 | 639 → 633 | 5 → 5 | 0 → 0 |
| Tahminler | 407 → 86 | 407 → 86 | 407 → 390 | 2 → 2 | 0 → 0.0018 |
| Doğruluk | 1010 → 340 | 1010 → 340 | 1010 → 740 | 8 → 8 | 0 → 0.0143 |
| Aylık beklenti | 873 → 340 | 873 → 340 | 873 → 840 | 2 → 2 | 0 → 0.0005 |
| Raporlar | 24 → 25 | 24 → 25 | 24 → 25 | 0 → 0 | 0 → 0 |
| Hakkında | 8 → 9 | 175 → 175 | 175 → 175 | 1 → 1 | 0 → 0 |

**Sıcak tekrar (<60 sn, medyan/3)**

| Sayfa | başlık (h1) ms | ilk içerik ms | tam ms | istek | CLS |
|---|---|---|---|---|---|
| Portföy | 31 → 30 | 31 → 30 | 58 → 45 | 0 → 0 | 0.0003 → 0.0003 |
| Santralim | 34 → 37 | 34 → 37 | 34 → 38 | 0 → 0 | 0 → 0 |
| Veri yükleme | 25 → 13 | 25 → 13 | 26 → 13 | 0 → 0 | 0.0678 → 0 |
| Kalibrasyon | 48 → 13 | 48 → 13 | 48 → 55 | 0 → 0 | 0 → 0.0127 |
| Tahminler | 28 → 44 | 28 → 44 | 28 → 61 | 0 → 0 | 0 → 0.0077 |
| Doğruluk | 11 → 11 | 11 → 11 | 11 → 11 | 0 → 0 | 0 → 0 |
| Aylık beklenti | 11 → 12 | 11 → 12 | 11 → 40 | 0 → 0 | 0 → 0.0013 |
| Raporlar | 9 → 15 | 9 → 15 | 9 → 15 | 0 → 0 | 0.0092 → 0 |
| Hakkında | 12 → 14 | 12 → 14 | 12 → 14 | 0 → 0 | 0 → 0 |

**Bellek dolmuş dönüş (+61 sn)**

| Sayfa | başlık (h1) ms | ilk içerik ms | tam ms | istek | CLS |
|---|---|---|---|---|---|
| Portföy | 43 → 39 | 43 → 39 | 1051 → 1028 | 11 → 11 | 0.0003 → 0.0003 |
| Santralim | 304 → 55 | 304 → 55 | 304 → 55 | 11 → 8 | 0.0865 → 0 |
| Veri yükleme | 12 → 9 | 12 → 9 | 12 → 9 | 2 → 2 | 0.0678 → 0.0678 |
| Kalibrasyon | 653 → 10 | 654 → 10 | 654 → 641 | 5 → 5 | 0 → 0.0127 |
| Tahminler | 425 → 65 | 425 → 65 | 425 → 425 | 5 → 5 | 0 → 0.0018 |
| Doğruluk | 940 → 15 | 940 → 15 | 940 → 760 | 8 → 8 | 0 → 0.0523 |
| Aylık beklenti | 817 → 22 | 817 → 22 | 817 → 838 | 3 → 3 | 0 → 0.0011 |
| Raporlar | 8 → 9 | 8 → 9 | 8 → 9 | 1 → 1 | 0.0092 → 0.0092 |
| Hakkında | 12 → 9 | 174 → 9 | 174 → 9 | 1 → 1 | 0 → 0 |

**Geri dönüş (A → B → A)**

| Sayfa | başlık (h1) ms | ilk içerik ms | tam ms | istek | CLS |
|---|---|---|---|---|---|
| Doğruluk → Tahminler → Doğruluk | 45 → 17 | 45 → 17 | 45 → 17 | — | 0 → 0 |
| Kalibrasyon → Santralim → Kalibrasyon | 38 → 11 | 38 → 11 | 38 → 23 | — | 0 → 0.0127 |
| Aylık beklenti → Raporlar → Aylık beklenti | 12 → 13 | 12 → 13 | 12 → 30 | — | 0 → 0.0013 |
| Portföy → Hakkında → Portföy | 20 → 20 | 20 → 20 | 41 → 43 | — | 0.0003 → 0.0003 |

**Hızlı ardışık 3×9** — süre ms / heap MB: önce 15004/16 · 3065/16 · 3065/18 → sonra 14985/17 · 3086/16 · 3042/14

**Konsol/istisna**: önce 0 → sonra 0

### Tema kipi: koyu (CPU 1×, değerler «önce → sonra»)

**Soğuk ilk ziyaret**

| Sayfa | başlık (h1) ms | ilk içerik ms | tam ms | istek | CLS |
|---|---|---|---|---|---|
| Portföy | 50 → 30 | 338 → 328 | 1067 → 1047 | 10 → 10 | 0.0003 → 0.0003 |
| Veri yükleme | 20 → 28 | 21 → 28 | 21 → 28 | 2 → 2 | 0.0678 → 0.0678 |
| Kalibrasyon | 635 → 233 | 636 → 234 | 636 → 634 | 5 → 5 | 0 → 0 |
| Tahminler | 387 → 78 | 387 → 78 | 387 → 389 | 2 → 2 | 0 → 0.0018 |
| Doğruluk | 980 → 340 | 981 → 340 | 981 → 739 | 8 → 8 | 0 → 0.0143 |
| Aylık beklenti | 868 → 342 | 868 → 342 | 868 → 842 | 2 → 2 | 0 → 0.0005 |
| Raporlar | 26 → 25 | 26 → 25 | 26 → 25 | 0 → 0 | 0 → 0 |
| Hakkında | 8 → 10 | 175 → 177 | 175 → 177 | 1 → 1 | 0 → 0 |

**Sıcak tekrar (<60 sn, medyan/3)**

| Sayfa | başlık (h1) ms | ilk içerik ms | tam ms | istek | CLS |
|---|---|---|---|---|---|
| Portföy | 30 → 32 | 30 → 32 | 40 → 43 | 0 → 0 | 0.0003 → 0.0003 |
| Santralim | 48 → 41 | 48 → 41 | 48 → 41 | 0 → 0 | 0 → 0 |
| Veri yükleme | 41 → 10 | 41 → 10 | 41 → 10 | 0 → 0 | 0 → 0.0678 |
| Kalibrasyon | 46 → 10 | 46 → 10 | 46 → 49 | 0 → 0 | 0 → 0.0127 |
| Tahminler | 53 → 24 | 53 → 24 | 53 → 68 | 0 → 0 | 0 → 0.0077 |
| Doğruluk | 14 → 10 | 14 → 10 | 14 → 25 | 0 → 0 | 0 → 0.038 |
| Aylık beklenti | 21 → 25 | 21 → 25 | 21 → 27 | 0 → 0 | 0 → 0 |
| Raporlar | 11 → 10 | 11 → 10 | 11 → 10 | 0 → 0 | 0 → 0 |
| Hakkında | 11 → 15 | 26 → 15 | 26 → 15 | 0 → 0 | 0 → 0 |

**Bellek dolmuş dönüş (+61 sn)**

| Sayfa | başlık (h1) ms | ilk içerik ms | tam ms | istek | CLS |
|---|---|---|---|---|---|
| Portföy | 59 → 22 | 59 → 22 | 1045 → 1036 | 11 → 11 | 0.0003 → 0.0003 |
| Santralim | 293 → 30 | 293 → 30 | 293 → 30 | 11 → 8 | 0.0865 → 0 |
| Veri yükleme | 10 → 10 | 10 → 10 | 10 → 10 | 2 → 2 | 0.0678 → 0.0678 |
| Kalibrasyon | 654 → 13 | 654 → 13 | 655 → 639 | 5 → 5 | 0 → 0.0127 |
| Tahminler | 430 → 50 | 430 → 50 | 430 → 408 | 5 → 5 | 0 → 0.0018 |
| Doğruluk | 942 → 12 | 942 → 12 | 942 → 740 | 8 → 8 | 0 → 0.0523 |
| Aylık beklenti | 828 → 21 | 829 → 21 | 829 → 821 | 3 → 3 | 0 → 0.0011 |
| Raporlar | 9 → 8 | 9 → 8 | 9 → 8 | 1 → 1 | 0.0092 → 0.0092 |
| Hakkında | 13 → 10 | 172 → 10 | 172 → 10 | 1 → 1 | 0 → 0 |

**Geri dönüş (A → B → A)**

| Sayfa | başlık (h1) ms | ilk içerik ms | tam ms | istek | CLS |
|---|---|---|---|---|---|
| Doğruluk → Tahminler → Doğruluk | 59 → 14 | 59 → 14 | 59 → 64 | — | 0 → 0.038 |
| Kalibrasyon → Santralim → Kalibrasyon | 55 → 15 | 55 → 16 | 55 → 43 | — | 0 → 0.0127 |
| Aylık beklenti → Raporlar → Aylık beklenti | 14 → 12 | 14 → 12 | 15 → 13 | — | 0 → 0 |
| Portföy → Hakkında → Portföy | 14 → 13 | 14 → 13 | 61 → 13 | — | 0.0003 → 0 |

**Hızlı ardışık 3×9** — süre ms / heap MB: önce 15033/15 · 3080/18 · 3081/18 → sonra 15015/16 · 3068/14 · 2994/16

**Konsol/istisna**: önce 0 → sonra 0
