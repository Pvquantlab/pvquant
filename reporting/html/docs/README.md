# PVQuant Rapor Motoru

16 sayfalık "Üretim Tahmini ve Doğruluk Raporu"nu HTML ve PDF olarak üretir.
Depoda `reporting/html/` altına yerleştirilmek üzere hazırlanmıştır.

## Kurulum

```bash
pip install -r gereksinimler.txt
```

WeasyPrint'in sistem bağımlılıkları (pango, cairo) gerekir. Debian/Ubuntu'da:

```bash
apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libcairo2
```

## Çalıştırma

```bash
python3 uret.py                 # 16 sayfa + birleşik HTML/PDF
python3 build_s07.py            # tek sayfa (hızlı deneme)
python3 merge_html.py           # yalnızca birleştirme
```

Çıktılar varsayılan olarak `./cikti` altına yazılır:

```
PVQuant_Konya_GES_s01_kapak.html/.pdf   … s16 …
PVQuant_Konya_GES_RAPOR_16sayfa.html    tek dosya, fontlar gömülü
PVQuant_Konya_GES_RAPOR_16sayfa.pdf
```

Yolları değiştirmek için:

```bash
PVQ_CIKTI=/tmp/rapor PVQ_FONTLAR=/opt/fontlar python3 uret.py
```

## CI adımı

`uret.py` bir sayfa tek A4'e sığmazsa **çıkış kodu 1** döndürür ve taşan sayfaları listeler.
Doğrudan CI adımı olarak koşturulabilir:

```yaml
- run: python3 reporting/html/uret.py
```

Taşma, raporun en sık karşılaşılan bozulma biçimidir: içerik sessizce kırpılır ve genellikle
altbilgi ile son çizelge kaybolur. Bu kontrol olmadan bozulma gözden kaçar.

## Dosya yapısı

```
pvq.py              Ortak modül. Palet, gömülü fontlar, temel CSS, üstbilgi/altbilgi,
                    build(), grafik motorları (fan_chart, bar_chart, band_columns),
                    19 yıllık iklim arşivi.
build_s01.py …16    Sayfa üreticileri. Her biri kendi verisini, CSS'ini ve gövdesini
                    taşır; pvq.build() ile tek sayfalık HTML + PDF yazar.
merge_html.py       16 sayfayı tek HTML'de birleştirir. Her sayfanın CSS'ini #pNN
                    altında kapsüller, böylece aynı adlı kurallar çakışmaz.
uret.py             Tümünü sırayla koşturur, taşma denetimi yapar.
fontlar/            IBM Plex Sans 400/500/600, IBM Plex Mono 400,
                    Source Serif 4 600/700. latin + latin-ext birleştirilmiş tam TTF.
```

## Fontlar hakkında

Yazı tipleri belgeye base64 olarak gömülür; çıktı HTML'in dış bağımlılığı yoktur.

**Alt-küme (subset) font dosyaları kullanılamaz.** Google Fonts'un `latin` ve `latin-ext`
dosyaları `unicode-range` ile ayrılmıştır ve bazı PDF motorları bu ayrımı çözemez; sonuçta
"Ağustos" → "A, ustos" gibi bozulmalar olur. `fontlar/` altındaki dosyalar iki alt-kümenin
fontTools ile birleştirilmiş hâlidir. Yeni bir ağırlık gerekirse aynı yöntemle üretilmelidir:

```python
from fontTools.ttLib import TTFont
from fontTools.merge import Merger
for src, dst in ((latin_woff2, "a.ttf"), (latin_ext_woff2, "b.ttf")):
    f = TTFont(src); f.flavor = None; f.save(dst)
Merger().merge(["a.ttf", "b.ttf"]).save("fontlar/Yeni-700.ttf")
```

## JSON v2.0 bağlantısı

Şu anda her sayfanın verisi kendi betiğinin başında sabit olarak duruyor. Hangi değişkenin
hangi alana karşılık geldiği `veri_haritasi.md` dosyasında listelenmiştir; adaptör yazılırken
tek referans o dosyadır.

Önerilen sıra:

1. `veri.py` adında tek bir modül oluşturun; `veri_haritasi.md`'deki tüm değişkenleri oraya
   taşıyın.
2. Her `build_sXX.py` dosyasının başındaki sabitleri `from veri import …` ile değiştirin.
3. `veri.py`'yi JSON v2.0 çıktısından dolduran bir adaptör yazın.

Bu sıra önemlidir: önce tek bir veri yüzeyi oluşturur, sonra onu beslersiniz. Betiklerin
içindeki sabitleri tek tek JSON'a bağlamak, 16 ayrı bağlantı noktası demektir.

## Değiştirilmemesi gerekenler

- Palet ve tipografi `pvq.py` içindedir; sayfa betiklerinde renk kodu yazılmamalıdır.
- Kum tonu (`FAN_AREA`) yalnızca belirsizlik ve büyüklük içindir; amber ve kırmızı yalnızca
  durum göstermek için kullanılır.
- Eksik veri hiçbir koşulda sıfırla doldurulmaz, "—" basılır.

Ayrıntılı gerekçeler ve kontrol listesi için `PVQuant_rapor_uretim_kilavuzu.md` dosyasına bakın.
