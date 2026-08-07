from pvq import *

BASE_KW = [489, 1048, 2004, 3412, 5175, 6991, 8413, 9017, 8610, 7322, 5547, 3743,
           2250, 1205, 574]                      # 05–06 … 19–20 saat dilimleri
HOURS = ["%02d–%02d" % (h, h + 1) for h in range(5, 20)]
DAILY = [65.8, 65.0, 66.4, 68.3, 69.4, 67.1, 59.3, 53.6, 58.9,
         65.6, 68.8, 69.6, 67.9, 66.2, 63.5, 61.0]
DAYS = ["%02d" % d for d in range(5, 21)]
PEAK = 9600.0


def mix(t):
    """#FDF8EF → #DFC589 kum tonlaması; sayı her zaman koyu kalır."""
    a, b = (254, 251, 245), (196, 158, 82)
    t = t ** 0.88
    return "#%02X%02X%02X" % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def tr(x, d=1):
    return ("%.*f" % (d, x)).replace(",", "").replace(".", ",")


rows = ""
# gece sınırı
rows += ('<tr><td class="hr">04–05</td>'
         + "".join('<td class="na">–</td>' for _ in DAYS) + "</tr>")
for i, h in enumerate(HOURS):
    cells = ""
    for d in range(16):
        v = BASE_KW[i] * DAILY[d] / 65.8
        t = min(1.0, v / PEAK)
        cells += ('<td style="background:%s">%s</td>'
                  % (mix(t), "{:,}".format(int(round(v))).replace(",", ".")))
    rows += '<tr><td class="hr">%s</td>%s</tr>' % (h, cells)
rows += ('<tr><td class="hr">20–21</td>'
         + "".join('<td class="na">–</td>' for _ in DAYS) + "</tr>")
rows += ('<tr class="sum"><td class="hr">Σ [MWh]</td>'
         + "".join('<td>%s</td>' % tr(v) for v in DAILY) + "</tr>")

# lejant şeridi
steps = "".join('<span style="background:%s"></span>' % mix(i / 11) for i in range(12))

CSS = """
table{border-collapse:collapse;width:100%;margin-top:3mm;table-layout:fixed}
th{background:BRAND;color:#fff;font-weight:600;font-size:7.6pt;padding:1.8mm .5mm;
  text-align:center;letter-spacing:.02em}
th:first-child{text-align:left;padding-left:2mm;width:17mm}
td{font-size:7.2pt;padding:1.35mm .5mm;text-align:center;font-variant-numeric:tabular-nums;
  border:.4pt solid #fff}
td.hr{text-align:left;padding-left:2mm;font-family:PlexMono;font-size:7pt;color:SEC;
  background:#fff;border-left:0}
td.na{color:#9AA5AB;background:#FCFBF8}
tr.sum td{background:#EDF1F3;font-weight:600;font-size:7.4pt;color:INK;border-top:.9pt solid BRAND}
tr.sum td.hr{background:#EDF1F3;font-weight:600;color:INK}
.scale{display:flex;align-items:center;gap:3mm;margin-top:3mm;font-size:7.9pt;
  font-weight:600;color:INK}
.scale .ramp{display:flex;flex:none}
.scale .ramp span{display:inline-block;width:5mm;height:2.8mm}
.scale .na{margin-left:auto;font-weight:400;color:SEC}
.two{display:flex;gap:11mm;margin-top:6mm}
.two > div{flex:1}
.two h2{font-size:10.5pt;font-weight:600;padding-bottom:2mm;border-bottom:.9pt solid BRAND;
  margin-bottom:3.5mm}
.two p{font-size:9pt;line-height:1.56;margin-top:0}
.tcap{font-size:8pt;font-weight:600;margin-top:7mm}
.tcap span{font-weight:500;color:INK}
""".replace("BRAND", BRAND).replace("SEC", SEC).replace("INK", INK)

BODY = """<div class="page"><div class="sheet">
""" + HEAD + """
  <div class="eyebrow">Tahmin detayı · devam</div>
  <h1>Saat × gün matrisi</h1>
  <p class="lead" style="max-width:162mm">Aynı tahminin üçüncü görünümü: her hücre bir günün
  bir saatindeki beklenen ortalama gücü verir. Grafik biçimi gösterir, bu çizelge sayıyı verir —
  saatlik satış, dengeleme ve bakım penceresi kararları doğrudan buradan okunur.</p>

  <div class="tcap">Çizelge 6.1 <span>Saatlik beklenen güç [kW], 05–20 Ağustos 2026 ·
    yerel saat</span></div>
  <table>
    <tr><th>Saat</th>""" + "".join("<th>%s</th>" % d for d in DAYS) + """</tr>
    """ + rows + """
  </table>
  <div class="scale">
    <span>düşük</span><span class="ramp">""" + steps + """</span><span>yüksek [kW]</span>
    <span class="na">gece: –</span>
  </div>

  <div class="two">
    <div>
      <h2>Matriste ne görünür?</h2>
      <p>Sütunlar arasındaki fark gün kalitesini, satırlar arasındaki fark gün içi seyri verir.
      11–13 Ağustos sütunlarının öğle saatleri komşularından belirgin biçimde açık: cephe
      geçişinin en çok vurduğu saatler 10:00–15:00 arasıdır. Sabah ve akşam saatleri ise
      neredeyse hiç etkilenmemiştir.</p>
    </div>
    <div>
      <h2>Renk neyi gösterir?</h2>
      <p>Tek renk tonlaması: açıktan koyuya doğru artan güç. Ton, grafiklerdeki olasılık
      aralığıyla aynı kum ailesinden; sayılar her hücrede koyu basıldığı için okunabilirlik
      ton koyulaştıkça bozulmaz. Uyarı renkleri bu çizelgeye girmez — yüksek üretimin kırmızıyla
      basılması iyi bir günü sorun gibi gösterirdi. Gece saatleri sıfırla değil “–” ile
      işaretlenir.</p>
    </div>
  </div>
""" + foot(6) + """
</div></div>"""

build("PVQuant_Konya_GES_s06_saat_gun_matrisi", CSS, BODY,
      "PVQuant — Konya GES · Saat × gün matrisi")
