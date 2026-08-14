from pvq import *

# --- son 30 günün karnesi (tek kaynak: veri.py) ---------------------------
from veri import KARNE_WM as wm, KARNE_SK as sk, KARNE_H72_KUYRUK, KARNE_TARIH as TARIH
from veri import KARNE_NAIF as naif   # v2.137: naif ölçümdür, motor türetmez
h72 = [round(w * 1.36, 1) for w in wm[:23]] + KARNE_H72_KUYRUK
ORT_SKILL = sum(sk) / len(sk) * 100
tr = lambda x, d=1: ("%.*f" % (d, x)).replace(".", ",")


def karne(W=1000, H=272, ml=60, mb=52, fs=15):
    MR, MT = 14, 20
    PW, PH = W - ml - MR, H - MT - mb
    n = len(wm)
    step = PW / (n - 1)
    cx = lambda i: ml + step * i
    # c5 (v2.109): eksen serilerin tepesinden, 5'e yuvarlı — kanonikte 20'yi üretir
    k_ymax = max(20, int(-(-max(max(wm), max(h72), max(naif)) // 5)) * 5)
    y = lambda v: MT + PH * (k_ymax - v) / k_ymax
    o = []
    for t in range(0, k_ymax + 1, 5):
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.3"/>'
                 % (ml, y(t), W - MR, y(t), GRID))
        o.append('<text x="%.1f" y="%.1f" text-anchor="end" font-family="PlexSans" font-size="%d"'
                 ' font-weight="500" fill="#2B3439">%%%d</text>' % (ml - 9, y(t) + fs * .34, fs, t))
    # kazanç alanı: naif referans ile gün-öncesi hata arasındaki fark
    pts = " ".join("%.1f,%.1f" % (cx(i), y(naif[i])) for i in range(n))
    pts += " " + " ".join("%.1f,%.1f" % (cx(i), y(wm[i])) for i in reversed(range(n)))
    o.append('<polygon points="%s" fill="%s"/>' % (pts, FAN_AREA))
    o.append('<path d="M %s" fill="none" stroke="#B08C43" stroke-width="1.8" '
             'stroke-dasharray="7 5"/>'
             % " L ".join("%.1f,%.1f" % (cx(i), y(naif[i])) for i in range(n)))
    o.append('<path d="M %s" fill="none" stroke="#6E93A6" stroke-width="1.6"/>'
             % " L ".join("%.1f,%.1f" % (cx(i), y(h72[i])) for i in range(n)))
    o.append('<path d="M %s" fill="none" stroke="%s" stroke-width="3" stroke-linejoin="round"/>'
             % (" L ".join("%.1f,%.1f" % (cx(i), y(wm[i])) for i in range(n)), BRAND))
    for i in range(n):
        o.append('<circle cx="%.1f" cy="%.1f" r="3.2" fill="#fff" stroke="%s" stroke-width="2"/>'
                 % (cx(i), y(wm[i]), BRAND))
    # kazanç etiketi
    o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" font-size="%d" '
             'font-weight="600" fill="#8A6A28">kazanç: ortalama %%%s</text>'
             % (cx(9), y(k_ymax * 0.96), fs, tr(ORT_SKILL, 0)))
    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#7C8781" stroke-width="1.5"/>'
             % (ml, y(0), W - MR, y(0)))
    for i in range(0, n, 4):
        o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" '
                 'font-size="%d" font-weight="500" fill="#2B3439">%s</text>'
                 % (cx(i), y(0) + fs * 1.5, fs, TARIH[i]))
    o.append('<text transform="translate(12,%.1f) rotate(-90)" text-anchor="middle" '
             'font-family="PlexSans" font-size="%d" font-weight="600" fill="%s">Hata [%%]</text>'
             % (MT + PH / 2, fs + 1, INK))
    return ('<svg class="fig" viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" role="img" '
            'aria-label="Son 30 gunun dogruluk karnesi">%s</svg>' % (W, H, "".join(o)))


rows = ""
for i in range(23, 30):
    izle = wm[i] > 10
    rows += ('<tr%s><td class="d">%s</td><td class="num b">%%%s</td><td class="num">%%%s</td>'
             '<td class="num">%%%s</td><td class="num b">%%%s</td>'
             '<td class="st">%s</td></tr>'
             % (' class="w"' if izle else "", TARIH[i], tr(wm[i]), tr(h72[i]), tr(naif[i]),
                tr(sk[i] * 100), '<span class="izle">izle</span>' if izle else
                '<span class="ok">✓</span>'))

CSS = """
.fig{margin-top:6mm}
.tcap{font-size:8pt;font-weight:600;margin-top:6mm}
.tcap span{font-weight:500;color:INK}
table{margin-top:2.5mm}
th{font-size:7.9pt;padding:1.9mm 2.5mm;text-align:right}
th:first-child{text-align:left}
td{font-size:8.4pt;padding:1.7mm 2.5mm}
td.d{font-weight:500}
td.num{text-align:right;font-variant-numeric:tabular-nums}
td.b{font-weight:600}
td.st{text-align:right;width:22mm}
tr.w td{background:#F6F2E7}
.ok{color:OK;font-weight:600}
.izle{color:AMBER;font-weight:600;font-size:7.9pt}
.two{display:flex;gap:11mm;margin-top:6mm}
.two > div{flex:1}
.two h2{font-size:10.5pt;font-weight:600;padding-bottom:2mm;border-bottom:.9pt solid BRAND;
  margin-bottom:3.5mm}
.two p{font-size:9pt;line-height:1.56;margin-top:0}
.two p + p{margin-top:3mm}
.legend i.gain{display:inline-block;width:4.4mm;height:2.8mm;background:FAN;
  border:.4pt solid #DCC79A;margin-right:1.6mm;vertical-align:-.4mm}
.legend i.naif{display:inline-block;width:5mm;height:0;border-top:1.6pt dashed #B08C43;
  margin-right:1.6mm;vertical-align:.2mm}
.legend i.h72{display:inline-block;width:5mm;height:1.1mm;background:#6E93A6;
  margin-right:1.6mm;vertical-align:-.1mm}
""".replace("INK", INK).replace("BRAND", BRAND).replace("AMBER", AMBER).replace("OK", OK).replace("FAN", FAN_AREA)

BODY = """<div class="page"><div class="sheet">
""" + HEAD + """
  <div class="eyebrow">Doğruluk karnesi</div>
  <h1>Her tahmin ölçülür</h1>
  <p class="lead" style="max-width:162mm">Yayımlanan her tahmin, ertesi gün santralin
  gerçekleşen üretimiyle karşılaştırılır ve sonuç kalıcı olarak saklanır. Bu bölüm o sınavın
  karnesidir: hatanın büyüklüğü, basit bir referans yönteme göre kazanılan isabet ve iki farklı
  ufuk için başarım.</p>

  """ + karne() + """
    <div class="legend"><span><i class="line"></i>Gün-öncesi hata (0–24 s)</span>
      <span><i class="h72"></i>24–72 saat</span>
      <span><i class="naif"></i>Naif referans</span>
      <span><i class="gain"></i>Kazanç</span></div>
    <div class="figcap"><b>Şekil 7.1</b>&nbsp;&nbsp;Son 30 günün karnesi. Kum rengi alan,
      tahminin basit referans yönteme göre kazandırdığı isabettir — alan ne kadar kalınsa
      model o gün o kadar değer üretmiştir. {{NARR_S07_SEKIL}}</div>

  <div class="tcap">Çizelge 7.1 <span>Son yedi günün karnesi</span></div>
  <table>
    <tr><th>Tarih</th><th>Gün-öncesi</th><th>24–72 saat</th><th>Naif referans</th>
      <th>Kazanç</th><th>Durum</th></tr>
    """ + rows + """
  </table>

  <div class="two">
    <div>
      <h2>Kazanç nasıl hesaplanır?</h2>
      <p>Ölçüt, tahminin hiç model kullanmadan elde edilebilecek sonuca göre ne kadar iyi
      olduğudur. Referans, güneşin açısına göre ölçeklenmiş “dün ne olduysa bugün de o olur”
      yöntemidir. Kazanç, hatanın referans hataya oranından çıkar: sıfır referansla aynı,
      yükseldikçe daha iyi demektir.</p>
    </div>
    <div>
      <h2>{{NARR_S07_BASLIK}}</h2>
      <p>{{NARR_S07_GOVDE}}</p>
    </div>
  </div>
""" + foot(7) + """
</div></div>"""

build("PVQuant_Konya_GES_s07_dogruluk_karnesi", CSS, BODY,
      "PVQuant — Konya GES · Doğruluk karnesi")
print("ortalama kazanç: %.1f" % ORT_SKILL)
