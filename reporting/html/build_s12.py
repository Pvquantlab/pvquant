from pvq import *

th = lambda x: "{:,}".format(int(round(x))).replace(",", ".")
YILLAR = list(range(2007, 2027))
AYMIN = [min(IKLIM[y][m] for y in TAM_YILLAR) for m in range(12)]
AYMAX = [max(IKLIM[y][m] for y in TAM_YILLAR) for m in range(12)]


def ton(v, m):
    t = min(1.0, max(0.0, (v - AYMIN[m]) / (AYMAX[m] - AYMIN[m]))) ** 0.88
    a, b = (254, 251, 245), (196, 158, 82)
    return "#%02X%02X%02X" % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


rows = ""
for y in YILLAR:
    hucre = ""
    for m in range(12):
        v = IKLIM[y][m]
        if v is None:
            hucre += '<td class="na">–</td>'
        else:
            hucre += '<td style="background:%s">%s</td>' % (ton(v, m), th(v))
    tam = all(x is not None for x in IKLIM[y])
    hucre += ('<td class="yil">%s</td>' % th(sum(IKLIM[y])) if tam
              else '<td class="yil na">–</td>')
    rows += '<tr><td class="yl">%d</td>%s</tr>' % (y, hucre)

lta = "".join('<td>%s</td>' % th(v) for v in LTA_AY)
rows += ('<tr class="lta"><td class="yl">Ortalama</td>%s<td class="yil">%s</td></tr>'
         % (lta, th(LTA_YIL)))

steps = "".join('<span style="background:%s"></span>'
                % ("#%02X%02X%02X" % tuple(round((254, 251, 245)[i] +
                   ((196, 158, 82)[i] - (254, 251, 245)[i]) * (k / 11) ** 0.88)
                   for i in range(3))) for k in range(12))

CSS = """
table{border-collapse:collapse;width:100%;margin-top:2.5mm;table-layout:fixed}
th{background:BRAND;color:#fff;font-weight:600;font-size:7.4pt;padding:1.7mm .5mm;
  text-align:center}
th:first-child{text-align:left;padding-left:2mm;width:15mm}
th:last-child{width:17mm}
td{font-size:7.2pt;padding:1.25mm .5mm;text-align:center;font-variant-numeric:tabular-nums;
  border:.4pt solid #fff;color:INK}
td.yl{text-align:left;padding-left:2mm;font-family:PlexMono;font-size:7pt;color:SEC;
  background:#fff;border-left:0}
td.yil{font-weight:600;background:#EDF1F3}
td.na{color:#9AA5AB;background:#FCFBF8}
tr.lta td{border-top:.9pt solid BRAND;font-weight:600;background:#EDF1F3}
tr.lta td.yl{color:INK;font-family:PlexSans;font-size:7.4pt}
tr:nth-child(even) td{background:none}
.scale{display:flex;align-items:center;gap:3mm;margin-top:3mm;font-size:7.9pt;
  font-weight:600;color:INK}
.scale .ramp{display:flex;flex:none}
.scale .ramp span{display:inline-block;width:5mm;height:2.8mm}
.scale .na{margin-left:auto;font-weight:400;color:SEC}
.tcap{font-size:8pt;font-weight:600;margin-top:6mm}
.tcap span{font-weight:500;color:INK}
.two{display:flex;gap:11mm;margin-top:6mm}
.two > div{flex:1}
.two h2{font-size:10.5pt;font-weight:600;padding-bottom:2mm;border-bottom:.9pt solid BRAND;
  margin-bottom:3mm}
.two p{font-size:9pt;line-height:1.55;margin-top:0}
""".replace("BRAND", BRAND).replace("SEC", SEC).replace("INK", INK)

BODY = """<div class="page"><div class="sheet">
""" + HEAD + """
  <div class="eyebrow">İklim bağlamı · devam</div>
  <h1>Yıl × ay üretim matrisi</h1>
  <p class="lead" style="max-width:162mm">Yirmi yılın tamamı tek çizelgede. Her hücre bir ayın
  toplam üretimidir; rengi, o hücrenin aynı ayın kendi 19 yıllık dağılımı içindeki yerini
  gösterir. Böylece Ocak ayı Temmuz'la değil, diğer Ocak aylarıyla karşılaştırılır.</p>

  <div class="tcap">Çizelge 12.1 <span>Aylık üretim [MWh], 2007–2026</span></div>
  <table>
    <tr><th>Yıl</th>""" + "".join("<th>%s</th>" % a for a in AY_TR) + """<th>Yıl</th></tr>
    """ + rows + """
  </table>
  <div class="scale">
    <span>ayın kurağı</span><span class="ramp">""" + steps + """</span>
    <span>ayın parlağı</span>
    <span class="na">tamamlanmamış ay: –</span>
  </div>

  <div class="two">
    <div>
      <h2>Matris nasıl okunur?</h2>
      <p>Satırlar yılları, sütunlar ayları verir. Bir satır boyunca koyu hücrelerin çokluğu o
      yılın genel olarak parlak geçtiğini, bir sütun boyunca açık hücreler o ayın o yıllarda
      zayıf kaldığını gösterir. Son satır 19 tam yılın ortalamasıdır ve sayfa 11'deki iklim
      zarfının orta çizgisiyle aynı değerlerdir.</p>
    </div>
    <div>
      <h2>2026 neden eksik?</h2>
      <p>Matris kısmi bir ayı tam ay gibi göstermez. 2026'nın Ağustos ayı devam ettiği için o
      hücre ve sonrası “–” ile basılır; yıl toplamı da hesaplanmaz. Aynı nedenle 2026 satırı,
      ortalamanın ve renk ölçeğinin hesabına dahil edilmemiştir — ölçek yalnızca 19 tam yıldan
      türetilir.</p>
    </div>
  </div>
""" + foot(12) + """
</div></div>"""

build("PVQuant_Konya_GES_s12_yil_ay_matrisi", CSS, BODY,
      "PVQuant — Konya GES · Yıl × ay matrisi")
