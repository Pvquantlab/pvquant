# WebKit tam sayfa görüntüsü gürültüsü — aynı «sonra» derlemesinin iki çekimi

Komut: `node olc/ekran.mjs --hedef sonra --cikti analiz/webkit-tekrar(2) --motor webkit`, ardından `node olc/piksel-bant.mjs …`. Görüntüler depoda değil (boyut).

## 390x844 — tekrar1 ↔ tekrar2
```
boy 37626 → 37626 (CSS 12542 → 12542)
üstten hizalı fark bantları (sonra koordinatı): CSS y 2197–2397 (253845 px)
```
## 768x1024 — tekrar1 ↔ tekrar2
```
boy 20454 → 20454 (CSS 10227 → 10227)
üstten hizalı fark bantları (sonra koordinatı): CSS y 2396–2556 (688 px) · CSS y 2573–2606 (346 px)
```
## 1440x900 — tekrar1 ↔ tekrar2
```
boy 15226 → 15226 (CSS 7613 → 7613)
üstten hizalı fark bantları (sonra koordinatı): yok
```
## 1920x1080 — tekrar1 ↔ tekrar2
```
boy 7702 → 7702 (CSS 7702 → 7702)
üstten hizalı fark bantları (sonra koordinatı): CSS y 1873–2053 (12925 px) · CSS y 3258–3459 (30143 px)
```
