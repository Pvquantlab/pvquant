from pvq import *

HALKA = [
    ("HAVA GİRDİSİ", "Saatlik hava senaryosu",
     "Işınım, bulutluluk, sıcaklık ve rüzgâr tahmini dış sağlayıcıdan alınır.", False),
    ("MOD A · HAM FİZİK", "Fizik modeli",
     "Panel düzlemine düşen ışınım, hücre sıcaklığı ve DC→AC dönüşümü hesaplanır. "
     "Kalibrasyonsuz taban çizgisi.", False),
    ("MOD B · KALİBRE", "Santral verisiyle ayar",
     "Sistem verimi ve bifacial kazanç santralin kendi üretiminden bulunur; bayraklı saatler "
     "dışlanır. Olasılık bandı üretmez.", False),
    ("MOD C · HİBRİT", "Bu raporun modu",
     "Makine öğrenmesi kalan hatayı öğrenir ve P10 / P50 / P90 aralıkları üretilir.", True),
]

from veri import SAHA, KUNYE

halkalar = ""
for i, (kod, ad, ac, aktif) in enumerate(HALKA):
    ok = ('<div class="ok">→</div>' if i else "")
    halkalar += ('%s<div class="halka%s"><b>%s</b><i>%s</i><span>%s</span></div>'
                 % (ok, " on" if aktif else "", kod, ad, ac))

saha = "".join('<div class="sr"><dt>%s</dt><dd>%s</dd></div>' % p for p in SAHA)
kunye = "".join('<tr><td class="kn">%s</td><td>%s</td><td>%s</td><td>%s</td>'
                '<td class="zd">%s</td></tr>' % k for k in KUNYE)

CSS = """
.zincir{display:flex;align-items:stretch;gap:0;margin-top:6mm}
.halka{flex:1;border:.6pt solid RULE;padding:3mm 3.4mm;background:#fff}
.halka.on{background:BRAND;border-color:BRAND;color:#fff}
.halka b{display:block;font-size:7.8pt;font-weight:600;letter-spacing:.07em}
.halka i{display:block;font-style:normal;font-size:8.4pt;font-weight:600;margin-top:1.4mm}
.halka span{display:block;font-size:7.7pt;line-height:1.42;color:SEC;margin-top:1.6mm}
.halka.on span{color:#fff;opacity:.86}
.ok{display:flex;align-items:center;padding:0 2mm;color:#9AA5AB;font-size:11pt}

h2{font-size:10.5pt;font-weight:600;padding-bottom:2mm;border-bottom:.9pt solid BRAND;
  margin-top:7mm}
.saha{display:flex;flex-wrap:wrap;margin-top:3mm}
.sr{width:50%;display:flex;gap:3mm;font-size:8.5pt;padding-right:6mm;line-height:1.5;padding:1.4mm 0;
  border-bottom:.6pt solid #E8EDEA}
.sr dt{color:SEC;width:34mm;flex:none}
.sr dd{font-weight:600}
table{margin-top:3mm}
th{font-size:7.9pt;padding:1.8mm 2.5mm}
td{font-size:8.3pt;padding:1.6mm 2.5mm;vertical-align:top}
td.kn{font-weight:600;width:36mm}
td.zd{width:26mm}
.figcap{margin-top:2.5mm}
""".replace("BRAND", BRAND).replace("RULE", RULE).replace("SEC", SEC)

BODY = """<div class="page"><div class="sheet">
""" + HEAD + """
  <div class="eyebrow">Metodoloji</div>
  <h1>Model zinciri ve veri künyesi</h1>
  <p class="lead" style="max-width:162mm">Tahmin dört halkalı bir zincirden geçer. Her halka
  raporda adıyla anılır ve ne yaptığı yazılır; kara kutu yoktur. Bu sayfa ayrıca sayıları
  besleyen her veri kaynağını, çözünürlüğünü ve dönemini listeler.</p>

  <div class="zincir">""" + halkalar + """</div>
  <div class="figcap"><b>Şekil 13.1</b>&nbsp;&nbsp;Model zinciri. Koyu kutu bu raporun
    üretildiği halkadır: santral verisiyle kalibre edilmiş fizik modelinin üzerine makine
    öğrenmesi eklenmiş hâli. Olasılık aralıkları yalnızca bu halkada hesaplanabilir; önceki
    halkalar tek bir beklenti üretir.</div>

  <h2>Saha kimliği</h2>
  <div class="saha">""" + saha + """</div>

  <h2>Veri künyesi</h2>
  <table>
    <tr><th>Kaynak</th><th>İçerik</th><th>Çözünürlük</th><th>Dönem</th><th>Zaman damgası</th></tr>
    """ + kunye + """
  </table>
""" + foot(13) + """
</div></div>"""

build("PVQuant_Konya_GES_s13_model_zinciri", CSS, BODY,
      "PVQuant — Konya GES · Model zinciri ve veri künyesi")
