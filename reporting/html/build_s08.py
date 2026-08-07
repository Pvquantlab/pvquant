import random
from pvq import *

R = random.Random(7)
tr = lambda x, d=1: ("%.*f" % (d, x)).replace(".", ",").replace("-", "\u2212")

# --- saçılım verisi: gerçekleşen ve tahmin çiftleri [MW] (tek kaynak: veri.py)
from veri import PROF, MAE24 as _MAE24, MAE72 as _MAE72, MU as _MU, SD as _SD, NDAYS as _NDAYS
pairs24, pairs72 = [], []
for _ in range(150):
    a = max(0.15, R.choice(PROF) * R.uniform(.72, 1.06))
    pairs24.append((a, max(0.05, a + R.gauss(0, .34 + a * .045))))
    pairs72.append((a, max(0.05, a + R.gauss(0, .62 + a * .085))))

MAE_H = list(range(6, 20))
mae24, mae72 = _MAE24, _MAE72

# --- günlük sapma dağılımı (F − A) [MWh/gün]
# Tek kaynak: ortalama −0,2 · standart sapma 2,0 · 116 geçerli gün.
# Histogram, medyan ve yüzdelikler bu tek dağılımdan türetilir.
import math
MU, SD, NDAYS = _MU, _SD, _NDAYS
_cdf = lambda x: 0.5 * (1 + math.erf((x - MU) / (SD * math.sqrt(2))))
BINS = [(lo, lo + 1, round(NDAYS * (_cdf(lo + 1) - _cdf(lo)))) for lo in range(-6, 6)]
TOTAL = sum(b[2] for b in BINS)


def pct(p):
    """Binlenmiş dağılımdan yüzdelik: eğrinin üzerinde duran nokta."""
    hedef, kum = p / 100 * TOTAL, 0
    for lo, hi, c in BINS:
        if kum + c >= hedef:
            return lo + (hedef - kum) / c
        kum += c
    return 6.0


P10, P50, P90 = pct(10), pct(50), pct(90)


def panel_frame(o, ox, oy, pw, ph, xmax, ymax, xstep, ystep, xlab, ylab, fs,
                xfmt="%d", yfmt="%d", xticks=True, ypad=34, xlabmul=3):
    X = lambda v: ox + pw * v / xmax
    Y = lambda v: oy + ph * (ymax - v) / ymax
    t = 0
    while t <= ymax + 1e-9:
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.2"/>'
                 % (ox, Y(t), ox + pw, Y(t), GRID))
        o.append('<text x="%.1f" y="%.1f" text-anchor="end" font-family="PlexSans" font-size="%d"'
                 ' font-weight="500" fill="#2B3439">%s</text>'
                 % (ox - 7, Y(t) + fs * .34, fs, yfmt % t))
        t += ystep
    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#7C8781" stroke-width="1.4"/>'
             % (ox, Y(0), ox + pw, Y(0)))
    if xticks:
        t = 0
        while t <= xmax + 1e-9:
            o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" '
                     'font-size="%d" font-weight="500" fill="#2B3439">%s</text>'
                     % (X(t), Y(0) + fs * 1.5, fs, xfmt % t))
            t += xstep
    o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" font-size="%d" '
             'font-weight="600" fill="%s">%s</text>'
             % (ox + pw / 2, Y(0) + fs * xlabmul, fs, INK, xlab))
    o.append('<text transform="translate(%.1f,%.1f) rotate(-90)" text-anchor="middle" '
             'font-family="PlexSans" font-size="%d" font-weight="600" fill="%s">%s</text>'
             % (ox - ypad, oy + ph / 2, fs, INK, ylab))
    return X, Y


# ---------------------------------------------------------------- Şekil 8.1
KOR = lambda a: 0.1 * a + 0.2          # ±%10 koridoru (küçük değerlerde taban pay)
oran = lambda ps: 100.0 * sum(1 for a, f in ps if abs(f - a) <= KOR(a)) / len(ps)
ORAN24, ORAN72 = oran(pairs24), oran(pairs72)


def fig81(W=1000, H=326, fs=13):
    pw, ph = 392, 210
    o = []
    X, Y = panel_frame(o, 52, 42, pw, ph, 10, 10, 2, 2, "Gerçekleşen [MW]", "Tahmin [MW]", fs)
    # ±%10 koridoru
    up = [(X(a), Y(min(10, a + KOR(a)))) for a in (0, 10)]
    dn = [(X(a), Y(max(0, a - KOR(a)))) for a in (10, 0)]
    o.append('<polygon points="%s" fill="#F3E7CE"/>'
             % " ".join("%.1f,%.1f" % p for p in up + dn))
    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#8A939A" '
             'stroke-width="1.6"/>' % (X(0), Y(0), X(10), Y(10)))
    for a, f in pairs72:
        o.append('<circle cx="%.1f" cy="%.1f" r="2.9" fill="none" stroke="#B08C43" '
                 'stroke-width="1.3"/>' % (X(a), Y(f)))
    for a, f in pairs24:
        o.append('<circle cx="%.1f" cy="%.1f" r="2.7" fill="%s"/>' % (X(a), Y(f), BRAND))
    o.append('<text x="%.1f" y="%.1f" font-family="PlexSans" font-size="%d" font-weight="600" '
             'fill="%s">±%%10 koridorunda kalan saatler</text>' % (52, 16, fs, INK))
    o.append('<text x="%.1f" y="%.1f" font-family="PlexSans" font-size="%d" font-weight="600" '
             'fill="%s">gün-öncesi %%%d</text>' % (52, 30, fs + 1, BRAND, round(ORAN24)))
    o.append('<text x="%.1f" y="%.1f" font-family="PlexSans" font-size="%d" font-weight="600" '
             'fill="#9A7526">· 24–72 s %%%d</text>' % (205, 30, fs + 1, round(ORAN72)))

    ox2 = 52 + pw + 100
    X2, Y2 = panel_frame(o, ox2, 42, 392, ph, 14, 1.0, 2, .25, "Yerel saat", "MAE [MW]", fs,
                         yfmt="%.2f", xticks=False, ypad=46)
    sw = 392 / len(MAE_H)
    for i in range(len(MAE_H)):
        x0 = ox2 + sw * i + sw * .14
        bw = sw * .33
        o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                 % (x0, Y2(mae24[i]), bw, Y2(0) - Y2(mae24[i]), BRAND))
        o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#D9B871"/>'
                 % (x0 + bw + 2, Y2(mae72[i]), bw, Y2(0) - Y2(mae72[i])))
    for i, h in enumerate(MAE_H):
        if h % 2 == 0:
            o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" '
                     'font-size="%d" font-weight="500" fill="#2B3439">%02d</text>'
                     % (ox2 + sw * (i + .5), Y2(0) + fs * 1.5, fs, h))
    o.append('<text x="%.1f" y="%.1f" font-family="PlexSans" font-size="%d" font-weight="600" '
             'fill="%s">Hatanın gün içi dağılımı</text>' % (ox2, 16, fs, INK))
    # panelin kendi lejantı (çubuk biçiminde)
    lx = ox2 + 392 - 150
    for k, (col, lab) in enumerate(((BRAND, "0–24 s"), ("#D9B871", "24–72 s"))):
        o.append('<rect x="%.1f" y="%.1f" width="9" height="9" fill="%s"/>'
                 % (lx + k * 74, 9, col))
        o.append('<text x="%.1f" y="%.1f" font-family="PlexSans" font-size="%d" '
                 'font-weight="500" fill="#2B3439">%s</text>' % (lx + k * 74 + 13, 17, fs, lab))
    # oransal hata: iki uçtan örnek
    o.append('<text x="%.1f" y="%.1f" font-family="PlexSans" font-size="%d" font-weight="500" '
             'fill="#2B3439">Sabah 0,19 MW, öğlen 0,58 MW — ikisi de üretimin yaklaşık '
             '%%6\u0027sı.</text>' % (ox2, 30, fs - 1))
    return ('<svg class="fig" viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg">%s</svg>'
            % (W, H, "".join(o)))


# ---------------------------------------------------------------- Şekil 8.2
def fig82(W=1000, H=310, fs=13):
    pw, ph = 380, 190
    o = []
    ymax = max(b[2] for b in BINS) + 4
    X, Y = panel_frame(o, 46, 16, pw, ph, 6, ymax, 2, 5, "Sapma (tahmin − gerçekleşen) [MWh/gün]",
                       "Gün sayısı", fs, xticks=False, xlabmul=4.6)
    sx = lambda v: 46 + pw * (v + 6) / 12
    for lo, hi, c in BINS:
        o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#D9B871" '
                 'stroke="#fff" stroke-width="1"/>'
                 % (sx(lo), Y(c), sx(hi) - sx(lo), Y(0) - Y(c)))
    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#B9C4CA" stroke-width="1.2"/>'
             % (sx(0), 16, sx(0), Y(0)))
    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2.2" '
             'stroke-dasharray="6 4"/>' % (sx(P50), 16, sx(P50), Y(0), BRAND))
    o.append('<text x="%.1f" y="%.1f" text-anchor="end" font-family="PlexSans" font-size="%d" '
             'font-weight="600" fill="%s">medyan %s</text>'
             % (sx(P50) - 5, 27, fs, BRAND, tr(P50)))
    o.append('<text x="%.1f" y="%.1f" font-family="PlexSans" font-size="%d" font-weight="500" '
             'fill="#7C868C">sıfır</text>' % (sx(0) + 5, 27, fs - 1))
    o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" font-size="%d" '
             'font-weight="500" fill="#5B686F">← beklentiden fazla üretildi</text>'
             % (sx(-3.2), Y(0) + fs * 3, fs - 1))
    o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" font-size="%d" '
             'font-weight="500" fill="#5B686F">beklentinin altında kalındı →</text>'
             % (sx(3.2), Y(0) + fs * 3, fs - 1))
    for v in (-6, -3, 0, 3, 6):
        o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" '
                 'font-size="%d" font-weight="500" fill="#2B3439">%s</text>'
                 % (sx(v), Y(0) + fs * 1.5, fs, ("+%d" % v) if v > 0 else str(v)))

    ox2 = 46 + pw + 90
    X2, Y2 = panel_frame(o, ox2, 16, 380, ph, 100, 100, 25, 25, "Sapma [MWh/gün]",
                         "Kümülatif [%]", fs, xticks=False)
    cx = lambda v: ox2 + 380 * (v + 6) / 12
    kum, pts = 0, [(cx(-6), Y2(0))]
    for lo, hi, c in BINS:
        kum += c
        pts.append((cx(hi), Y2(kum / TOTAL * 100)))
    o.append('<path d="M %s" fill="none" stroke="%s" stroke-width="2.8" stroke-linejoin="round"/>'
             % (" L ".join("%.1f,%.1f" % p for p in pts), BRAND))
    for v, p, lab in ((P10, 10, "P10"), (P50, 50, "P50"), (P90, 90, "P90")):
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#B9C4CA" '
                 'stroke-width="1.1" stroke-dasharray="4 3"/>' % (cx(-6), Y2(p), cx(v), Y2(p)))
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#B9C4CA" '
                 'stroke-width="1.1" stroke-dasharray="4 3"/>' % (cx(v), Y2(p), cx(v), Y2(0)))
        o.append('<circle cx="%.1f" cy="%.1f" r="4.4" fill="#D9B871" stroke="%s" '
                 'stroke-width="2"/>' % (cx(v), Y2(p), BRAND))
        dy = 15 if p >= 90 else -6
        o.append('<text x="%.1f" y="%.1f" font-family="PlexSans" font-size="%d" '
                 'font-weight="600" fill="%s">%s = %s%s</text>'
                 % (cx(v) + 9, Y2(p) + dy, fs, INK, lab, "+" if v > 0 else "", tr(v)))
    for v in (-6, -3, 0, 3, 6):
        o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" '
                 'font-size="%d" font-weight="500" fill="#2B3439">%s</text>'
                 % (cx(v), Y2(0) + fs * 1.5, fs, ("+%d" % v) if v > 0 else str(v)))
    return ('<svg class="fig" viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg">%s</svg>'
            % (W, H, "".join(o)))


RULES = [
    ("Ölçülmemiş gün", "Karneye katılmaz, ortalamayı seyreltmez; satır “—” olarak basılır."),
    ("Kapsama eşiği", "Gün içi geçerli saat oranı %60'ın altındaysa o gün karne dışıdır."),
    ("Zayıf gün", "Gizlenmez. Amber ya da kırmızı basılır ve nedeni yazılır."),
    ("Küçük örneklem", "Pencerede 14 günden az geçerli gün varsa başlığa uyarı eklenir."),
    ("Pencere tutarlılığı", "Karne, çevrimiçi rapor ve veri servisi aynı 120 günü kullanır."),
]

CSS = """
.fig{margin-top:5mm}
.legend{margin-top:1.5mm}
.legend i.s24{display:inline-block;width:3mm;height:3mm;border-radius:50%;background:BRAND;
  margin-right:1.6mm;vertical-align:-.3mm}
.legend i.s72{display:inline-block;width:3mm;height:3mm;border-radius:50%;background:#D9B871;
  margin-right:1.6mm;vertical-align:-.3mm}
.legend i.kor{display:inline-block;width:4.4mm;height:2.8mm;background:#F3E7CE;
  border:.4pt solid #DCC79A;margin-right:1.6mm;vertical-align:-.4mm}
.legend i.s72{display:inline-block;width:3mm;height:3mm;border-radius:50%;background:none;
  border:1pt solid #B08C43;margin-right:1.6mm;vertical-align:-.3mm}
.legend i.unit{display:inline-block;width:5mm;height:1.2mm;background:#8A939A;
  margin-right:1.6mm;vertical-align:-.1mm}
h2{font-size:10.5pt;font-weight:600;padding-bottom:2mm;border-bottom:.9pt solid BRAND;
  margin-top:7mm}
table{margin-top:3mm}
th{font-size:7.9pt;padding:1.8mm 2.5mm}
td{font-size:8.4pt;padding:1.7mm 2.5mm}
td:first-child{font-weight:600;width:40mm}
""".replace("BRAND", BRAND)

rows = "".join("<tr><td>%s</td><td>%s</td></tr>" % r for r in RULES)

BODY = """<div class="page"><div class="sheet">
""" + HEAD + """
  <div class="eyebrow">Doğruluk karnesi · devam</div>
  <h1>Hata nerede ve ne kadar?</h1>
  <p class="lead" style="max-width:162mm">Ortalama hata tek başına yeterli değildir: hatanın
  hangi saatlerde büyüdüğü, sistematik bir yanlılık taşıyıp taşımadığı ve hangi ufukta ne kadar
  arttığı ayrıca ölçülür.</p>

  """ + fig81() + """
    <div class="legend"><span><i class="s24"></i>Gün-öncesi (0–24 s)</span>
      <span><i class="s72"></i>24–72 saat</span>
      <span><i class="kor"></i>±%10 koridoru</span>
      <span><i class="unit"></i>Birim doğru</span></div>
    <div class="figcap"><b>Şekil 8.1</b>&nbsp;&nbsp;Solda saatlik tahmin–gerçekleşen saçılımı. Kum rengi
      koridor, tahminin gerçekleşenden ±%10'dan az saptığı bölgedir: gün-öncesi saatlerin
      %""" + str(round(ORAN24)) + """'i bu koridorda kalırken, 24–72 saatlik tahminlerde oran
      %""" + str(round(ORAN72)) + """'a düşer — ufuk uzadıkça belirsizlik artar. Sağda hatanın gün içi
      dağılımı: mutlak hata öğle saatlerinde büyür, çünkü üretim de o saatlerde büyüktür;
      oransal hata gün boyunca sabit kalır.</div>

  """ + fig82() + """
    <div class="figcap"><b>Şekil 8.2</b>&nbsp;&nbsp;Günlük sapma (tahmin eksi gerçekleşen), 116 geçerli
      gün. Solda dağılımın kendisi: medyan """ + tr(P50) + """ MWh, yani sıfıra çok yakın —
      model ne sürekli yüksek ne sürekli düşük tahmin ediyor, sistematik bir yanlılık yok.
      Sağda aynı dağılımın kümülatif hâli: günlerin %80'i """ + tr(P10) + """ ile +""" + tr(P90) + """ MWh
      arasında kalıyor. Her iki panel de tek bir dağılımdan türetilir.</div>

  <h2>Karnenin bütünlük kuralları</h2>
  <table>
    <tr><th>Kural</th><th>Uygulama</th></tr>
    """ + rows + """
  </table>
""" + foot(8) + """
</div></div>"""

build("PVQuant_Konya_GES_s08_hata_dagilimi", CSS, BODY,
      "PVQuant — Konya GES · Hata dağılımı")
