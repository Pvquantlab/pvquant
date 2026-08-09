from pvq import *

from veri import P50_GUN as p50, HW_GUN as hw, GUN_ETIKET as days, CEPHE, GUN_YMIN, GUN_YMAX, AY_YIL

tr = lambda x, d=1: ("%.*f" % (d, x)).replace(".", ",")

CHART = fan_chart(p50, hw, days, AY_YIL + " [gün]", "[MWh/gün]",
                  ymin=GUN_YMIN, ymax=GUN_YMAX, step=10, H=290, fs=15,
                  highlight=CEPHE, hl_label="cephe geçişi")

hdr = "".join("<th class='num'>%s</th>" % d for d in days)


def rowcells(vals, bold=False):
    return "".join("<td class='num%s'>%s</td>" % (" b" if bold else "", tr(v)) for v in vals)


CSS = """
.fig{margin-top:7mm}
table{margin-top:2mm}
th{font-size:7.4pt;padding:1.6mm 1mm;text-align:right}
th:first-child{text-align:left;padding-left:2mm}
td{font-size:7.6pt;padding:1.5mm 1mm}
td:first-child{text-align:left;padding-left:2mm;color:SEC;width:26mm}
td.b{font-weight:600}
tr.mid td{background:#EAF2ED}
tr.mid td:first-child{color:INK;font-weight:500}
.tcap{font-size:8pt;font-weight:600;margin-top:6mm}
.tcap span{font-weight:500;color:INK}
.tot{display:flex;gap:8mm;margin-top:3mm;padding-top:2.5mm;border-top:.6pt solid RULE;
  font-size:8.6pt}
.tot b{font-weight:600}
.tot .lb{color:INK;font-weight:600}
.two{display:flex;gap:11mm;margin-top:7mm}
.two > div{flex:1}
.two p{font-size:9pt;line-height:1.56;margin-top:0}
.two p + p{margin-top:3.5mm}
h2{font-size:11pt;font-weight:600;padding-bottom:2mm;border-bottom:.9pt solid BRAND}
""".replace("BRAND", BRAND).replace("RULE", RULE).replace("SEC", SEC).replace("INK", INK)

BODY = """<div class="page"><div class="sheet">
""" + HEAD + """
  <div class="eyebrow">Tahmin detayı</div>
  <h1>Günlük üretim ve olasılık bandı</h1>
  <p class="lead" style="max-width:160mm">Bu bölüm 16 günlük ufku üç görünümde sunar: günlük
  toplamlar ve olasılık bandı, saatlik profiller ve saat × gün matrisi. Üçü de aynı hesaplamadan
  türetilir; aralarında bağımsız bir hesap yoktur. Saat eksenleri yerel saattir
  (Europe/Istanbul, UTC+3).</p>

  """ + CHART + """
    <div class="legend"><span><i class="line"></i>Beklenti (P50)</span>
      <span><i class="fan"></i>%80 olasılık aralığı (P10–P90)</span></div>
    <div class="figcap"><b>Şekil 4.1</b>&nbsp;&nbsp;Günlük üretim tahmini. Çizgi beklentiyi, çevresindeki
      alan %80 olasılık aralığını gösterir; alan ne kadar kalınsa o gün hava o kadar
      belirsizdir. Düşey eksen """ + str(GUN_YMIN) + """ MWh'ten başlar.{{NARR_S04_KUYRUK}}</div>

  <div class="tcap">Çizelge 4.1 <span>Günlük değerler [MWh]</span></div>
  <table>
    <tr><th>""" + AY_YIL + """</th>""" + hdr + """</tr>
    <tr><td>P90 · üst sınır</td>""" + rowcells([a + b for a, b in zip(p50, hw)]) + """</tr>
    <tr class="mid"><td>P50 · beklenti</td>""" + rowcells(p50, True) + """</tr>
    <tr><td>P10 · alt sınır</td>""" + rowcells([a - b for a, b in zip(p50, hw)]) + """</tr>
  </table>
  <div class="tot">
    <span class="lb">Dönem toplamı:</span>
    <span><b>{{TOPLAM_P50}} MWh</b> beklenti</span>
    <span><b>{{TOPLAM_P10}} MWh</b> alt sınır</span>
    <span><b>{{TOPLAM_P90}} MWh</b> üst sınır</span>
  </div>

  <div class="two">
    <div>
      <h2>Bant nasıl yorumlanır?</h2>
      <p style="margin-top:4mm">Bandın genişliği havanın belirsizliğinin doğrudan ölçüsüdür.
      Açık günlerde beklentinin ±%6–8'i kadardır; cephe geçişi beklenen günlerde ±%15'e kadar
      genişler. Bant ne kadar darsa, o gün için verilen sayı o kadar bağlayıcıdır.</p>
      <p>İşletme planlamasında önerilen okuma, alt sınırın (P10) güvenli taahhüt seviyesi olarak
      kullanılmasıdır. On raporun sekizinde gerçekleşen üretim bandın içinde kalır; alt sınırın
      altına düşme olasılığı %10'dur.</p>
    </div>
    <div>
      <h2>Dönem toplamı neden daha dar?</h2>
      <p style="margin-top:4mm">Günlük bantlar ±%6–8 iken dönem toplamının bandı ±%3'tür. Bunun
      nedeni günlerin birbirinden kısmen bağımsız olmasıdır: bir günün beklenenden düşük gelmesi,
      başka bir günün yüksek gelmesiyle kısmen dengelenir. Bu yüzden <b>dönem toplamının alt
      sınırı, günlük alt sınırların toplamı değildir</b> — 948 değil, {{TOPLAM_P10}} MWh'tir.</p>
      <p>Tahmin üretilemeyen bir gün olursa o gün için çubuk çizilmez ve eksende boş bırakılır;
      eksik gün hiçbir toplama dahil edilmez.</p>
    </div>
  </div>
""" + foot(4) + """
</div></div>"""

build("PVQuant_Konya_GES_s04_gunluk_uretim", CSS, BODY,
      "PVQuant — Konya GES · Günlük üretim ve olasılık bandı")
