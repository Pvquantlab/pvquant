import base64, os
from pvq import fan_chart

import os as _os
_BURASI = _os.path.dirname(_os.path.abspath(__file__))
FONTS = _os.environ.get("PVQ_FONTLAR", _os.path.join(_BURASI, "fontlar"))
OUT = _os.environ.get("PVQ_CIKTI", _os.path.join(_BURASI, "cikti"))
_os.makedirs(OUT, exist_ok=True)

def face(fam, weight, file):
    b = base64.b64encode(open(f"{FONTS}/{file}", "rb").read()).decode()
    return ("@font-face{font-family:'%s';font-style:normal;font-weight:%d;font-display:block;"
            "src:url(data:font/ttf;base64,%s) format('truetype');}" % (fam, weight, b))

FONTCSS = "".join([
    face("PlexSans", 400, "PlexSans-400.ttf"),
    face("PlexSans", 500, "PlexSans-500.ttf"),
    face("PlexSans", 600, "PlexSans-600.ttf"),
    face("PlexMono", 400, "PlexMono-400.ttf"),
    face("SourceSerif", 600, "SourceSerif-600.ttf"),
    face("SourceSerif", 700, "SourceSerif-700.ttf"),
])

BRAND, BRAND2, DEEP = "#0D4C68", "#2B7B9B", "#082F42"
INK, SEC, RULE = "#11171A", "#414B46", "#CDD6D1"

from veri import P50_GUN as p50, HW_GUN as hw, GUN_YMIN, GUN_YMAX, DONEM, GUN_SAYISI, METRIK_PENCERE, AY_YIL, CEPHE, BANT_VAR
from veri import GUN_ETIKET  # C-5/1 (v2.155): eksen elle range(5,21) idi — canlıda
                             # taze p50 + bayat 05–20 etiketi bastı (18 Ağu kabul avı)


# C-5/1 (v2.155): olu chart() SOKULDU — hicbir cagrisi yoktu ve govdesi
# elle 'Ağustos 2026' + ymax=80 tasiyordu (ayni hastaligin uyuyan kopyasi).

BASE = """
*{box-sizing:border-box;margin:0;padding:0}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{background:#E8EBE9;font-family:PlexSans,sans-serif;color:INK;font-feature-settings:"tnum" 1}
@page{size:A4;margin:0}
.page{width:210mm;height:297mm;background:#fff;margin:12mm auto;
  box-shadow:0 2px 24px rgba(0,0,0,.28);overflow:hidden;display:flex}
@media print{body{background:#fff}.page{margin:0;box-shadow:none}}
.fig{display:block;width:100%;height:auto}
.legend{display:flex;gap:7mm;align-items:center;font-size:8.2pt;font-weight:600;color:INK;margin-top:1mm}
.legend i{display:inline-block;width:4mm;height:2.4mm;background:BRAND2;margin-right:1.6mm;
  vertical-align:-.3mm}
.legend i.w{width:.5mm;height:3.4mm;background:#0C3123}
.legend i.band{display:inline-block;width:4mm;height:2.6mm;background:#C7E0D2;border:.4pt solid #A8CBB8;margin-right:1.6mm;vertical-align:-.3mm}
.legend i.line{display:inline-block;width:5mm;height:1.1mm;background:#0C3123;margin-right:1.6mm;vertical-align:-.1mm}
.figcap{font-size:8pt;line-height:1.5;color:#2B3532;margin-top:2.5mm}
.figcap b{color:INK;font-weight:600}
.row{display:flex;gap:3mm;font-size:8.4pt;line-height:1.5;padding:.15mm 0}
.row dt{color:SEC;width:27.5mm;flex:none}
.row dd{font-weight:500}
.mono{font-family:PlexMono;font-size:7.6pt;letter-spacing:-.02em;white-space:nowrap}
.imp h2{font-size:7.6pt;letter-spacing:.15em;text-transform:uppercase;color:BRAND;
  font-weight:600;padding-bottom:1.8mm;border-bottom:.6pt solid RULE;margin-bottom:2mm}
.k{font-size:7.6pt;letter-spacing:.11em;text-transform:uppercase;color:SEC}
.v{font-family:Newsreader,Georgia,serif;font-size:22pt;font-weight:600;line-height:1.05;
  margin-top:1.3mm;letter-spacing:-.01em}
.v u{text-decoration:none;font-family:PlexSans;font-size:9.6pt;font-weight:500;color:SEC;
  padding-left:1.2mm}
.n{font-size:7.9pt;color:SEC;margin-top:1.1mm;line-height:1.4}
""".replace("INK", INK).replace("SEC", SEC).replace("RULE", RULE) \
   .replace("BRAND2", BRAND2).replace("BRAND", BRAND)

IMPRINT = """
  <div class="imp">
    <div>
      <h2>Santral</h2>
      <div class="row"><dt>Saha</dt><dd>Konya GES — Konya, Türkiye</dd></div>
      <div class="row"><dt>Kurulu güç</dt><dd>{{KURULU}}</dd></div>
      <div class="row"><dt>Koordinat</dt><dd>{{KOORD_YUK}}</dd></div>
      <div class="row"><dt>Panel / inverter</dt><dd>MonoPERC-540B · INV-3125K</dd></div>
    </div>
    <div>
      <h2>Rapor</h2>
      <div class="row"><dt>Rapor kimliği</dt><dd class="mono">{{RAPOR_ID}}</dd></div>
      <div class="row"><dt>Hazırlanma</dt><dd>{{HAZIRLANMA}}</dd></div>
      <div class="row"><dt>Tahmin ufku</dt><dd>""" + DONEM + """ (""" + str(GUN_SAYISI) + """ gün)</dd></div>
      <div class="row"><dt>Metrik penceresi</dt><dd>""" + METRIK_PENCERE + """</dd></div>
    </div>
  </div>"""

# v2.182: bantsız koşuda fan lejantı ve bant açıklama cümlesi düşer
# (kural 4: bant yokken bant anlatılmaz); bantlıda baytlar birebir (md5).
_FAN_SPAN = ('\n      <span><i style="display:inline-block;width:4.4mm;height:2.8mm;background:#F0E3C9;border:0.4pt solid #DCC79A;margin-right:1.6mm;vertical-align:-0.4mm"></i>%80 olasılık aralığı (P10–P90)</span>') if BANT_VAR else ""
_BANT_CUMLE = (', çevresindeki alan %80 olasılık aralığını gösterir; alan ne kadar kalınsa hava\n      o kadar belirsizdir') if BANT_VAR else ' gösterir'

_LEDE_BANT_A = ', beklentinin\n  olasılık bandını ve' if BANT_VAR else ' ve'
_LEDE_BANT_C = ', beklentinin\n   olasılık bandını ve' if BANT_VAR else ' ve'

LEGCAP = """
    <div class="legend"><span><i style="display:inline-block;width:5mm;height:1.1mm;background:#0D4C68;margin-right:1.6mm;vertical-align:-0.1mm"></i>Beklenti (P50)</span>""" + _FAN_SPAN + """
      </div>
    <div class="figcap"><b>Şekil 1.1</b>&nbsp;&nbsp;Günlük üretim tahmini, """ + DONEM + """. Çizgi
      beklentiyi""" + _BANT_CUMLE + """. Düşey eksen """ + str(GUN_YMIN) + """ MWh'ten başlar.</div>"""


def shell(css, body, title):
    return ("<!doctype html><html lang=\"tr\"><head><meta charset=\"utf-8\"><title>%s</title>"
            "<style>%s%s%s</style></head><body>%s</body></html>"
            % (title, FONTCSS, BASE, css, body))


# =================================================================== A · blok
import textwrap

# v2.158 (C-3): s01'in uc yerlesim varyantina elle kopyalanan "kesintisiz" cumlesi
# tek kaynak; girinti varyant basina verilir ki HTML BAYT-BIREBIR kalsin (kanonik md5).
EVI_METIN = ('<div class="evi">Bu tahmin, {{KESINTISIZ}} g\u00fcnd\u00fcr kesintisiz '
             'olarak ertesi g\u00fcn ger\u00e7ekle\u015fen \u00fcretimle\n'
             '  kar\u015f\u0131la\u015ft\u0131r\u0131lmaktad\u0131r; sonu\u00e7lar S4 \u00b7 '
             "Do\u011fruluk Karnesi'ndedir.</div>")

def _evi(n):
    return textwrap.indent(EVI_METIN, " " * n)

CSS_A = """
.page{flex-direction:column}
.band{background:DEEP;color:#fff;padding:13mm 18mm 11mm}
.bhead{display:flex;justify-content:space-between;align-items:baseline;
  padding-bottom:9mm;border-bottom:1px solid rgba(255,255,255,.25)}
.bhead .m{font-size:13.5pt;font-weight:600;letter-spacing:-.015em}
.bhead .m span{font-weight:400;font-size:8.6pt;opacity:.72;padding-left:3mm;margin-left:3mm;
  border-left:1px solid rgba(255,255,255,.3)}
.bhead .r{font-size:8.5pt;opacity:.72}
.eyeb{font-size:7.9pt;letter-spacing:.18em;text-transform:uppercase;color:#8FC4DC;
  font-weight:600;margin-top:8mm}
h1{font-family:Newsreader,Georgia,serif;font-weight:600;font-size:46pt;line-height:.95;
  letter-spacing:-.02em;margin-top:3mm}
.sub{font-size:11.6pt;line-height:1.45;margin-top:4mm;opacity:.9}
.sub b{font-weight:600;opacity:1}
.pills{display:flex;gap:1.6mm;margin-top:8mm}
.pill{border:1px solid rgba(255,255,255,.35);padding:1.8mm 3.4mm;font-size:7.6pt;
  letter-spacing:.08em;opacity:.7}
.pill.on{background:#fff;color:DEEP;border-color:#fff;opacity:1;font-weight:600}
.main{flex:1;padding:8mm 18mm 11mm;display:flex;flex-direction:column}
.strip{display:flex;align-items:flex-start;border-bottom:.6pt solid RULE;padding-bottom:6mm}
.cell{flex:1;padding-left:7mm;border-left:.6pt solid RULE}
.cell:first-child{padding-left:0;border-left:0}
.lede{font-size:9.4pt;line-height:1.55;margin-top:5.5mm;max-width:158mm}
.figwrap{margin-top:auto;padding-top:8mm}
.imp{display:flex;gap:10mm;margin-top:6mm}
.imp>div{flex:1}
.evi{margin-top:5mm;padding:2.2mm 0 0 3.4mm;border-left:1.6pt solid BRAND2;
  font-size:8.2pt;line-height:1.45;color:#2B3532}
.foot{margin-top:4mm;padding-top:3mm;border-top:.6pt solid RULE;display:flex;
  justify-content:space-between;font-size:7.6pt;color:SEC}
.foot b{color:BRAND;font-weight:600;letter-spacing:.08em}
""".replace("DEEP", DEEP).replace("BRAND2", BRAND2).replace("BRAND", BRAND) \
   .replace("RULE", RULE).replace("SEC", SEC)

BODY_A = """<div class="page">
 <div class="band">
  <div class="bhead"><div class="m">PVQuant<span>Kanıta dayalı üretim tahmini</span></div>
    <div class="r">Üretim Tahmini ve Doğruluk Raporu</div></div>
  <div class="eyeb">{{MUSTERI}} için hazırlanmıştır</div>
  <h1>Konya GES</h1>
  <div class="sub"><b>""" + DONEM + """</b> · """ + str(GUN_SAYISI) + """ günlük saatlik üretim tahmini
    ve 120 günlük doğruluk karnesi</div>
  <div class="pills"><div class="pill">MOD A · HAM FİZİK</div>
    <div class="pill">MOD B · KALİBRE</div>
    <div class="pill on">MOD C · HİBRİT ✓</div></div>
 </div>
 <div class="main">
  <div class="strip">
    <div class="cell"><div class="k">""" + str(GUN_SAYISI) + """ günlük toplam beklenti</div>
      <div class="v">{{TOPLAM_P50}}<u>MWh</u></div><div class="n">P50 · en olası senaryo</div></div>
    <div class="cell"><div class="k">%80 olasılık bandı</div>
      <div class="v">{{TOPLAM_BANT}}<u>MWh</u></div>
      <div class="n">{{TAAHHUT_NOT}}</div></div>
  </div>
  <p class="lede">Bu rapor önümüzdeki """ + str(GUN_SAYISI) + """ gün için saatlik üretim beklentisini""" + _LEDE_BANT_A + """ son 120 günde her tahminin gerçekleşen üretimle gece-gece
  karşılaştırıldığı doğruluk karnesini bir arada sunar.</p>
  <div class="figwrap">__CHART__""" + LEGCAP + """</div>
  """ + IMPRINT + """
""" + _evi(2) + """
  <div class="foot"><div><b>MOD C · HİBRİT</b></div><div>Sayfa 1 / 16</div></div>
 </div>
</div>"""

# =================================================================== B · veri önde
CSS_B = """
.page{flex-direction:column;padding:14mm 18mm 11mm}
.head{display:flex;justify-content:space-between;align-items:baseline;padding-bottom:3mm;
  border-bottom:1.6pt solid BRAND}
.mark{font-size:13pt;font-weight:600;color:BRAND;letter-spacing:-.015em}
.mark span{font-weight:400;color:SEC;font-size:8.6pt;padding-left:3mm;margin-left:3mm;
  border-left:1px solid RULE}
.head .r{font-size:8.5pt;color:SEC}
.eyeb{font-size:7.9pt;letter-spacing:.18em;text-transform:uppercase;color:BRAND;
  font-weight:600;margin-top:7mm}
.hero{display:flex;align-items:flex-end;gap:8mm;margin-top:2.5mm;
  padding-bottom:5mm;border-bottom:.6pt solid RULE}
h1{font-family:Newsreader,Georgia,serif;font-weight:600;font-size:37pt;line-height:.92;
  letter-spacing:-.02em;white-space:nowrap}
.hero .sub{font-size:10.4pt;line-height:1.4;color:SEC;padding-bottom:2mm}
.figwrap{margin-top:7mm}
.callout{position:relative}
.numbers{display:flex;margin-top:7mm;border-top:1.4pt solid BRAND;
  border-bottom:.6pt solid RULE}
.cell{flex:1;padding:4.5mm 0 4.5mm 7mm;border-left:.6pt solid RULE}
.cell:first-child{padding-left:0;border-left:0}
.cell .v{font-size:26pt}
.pills{display:flex;gap:1.6mm;margin-top:6mm}
.pill{border:.6pt solid RULE;padding:1.8mm 3.4mm;font-size:7.6pt;letter-spacing:.08em;color:SEC}
.pill.on{background:BRAND;color:#fff;border-color:BRAND;font-weight:600}
.imp{display:flex;gap:10mm;margin-top:auto;padding-top:7mm}
.imp>div{flex:1}
.evi{margin-top:5mm;padding:2.2mm 0 0 3.4mm;border-left:1.6pt solid BRAND2;
  font-size:8.2pt;line-height:1.45;color:#2B3532}
.foot{margin-top:4mm;padding-top:3mm;border-top:.6pt solid RULE;display:flex;
  justify-content:space-between;font-size:7.6pt;color:SEC}
.foot b{color:BRAND;font-weight:600;letter-spacing:.08em}
""".replace("BRAND2", BRAND2).replace("BRAND", BRAND).replace("RULE", RULE).replace("SEC", SEC)

BODY_B = """<div class="page">
 <div class="head"><div class="mark">PVQuant<span>Kanıta dayalı üretim tahmini</span></div>
   <div class="r">Üretim Tahmini ve Doğruluk Raporu</div></div>
 <div class="eyeb">{{MUSTERI}} için hazırlanmıştır</div>
 <div class="hero"><h1>Konya GES</h1>
   <div class="sub">""" + DONEM + """<br>""" + str(GUN_SAYISI) + """ günlük saatlik tahmin ·
     120 günlük doğruluk karnesi</div></div>
 <div class="figwrap">__CHART__""" + LEGCAP + """</div>
 <div class="numbers">
   <div class="cell"><div class="k">""" + str(GUN_SAYISI) + """ günlük toplam beklenti</div>
     <div class="v">{{TOPLAM_P50}}<u>MWh</u></div><div class="n">P50 · en olası senaryo</div></div>
   <div class="cell"><div class="k">%80 olasılık bandı</div>
     <div class="v">{{TOPLAM_BANT}}<u>MWh</u></div>
     <div class="n">{{TAAHHUT_NOT}}</div></div>
 </div>
 <div class="pills"><div class="pill">MOD A · HAM FİZİK</div>
   <div class="pill">MOD B · KALİBRE</div><div class="pill on">MOD C · HİBRİT ✓</div></div>
 """ + IMPRINT + """
""" + _evi(1) + """
 <div class="foot"><div><b>MOD C · HİBRİT</b></div><div>Sayfa 1 / 16</div></div>
</div>"""

# =================================================================== C · yan ray
CSS_C = """
.rail{width:64mm;background:DEEP;color:#fff;padding:14mm 10mm 11mm;display:flex;
  flex-direction:column}
.rail .m{font-size:13.5pt;font-weight:600;letter-spacing:-.015em}
.rail .tag{font-size:8pt;opacity:.7;margin-top:1.5mm;line-height:1.4}
.rail .big{margin-top:auto;padding-top:8mm;border-top:1px solid rgba(255,255,255,.28)}
.rail .bk{font-size:7.4pt;letter-spacing:.11em;text-transform:uppercase;opacity:.7}
.rail .bv{font-family:Newsreader,Georgia,serif;font-size:25pt;white-space:nowrap;font-weight:600;line-height:1.05;
  margin-top:1.5mm}
.rail .bv u{text-decoration:none;font-family:PlexSans;font-size:10pt;font-weight:500;
  opacity:.75;padding-left:1.2mm}
.rail .bn{font-size:7.8pt;opacity:.75;margin-top:1.2mm;line-height:1.45}
.rail .sep{height:1px;background:rgba(255,255,255,.28);margin:6mm 0}
.rail .mode{font-size:7.6pt;letter-spacing:.09em;font-weight:600}
.rail .modes{font-size:7.4pt;opacity:.65;margin-top:1.4mm;line-height:1.5}
.rail .pg{margin-top:auto;padding-top:8mm;font-size:7.6pt;opacity:.7}
.main{flex:1;padding:14mm 13mm 11mm;display:flex;flex-direction:column}
.head{display:flex;justify-content:flex-end;padding-bottom:3mm;border-bottom:1.6pt solid BRAND;
  font-size:8.5pt;color:SEC}
.eyeb{font-size:7.9pt;letter-spacing:.18em;text-transform:uppercase;color:BRAND;
  font-weight:600;margin-top:9mm}
h1{font-family:Newsreader,Georgia,serif;font-weight:600;font-size:38pt;line-height:.94;
  letter-spacing:-.02em;margin-top:2.5mm}
.sub{font-size:11pt;line-height:1.45;margin-top:3.5mm}
.sub b{font-weight:600}
.lede{font-size:9.2pt;line-height:1.55;color:INK;margin-top:5.5mm}
.figwrap{margin-top:auto;padding-top:8mm}
.imp{display:block;margin-top:6mm}
.imp>div+div{margin-top:5mm}
.row{font-size:8.3pt}
.row dt{width:30mm}
.evi{margin-top:5mm;padding:2.2mm 0 0 3.4mm;border-left:1.6pt solid BRAND2;
  font-size:8.1pt;line-height:1.45;color:#2B3532}
""".replace("DEEP", DEEP).replace("BRAND2", BRAND2).replace("BRAND", BRAND) \
   .replace("RULE", RULE).replace("SEC", SEC).replace("INK", INK)

BODY_C = """<div class="page">
 <div class="rail">
   <div class="m">PVQuant</div>
   <div class="tag">Kanıta dayalı<br>üretim tahmini</div>
   <div class="big">
     <div class="bk">""" + str(GUN_SAYISI) + """ günlük toplam beklenti</div>
     <div class="bv">{{TOPLAM_P50}}<u>MWh</u></div>
     <div class="bn">P50 · en olası senaryo</div>
     <div class="sep"></div>
     <div class="bk">%80 olasılık bandı</div>
     <div class="bv" style="font-size:17.5pt">{{TOPLAM_BANT}}<u>MWh</u></div>
     <div class="bn">{{TAAHHUT_NOT}}</div>
   </div>
   <div class="pg"><div class="mode">MOD C · HİBRİT ✓</div>
     <div class="modes">A ham fizik · B kalibre · C hibrit</div>
     <div style="margin-top:6mm">Sayfa 1 / 16</div></div>
 </div>
 <div class="main">
   <div class="head">Üretim Tahmini ve Doğruluk Raporu</div>
   <div class="eyeb">{{MUSTERI}} için hazırlanmıştır</div>
   <h1>Konya GES</h1>
   <div class="sub"><b>""" + DONEM + """</b> · """ + str(GUN_SAYISI) + """ günlük saatlik üretim tahmini
     ve 120 günlük doğruluk karnesi</div>
   <p class="lede">Bu rapor önümüzdeki """ + str(GUN_SAYISI) + """ gün için saatlik üretim beklentisini""" + _LEDE_BANT_C + """ son 120 günde her tahminin gerçekleşen üretimle gece-gece
   karşılaştırıldığı doğruluk karnesini bir arada sunar.</p>
   <div class="figwrap">__CHART__""" + LEGCAP + """</div>
   """ + IMPRINT + """
""" + _evi(3) + """
 </div>
</div>"""

VARIANTS = [("PVQuant_Konya_GES_s01_kapak", CSS_A, BODY_A,
             fan_chart(p50, hw, GUN_ETIKET, AY_YIL + " [gün]",
                       "[MWh/gün]", ymin=GUN_YMIN, ymax=GUN_YMAX, step=10, H=250, fs=15,
                       highlight=CEPHE, hl_label="cephe geçişi"))]

from weasyprint import HTML as WH
for name, css, body, ch in VARIANTS:
    html = shell(css, body.replace("__CHART__", ch), "PVQuant — Konya GES · Kapak")
    hp = f"{OUT}/{name}.html"
    from veri import doldur
    open(hp, "w", encoding="utf-8").write(doldur(html))
    doc = WH(hp).render()
    doc.write_pdf(f"{OUT}/{name}.pdf")
    print(name, "sayfa:", len(doc.pages))
