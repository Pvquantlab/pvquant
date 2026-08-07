"""PVQuant rapor tasarım sistemi — tüm sayfalar bu modülden beslenir."""
import base64, os

import os as _os
_BURASI = _os.path.dirname(_os.path.abspath(__file__))
FONTS = _os.environ.get("PVQ_FONTLAR", _os.path.join(_BURASI, "fontlar"))
OUT = _os.environ.get("PVQ_CIKTI", _os.path.join(_BURASI, "cikti"))
_os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- renk paleti
BRAND, BRAND2, DEEP = "#0D4C68", "#2B7B9B", "#082F42"
FAN_AREA, FAN_EDGE = "#F0E3C9", "#DCC79A"
OK = "#2E7856"   # durum rengi: marka renginden bağımsız
INK, SEC, RULE = "#11171A", "#414B46", "#CDD6D1"
WASH, GRID = "#E7F2F6", "#E2E7EA"
AMBER, RED = "#A87519", "#A83A2B"


def _face(fam, weight, file):
    b = base64.b64encode(open(f"{FONTS}/{file}", "rb").read()).decode()
    return ("@font-face{font-family:'%s';font-style:normal;font-weight:%d;font-display:block;"
            "src:url(data:font/ttf;base64,%s) format('truetype');}" % (fam, weight, b))


FONTCSS = "".join([
    _face("PlexSans", 400, "PlexSans-400.ttf"),
    _face("PlexSans", 500, "PlexSans-500.ttf"),
    _face("PlexSans", 600, "PlexSans-600.ttf"),
    _face("PlexMono", 400, "PlexMono-400.ttf"),
    _face("SourceSerif", 600, "SourceSerif-600.ttf"),
    _face("SourceSerif", 700, "SourceSerif-700.ttf"),
])

# ---------------------------------------------------------------- ortak stil
BASE = """
*{box-sizing:border-box;margin:0;padding:0}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{background:#E8EBE9;font-family:PlexSans,sans-serif;color:INK;font-feature-settings:"tnum" 1}
@page{size:A4;margin:0}
.page{width:210mm;height:297mm;background:#fff;margin:12mm auto;
  box-shadow:0 2px 24px rgba(0,0,0,.28);overflow:hidden;display:flex;flex-direction:column}
@media print{body{background:#fff}.page{margin:0;box-shadow:none}}

/* --- iç sayfa başlığı ve altbilgisi --- */
.sheet{padding:14mm 18mm 11mm;flex:1;display:flex;flex-direction:column}
.head{display:flex;justify-content:space-between;align-items:baseline;padding-bottom:3mm;
  border-bottom:1.2pt solid BRAND;font-size:8.5pt;color:SEC}
.head .m{font-size:10pt;font-weight:600;color:BRAND;letter-spacing:-.015em}
.head .m span{font-weight:400;color:SEC;font-size:8.2pt;padding-left:2.6mm;margin-left:2.6mm;
  border-left:1px solid RULE}
.foot{margin-top:auto;padding-top:3mm;border-top:.6pt solid RULE;display:flex;
  justify-content:space-between;align-items:baseline;font-size:7.6pt;color:SEC}
.foot b{color:BRAND;font-weight:600;letter-spacing:.08em}

/* --- bölüm başlıkları --- */
.eyebrow{font-size:7.9pt;letter-spacing:.18em;text-transform:uppercase;color:BRAND;
  font-weight:600;margin-top:9mm}
h1{font-family:SourceSerif,Georgia,serif;font-weight:700;font-size:26pt;line-height:1.04;
  letter-spacing:-.016em;margin-top:2.5mm}
h2{font-size:10pt;font-weight:600;margin-top:7mm}
p{font-size:9.2pt;line-height:1.58;margin-top:3.5mm}
.lead{font-size:9.6pt;line-height:1.55}

/* --- şekil --- */
.fig{display:block;width:100%;height:auto}
.legend{display:flex;gap:7mm;align-items:center;font-size:8.2pt;font-weight:600;color:INK;margin-top:1mm}
.legend i{display:inline-block;width:4mm;height:2.4mm;background:BRAND2;margin-right:1.6mm;
  vertical-align:-.3mm}
.legend i.w{width:.5mm;height:3.4mm;background:#082F42}
.legend i.band{display:inline-block;width:4mm;height:2.6mm;background:#C4E1EA;border:.4pt solid #7FB9CC;margin-right:1.6mm;vertical-align:-.3mm}
.legend i.line{display:inline-block;width:5mm;height:1.1mm;background:#0D4C68;margin-right:1.6mm;vertical-align:-.1mm}
.legend i.fan{display:inline-block;width:4.4mm;height:2.8mm;background:#F0E3C9;border:.4pt solid #DCC79A;margin-right:1.6mm;vertical-align:-.4mm}
.figcap{font-size:8pt;line-height:1.5;color:INK;margin-top:2.5mm}
.figcap b{color:INK;font-weight:600}

/* --- veri satırları / tablolar --- */
.row{display:flex;gap:3mm;font-size:8.4pt;line-height:1.5;padding:.15mm 0}
.row dt{color:SEC;width:27.5mm;flex:none}
.row dd{font-weight:500}
.mono{font-family:PlexMono;font-size:7.6pt;letter-spacing:-.02em}
table{border-collapse:collapse;width:100%;font-size:8.4pt}
th{background:BRAND;color:#fff;font-weight:600;text-align:left;padding:2mm 2.5mm;
  font-size:7.9pt;letter-spacing:.03em}
td{padding:1.7mm 2.5mm;border-bottom:.6pt solid RULE}
tr:nth-child(even) td{background:#F4F8FA}
.num{text-align:right;font-variant-numeric:tabular-nums}

/* --- kutular --- */
.note{background:WASH;border-left:1.6pt solid BRAND2;padding:3.5mm 4mm;margin-top:5mm}
.note h3{font-size:8.4pt;font-weight:600;color:BRAND;margin-bottom:1.5mm}
.note p{font-size:8.3pt;line-height:1.5;margin-top:1.5mm}
.note p:first-of-type{margin-top:0}
.k{font-size:7.6pt;letter-spacing:.11em;text-transform:uppercase;color:SEC}
.v{font-family:SourceSerif,Georgia,serif;font-size:21pt;font-weight:600;line-height:1.05;
  margin-top:1.3mm;letter-spacing:-.01em}
.v u{text-decoration:none;font-family:PlexSans;font-size:9.6pt;font-weight:500;color:SEC;
  padding-left:1.2mm}
.n{font-size:7.9pt;color:SEC;margin-top:1.1mm;line-height:1.4}
""".replace("INK", INK).replace("SEC", SEC).replace("RULE", RULE).replace("WASH", WASH) \
   .replace("BRAND2", BRAND2).replace("BRAND", BRAND)

HEAD = ('<div class="head"><div class="m">PVQuant<span>Kanıta dayalı üretim tahmini</span></div>'
        '<div>Konya GES · 05–20 Ağustos 2026</div></div>')


def foot(page):
    return ('<div class="foot"><div><b>MOD C · HİBRİT</b></div>'
            '<div>Sayfa %d / 16</div></div>' % page)


def shell(css, body, title):
    return ("<!doctype html><html lang=\"tr\"><head><meta charset=\"utf-8\"><title>%s</title>"
            "<style>%s%s%s</style></head><body>%s</body></html>"
            % (title, FONTCSS, BASE, css, body))


def build(name, css, body, title):
    from weasyprint import HTML as WH
    hp = f"{OUT}/{name}.html"
    open(hp, "w", encoding="utf-8").write(shell(css, body, title))
    doc = WH(hp).render()
    doc.write_pdf(f"{OUT}/{name}.pdf")
    n = len(doc.pages)
    print(f"{name}: {n} sayfa" + ("" if n == 1 else "   ← TAŞMA VAR"))
    return n


# ---------------------------------------------------------------- sütun grafiği
def bar_chart(vals, band, labels, xtitle, ytitle, ymax=80, step=20, W=1000, H=270,
              ml=58, mb=58, fs=16, bar=BRAND2, whisk="#0C3123"):
    MR, MT = 8, 12
    PW, PH = W - ml - MR, H - MT - mb
    slot = PW / len(vals)
    bw = slot * .54
    cx = lambda i: ml + slot * (i + .5)
    y = lambda v: MT + PH * (ymax - v) / ymax
    o = []
    for t in range(0, ymax + 1, step):
        yy = y(t)
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.4"/>'
                 % (ml, yy, W - MR, yy, GRID))
        o.append('<text x="%.1f" y="%.1f" text-anchor="end" font-family="PlexSans" font-size="%d"'
                 ' fill="%s">%d</text>' % (ml - 10, yy + fs * .34, fs, SEC, t))
    for i, v in enumerate(vals):
        o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                 % (cx(i) - bw / 2, y(v), bw, y(0) - y(v), bar))
    if band:
        for i, v in enumerate(vals):
            hi, lo, c = y(v + band[i]), y(v - band[i]), cx(i)
            o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.8"/>'
                     % (c, hi, c, lo, whisk))
            for yy in (hi, lo):
                o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                         'stroke-width="1.8"/>' % (c - 7, yy, c + 7, yy, whisk))
    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#7C8781" stroke-width="1.6"/>'
             % (ml, y(0), W - MR, y(0)))
    for i, lb in enumerate(labels):
        o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" '
                 'font-size="%d" fill="%s">%s</text>' % (cx(i), y(0) + fs * 1.4, fs, SEC, lb))
    o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" font-size="%d" '
             'fill="%s">%s</text>' % (ml + PW / 2, y(0) + fs * 2.9, fs, SEC, xtitle))
    o.append('<text transform="translate(16,%.1f) rotate(-90)" text-anchor="middle" '
             'font-family="PlexSans" font-size="%d" fill="%s">%s</text>'
             % (MT + PH / 2, fs, SEC, ytitle))
    return ('<svg class="fig" viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" role="img" '
            'aria-label="%s">%s</svg>' % (W, H, xtitle, "".join(o)))


# ------------------------------------------------- bant sütunu (PVQuant biçimi)
def band_columns(vals, half, labels, xtitle, ytitle, ymax=80, step=20, W=1000, H=300,
                 ml=58, mb=58, fs=15, solid=BRAND2, band="#C7E0D2", mark="#0C3123"):
    """Alt sınıra kadar dolu sütun, P10–P90 arası açık kılıf, beklentide koyu çizgi."""
    MR, MT = 8, 12
    PW, PH = W - ml - MR, H - MT - mb
    slot = PW / len(vals)
    bw = slot * .58
    cx = lambda i: ml + slot * (i + .5)
    y = lambda v: MT + PH * (ymax - v) / ymax
    o = []
    for t in range(0, ymax + 1, step):
        yy = y(t)
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.4"/>'
                 % (ml, yy, W - MR, yy, GRID))
        o.append('<text x="%.1f" y="%.1f" text-anchor="end" font-family="PlexSans" font-size="%d"'
                 ' fill="%s">%d</text>' % (ml - 10, yy + fs * .34, fs, SEC, t))
    for i, v in enumerate(vals):
        lo, hi = v - half[i], v + half[i]
        x0 = cx(i) - bw / 2
        # kesin bölge: 0 → P10
        o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                 % (x0, y(lo), bw, y(0) - y(lo), solid))
        # belirsizlik kılıfı: P10 → P90
        o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" '
                 'stroke="#A8CBB8" stroke-width="1"/>' % (x0, y(hi), bw, y(lo) - y(hi), band))
        # beklenti çizgisi
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2.6"/>'
                 % (x0 - 2, y(v), x0 + bw + 2, y(v), mark))
    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#7C8781" stroke-width="1.6"/>'
             % (ml, y(0), W - MR, y(0)))
    for i, lb in enumerate(labels):
        o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" '
                 'font-size="%d" fill="%s">%s</text>' % (cx(i), y(0) + fs * 1.4, fs, SEC, lb))
    o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" font-size="%d" '
             'fill="%s">%s</text>' % (ml + PW / 2, y(0) + fs * 2.9, fs, SEC, xtitle))
    o.append('<text transform="translate(16,%.1f) rotate(-90)" text-anchor="middle" '
             'font-family="PlexSans" font-size="%d" fill="%s">%s</text>'
             % (MT + PH / 2, fs, SEC, ytitle))
    return ('<svg class="fig" viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" role="img" '
            'aria-label="%s">%s</svg>' % (W, H, xtitle, "".join(o)))


# ------------------------------------------------- yelpaze (PVQuant standart biçimi)
def fan_chart(vals, half, labels, xtitle, ytitle, ymin=40, ymax=80, step=10,
              W=1000, H=280, ml=54, mb=52, fs=15, highlight=None, hl_label=None):
    """Beklenti çizgi, %80 olasılık aralığı alan. highlight=(i0,i1) vurgulu gün aralığı."""
    MR, MT = 10, 16
    PW, PH = W - ml - MR, H - MT - mb
    n = len(vals)
    slot = PW / n
    cx = lambda i: ml + slot * (i + .5)
    y = lambda v: MT + PH * (ymax - v) / (ymax - ymin)
    lo = [a - b for a, b in zip(vals, half)]
    hi = [a + b for a, b in zip(vals, half)]
    o = []

    if highlight:
        i0, i1 = highlight
        x0, x1 = ml + slot * i0, ml + slot * (i1 + 1)
        o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#F1F4F6"/>'
                 % (x0, MT, x1 - x0, PH))
        if hl_label:
            o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" '
                     'font-size="%d" fill="%s">%s</text>'
                     % ((x0 + x1) / 2, MT - 4, fs - 1, SEC, hl_label))

    t = ymin
    while t <= ymax + .001:
        yy = y(t)
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.3"/>'
                 % (ml, yy, W - MR, yy, GRID))
        o.append('<text x="%.1f" y="%.1f" text-anchor="end" font-family="PlexSans" font-size="%d"'
                 ' font-weight="500" fill="#2B3439">%d</text>' % (ml - 9, yy + fs * .34, fs, t))
        t += step

    pts = " ".join("%.1f,%.1f" % (cx(i), y(hi[i])) for i in range(n))
    pts += " " + " ".join("%.1f,%.1f" % (cx(i), y(lo[i])) for i in reversed(range(n)))
    o.append('<polygon points="%s" fill="%s"/>' % (pts, FAN_AREA))
    for series in (hi, lo):
        o.append('<path d="M %s" fill="none" stroke="%s" stroke-width="1.4"/>'
                 % (" L ".join("%.1f,%.1f" % (cx(i), y(series[i])) for i in range(n)), FAN_EDGE))
    o.append('<path d="M %s" fill="none" stroke="%s" stroke-width="3.2" stroke-linejoin="round" '
             'stroke-linecap="round"/>'
             % (" L ".join("%.1f,%.1f" % (cx(i), y(vals[i])) for i in range(n)), BRAND))
    for i in range(n):
        o.append('<circle cx="%.1f" cy="%.1f" r="4" fill="#fff" stroke="%s" stroke-width="2.2"/>'
                 % (cx(i), y(vals[i]), BRAND))

    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#7C8781" stroke-width="1.5"/>'
             % (ml, y(ymin), W - MR, y(ymin)))
    for i, lb in enumerate(labels):
        o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" '
                 'font-size="%d" font-weight="500" fill="#2B3439">%s</text>'
                 % (cx(i), y(ymin) + fs * 1.5, fs, lb))
    o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" font-size="%d" '
             'font-weight="600" fill="%s">%s</text>'
             % (ml + PW / 2, y(ymin) + fs * 3.1, fs + 1, INK, xtitle))
    o.append('<text transform="translate(14,%.1f) rotate(-90)" text-anchor="middle" '
             'font-family="PlexSans" font-size="%d" font-weight="600" fill="%s">%s</text>'
             % (MT + PH / 2, fs + 1, INK, ytitle))
    return ('<svg class="fig" viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" role="img" '
            'aria-label="%s">%s</svg>' % (W, H, xtitle, "".join(o)))


# ------------------------------------------------- iklim arşivi (aylık üretim, MWh)
AY_TR = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
IKLIM = {
    2007: [971, 1178, 1514, 1913, 2310, 2370, 2142, 2231, 1847, 1497, 1029, 895],
    2008: [1010, 1139, 1693, 1805, 2280, 2487, 2362, 2268, 1854, 1487, 1039, 917],
    2009: [1068, 1031, 1580, 1781, 2082, 2472, 2381, 2022, 1743, 1437, 1033, 889],
    2010: [962, 1114, 1567, 1650, 2097, 2114, 2224, 1954, 1626, 1332, 1051, 877],
    2011: [941, 1081, 1572, 1604, 2114, 2246, 2452, 2236, 1718, 1378, 1036, 931],
    2012: [942, 1059, 1482, 1694, 2050, 2037, 2202, 2026, 1769, 1387, 1002, 854],
    2013: [1027, 1227, 1583, 1906, 2105, 2385, 2194, 2023, 1788, 1394, 1098, 999],
    2014: [1085, 1227, 1763, 2082, 2433, 2544, 2739, 2479, 1892, 1605, 1191, 945],
    2015: [1027, 1085, 1611, 1814, 2191, 2209, 2311, 1970, 1663, 1442, 948, 909],
    2016: [907, 1150, 1440, 1827, 2150, 2056, 2419, 2288, 1720, 1367, 1028, 811],
    2017: [1128, 1163, 1617, 1820, 2229, 2248, 2609, 2281, 1948, 1496, 1078, 905],
    2018: [1038, 1194, 1591, 1867, 2145, 2305, 2657, 2223, 1762, 1519, 1195, 853],
    2019: [1048, 1147, 1466, 1947, 2278, 2388, 2341, 2327, 1794, 1470, 1046, 857],
    2020: [1022, 1043, 1473, 1694, 2016, 2096, 2266, 2030, 1652, 1338, 1059, 853],
    2021: [1029, 1096, 1421, 1876, 2281, 2251, 2380, 2257, 1830, 1477, 1030, 937],
    2022: [1001, 1246, 1662, 1977, 2520, 2581, 2308, 2103, 1936, 1417, 1115, 960],
    2023: [893, 974, 1489, 1723, 2064, 2183, 2130, 1938, 1673, 1291, 932, 856],
    2024: [1006, 1150, 1454, 1730, 2066, 2167, 2337, 2088, 1786, 1434, 1159, 808],
    2025: [933, 995, 1377, 1490, 1895, 2105, 2082, 1916, 1553, 1345, 938, 702],
    2026: [922, 965, 1238, 1420, 2205, 2173, 2105, None, None, None, None, None],
}
TAM_YILLAR = list(range(2007, 2026))          # 19 tam yıl
LTA_AY = [round(sum(IKLIM[y][m] for y in TAM_YILLAR) / len(TAM_YILLAR)) for m in range(12)]
LTA_YIL = sum(LTA_AY)


def ay_pct(m, p):
    """Bir ayın 19 yıllık dağılımından yüzdelik (doğrusal ara değer)."""
    v = sorted(IKLIM[y][m] for y in TAM_YILLAR)
    k = (len(v) - 1) * p / 100
    i = int(k)
    return v[i] + (v[min(i + 1, len(v) - 1)] - v[i]) * (k - i)
