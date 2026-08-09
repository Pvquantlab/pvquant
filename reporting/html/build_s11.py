import math
from pvq import *

tr = lambda x, d=1: ("%.*f" % (d, x)).replace(",", "").replace(".", ",")
th = lambda x: "{:,}".format(int(round(x))).replace(",", ".")

P10 = [ay_pct(m, 10) for m in range(12)]
P90 = [ay_pct(m, 90) for m in range(12)]
# SON12 veri-güdümlü (v2.104): her takvim ayı için o ayı içeren EN YENİ yılın
# değeri — kanonik girdide 2026(Oca–Tem)+2025(Ağu–Ara) bölünmesini birebir üretir.
def _son12(iklim):
    yillar = sorted(iklim)
    out = []
    for m in range(12):
        v = 0.0
        for y in reversed(yillar):
            d = iklim[y][m]
            if d is not None and d > 0:     # kanonikte boş ay None gelebilir
                v = d
                break
        out.append(v)
    return out
SON12 = _son12(IKLIM)

YIL = [sum(IKLIM[y]) for y in TAM_YILLAR]
ORT = sum(YIL) / len(YIL)
SD = math.sqrt(sum((v - ORT) ** 2 for v in YIL) / (len(YIL) - 1))
CV = SD / ORT * 100
PARLAK = max(TAM_YILLAR, key=lambda y: sum(IKLIM[y]))
BULUT = min(TAM_YILLAR, key=lambda y: sum(IKLIM[y]))
p_yil = lambda p: ORT - {50: 0, 75: 0.6745, 90: 1.2816}[p] * SD


# ---------------------------------------------------------------- Şekil 11.1
def zarf(W=1000, H=300, ml=64, mb=52, fs=14):
    MR, MT = 14, 28
    PW, PH = W - ml - MR, H - MT - mb
    slot = PW / 12
    cx = lambda i: ml + slot * (i + .5)
    # c1b (v2.105): eksen zarf tepesinden, çeyrek-adım 100'e yuvarlı —
    # kanonikte (max P90≈2739) 700 adım / 2800 tavanı birebir üretir.
    _tepe = max(max(P90), max(SON12))
    z_adim = int(-(-(_tepe / 4.0) // 100)) * 100
    z_ymax = 4 * z_adim
    y = lambda v: MT + PH * (z_ymax - v) / z_ymax
    o = []
    for t in range(0, z_ymax + 1, z_adim):
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.3"/>'
                 % (ml, y(t), W - MR, y(t), GRID))
        o.append('<text x="%.1f" y="%.1f" text-anchor="end" font-family="PlexSans" font-size="%d"'
                 ' font-weight="500" fill="#2B3439">%s</text>'
                 % (ml - 9, y(t) + fs * .34, fs, th(t)))
    pts = " ".join("%.1f,%.1f" % (cx(i), y(P90[i])) for i in range(12))
    pts += " " + " ".join("%.1f,%.1f" % (cx(i), y(P10[i])) for i in reversed(range(12)))
    o.append('<polygon points="%s" fill="%s"/>' % (pts, FAN_AREA))
    for ser in (P90, P10):
        o.append('<path d="M %s" fill="none" stroke="%s" stroke-width="1.3"/>'
                 % (" L ".join("%.1f,%.1f" % (cx(i), y(ser[i])) for i in range(12)), FAN_EDGE))
    o.append('<path d="M %s" fill="none" stroke="#8A6A28" stroke-width="1.9" '
             'stroke-dasharray="7 5"/>'
             % " L ".join("%.1f,%.1f" % (cx(i), y(LTA_AY[i])) for i in range(12)))
    o.append('<path d="M %s" fill="none" stroke="%s" stroke-width="3" stroke-linejoin="round"/>'
             % (" L ".join("%.1f,%.1f" % (cx(i), y(SON12[i])) for i in range(12)), BRAND))
    for i in range(12):
        o.append('<circle cx="%.1f" cy="%.1f" r="3.6" fill="#fff" stroke="%s" stroke-width="2"/>'
                 % (cx(i), y(SON12[i]), BRAND))
    # Nisan işareti
    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#8A939A" stroke-width="1.1"/>'
             % (cx(3), y(SON12[3]) + 8, cx(3) + 40, y(SON12[3]) + 42))
    o.append('<text x="%.1f" y="%.1f" font-family="PlexSans" font-size="%d" font-weight="600" '
             'fill="%s">Nisan · düşük kapsama</text>' % (cx(3) + 44, y(SON12[3]) + 46, fs, INK))
    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#7C8781" stroke-width="1.5"/>'
             % (ml, y(0), W - MR, y(0)))
    for i, ad in enumerate(AY_TR):
        o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" '
                 'font-size="%d" font-weight="500" fill="#2B3439">%s</text>'
                 % (cx(i), y(0) + fs * 1.5, fs, ad))
    o.append('<text transform="translate(13,%.1f) rotate(-90)" text-anchor="middle" '
             'font-family="PlexSans" font-size="%d" font-weight="600" fill="%s">Aylık üretim '
             '[MWh]</text>' % (MT + PH / 2, fs + 1, INK))
    return ('<svg class="fig" viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" role="img" '
            'aria-label="Iklim zarfi">%s</svg>' % (W, H, "".join(o)))


# ---------------------------------------------------------------- Şekil 11.2
def egri(W=1000, H=272, ml=64, mb=52, fs=14):
    MR, MT = 38, 22
    PW, PH = W - ml - MR, H - MT - mb
    # c1 (v2.105): eksen ORT±3·SD, binliğe yuvarlı — kanonikte 16000/23000
    x0v = int(math.floor((ORT - 3 * SD) / 1000.0)) * 1000
    x1v = int(math.ceil((ORT + 3 * SD) / 1000.0)) * 1000
    X = lambda v: ml + PW * (v - x0v) / (x1v - x0v)
    Y = lambda v: MT + PH * (100 - v) / 100
    F = lambda v: 100 * (1 - 0.5 * (1 + math.erf((v - ORT) / (SD * math.sqrt(2)))))
    o = []
    for t in range(0, 101, 25):
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.3"/>'
                 % (ml, Y(t), W - MR, Y(t), GRID))
        o.append('<text x="%.1f" y="%.1f" text-anchor="end" font-family="PlexSans" font-size="%d"'
                 ' font-weight="500" fill="#2B3439">%%%d</text>' % (ml - 9, Y(t) + fs * .34, fs, t))
    seg = [(X(v), Y(F(v))) for v in range(x0v, x1v + 1, 100)]
    o.append('<path d="M %s" fill="none" stroke="%s" stroke-width="3" stroke-linejoin="round"/>'
             % (" L ".join("%.1f,%.1f" % p for p in seg), BRAND))
    for p, lab in ((90, "P90"), (75, "P75"), (50, "P50")):
        v = p_yil(p)
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#B9C4CA" '
                 'stroke-width="1.1" stroke-dasharray="4 3"/>' % (ml, Y(p), X(v), Y(p)))
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#B9C4CA" '
                 'stroke-width="1.1" stroke-dasharray="4 3"/>' % (X(v), Y(p), X(v), Y(0)))
        o.append('<circle cx="%.1f" cy="%.1f" r="4.6" fill="%s" stroke="%s" stroke-width="2"/>'
                 % (X(v), Y(p), FAN_AREA, BRAND))
        o.append('<text x="%.1f" y="%.1f" text-anchor="end" font-family="PlexSans" '
                 'font-size="%d" font-weight="600" fill="%s">%s</text>'
                 % (X(v) - 12, Y(p) + 16, fs, INK, lab))
        o.append('<text x="%.1f" y="%.1f" text-anchor="end" font-family="PlexSans" '
                 'font-size="%d" font-weight="500" fill="#2B3439">%s MWh/yıl</text>'
                 % (X(v) - 12, Y(p) + 31, fs, th(v)))
    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#7C8781" stroke-width="1.5"/>'
             % (ml, Y(0), W - MR, Y(0)))
    for v in range(x0v, x1v + 1, 1000):
        o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" '
                 'font-size="%d" font-weight="500" fill="#2B3439">%s</text>'
                 % (X(v), Y(0) + fs * 1.5, fs, th(v)))
    o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" font-size="%d" '
             'font-weight="600" fill="%s">Yıllık üretim [MWh]</text>'
             % (ml + PW / 2, Y(0) + fs * 3, fs + 1, INK))
    o.append('<text transform="translate(13,%.1f) rotate(-90)" text-anchor="middle" '
             'font-family="PlexSans" font-size="%d" font-weight="600" fill="%s">Aşılma '
             'olasılığı [%%]</text>' % (MT + PH / 2, fs + 1, INK))
    return ('<svg class="fig" viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" role="img" '
            'aria-label="Asilma olasiligi egrisi">%s</svg>' % (W, H, "".join(o)))


IST = [
    ("Uzun dönem ortalaması", th(ORT) + " MWh/yıl", "19 tam yılın ortalaması"),
    ("Özgül üretim", th(ORT / KAPASITE_MWP) + " kWh/kWp",           # v2.103
     "%s MWp kurulu güce göre" % tr(KAPASITE_MWP)),
    ("En parlak yıl", str(PARLAK), "%s MWh · ortalamanın %%%d üzeri"
     % (th(sum(IKLIM[PARLAK])), round((sum(IKLIM[PARLAK]) / ORT - 1) * 100))),
    ("En bulutlu yıl", str(BULUT), "%s MWh · ortalamanın %%%d altı"
     % (th(sum(IKLIM[BULUT])), round((1 - sum(IKLIM[BULUT]) / ORT) * 100))),
    ("Yıllar arası değişkenlik", "%%%s" % tr(CV), "standart sapmanın ortalamaya oranı"),
]

rows = "".join('<div class="ist"><b>%s</b><span class="v2">%s</span><span class="a2">%s</span>'
               '</div>' % i for i in IST)

CSS = """
.fig{margin-top:5mm}
.ists{display:flex;gap:0;margin-top:6mm;border-top:1pt solid BRAND;
  border-bottom:.6pt solid RULE}
.ist{flex:1;padding:3.2mm 0 3.2mm 5mm;border-left:.6pt solid RULE}
.ist:first-child{padding-left:0;border-left:0}
.ist b{display:block;font-size:7.6pt;font-weight:600;letter-spacing:.05em;
  text-transform:uppercase;color:INK;line-height:1.3;min-height:7mm}
.ist .v2{display:block;font-size:9.6pt;font-weight:600;margin-top:1.4mm}
.ist .a2{display:block;font-size:7.8pt;color:SEC;margin-top:1mm;line-height:1.35}
.legend i.zarf{display:inline-block;width:4.4mm;height:2.8mm;background:FAN;
  border:.4pt solid EDGE;margin-right:1.6mm;vertical-align:-.4mm}
.legend i.lta{display:inline-block;width:5mm;height:0;background:none;
  border-top:1.6pt dashed #8A6A28;margin-right:1.6mm;vertical-align:.2mm}
""".replace("BRAND", BRAND).replace("RULE", RULE).replace("SEC", SEC).replace("INK", INK) \
   .replace("FAN", FAN_AREA).replace("EDGE", FAN_EDGE)

BODY = """<div class="page"><div class="sheet">
""" + HEAD + """
  <div class="eyebrow">İklim bağlamı</div>
  <h1>İklim zarfı ve aşılma olasılıkları</h1>
  <p class="lead" style="max-width:162mm">Bir ayın üretimi ancak kendi geçmişiyle
  karşılaştırıldığında değerlendirilebilir. Bu bölüm, her ayın 19 tam yıllık dağılımını
  (2007–2025) ve son 12 ayın bu dağılımın neresine düştüğünü gösterir.</p>

  """ + zarf() + """
    <div class="legend"><span><i class="line"></i>Son 12 ay gerçekleşen</span>
      <span><i class="lta"></i>Uzun dönem ortalaması</span>
      <span><i class="zarf"></i>İklim zarfı (P10–P90, 2007–2025)</span></div>
    <div class="figcap"><b>Şekil 11.1</b>&nbsp;&nbsp;Son 12 ay (Ağustos 2025 – Temmuz 2026)
      genel olarak zarfın alt yarısında seyretmiştir. Nisan ayı zarfın belirgin altında kalır;
      bu düşüş meteorolojik değil, ölçümseldir — aynı ayda santral verisinin kapsaması %49'a
      gerilemişti (sayfa 10). Düşük kapsamalı aylar için zarf-altı yorumu yapılmaz.</div>

  """ + egri() + """
    <div class="figcap"><b>Şekil 11.2</b>&nbsp;&nbsp;Yıllık toplam üretimin aşılma olasılığı.
      Eğri, 19 tam yılın dağılımına normal yaklaşımla oturtulmuştur. Finansman
      senaryolarında alt sınır olarak genellikle P90 kullanılır: bu santral için
      """ + th(p_yil(90)) + """ MWh/yıl. Not: normal varsayımı yalnızca bu yıllık eğri için
      geçerlidir; günlük ve saatlik bantlar (sayfa 4–5) dağılım varsayımı olmadan üretilir.</div>

  <div class="ists">""" + rows + """</div>
""" + foot(11) + """
</div></div>"""

build("PVQuant_Konya_GES_s11_iklim_zarfi", CSS, BODY,
      "PVQuant — Konya GES · İklim zarfı")
print("CV %.2f  P50 %.0f  P75 %.0f  P90 %.0f" % (CV, p_yil(50), p_yil(75), p_yil(90)))
