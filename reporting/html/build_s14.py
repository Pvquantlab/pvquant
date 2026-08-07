from pvq import *

tr = lambda x, d=1: ("%.*f" % (d, x)).replace(".", ",")

from veri import EVRIM

STANDART = [
    ("IEC 61724-1", "Fotovoltaik sistem performans izleme standardı",
     "Özgül üretim, performans oranı ve veri erişilebilirliği tanımları buradan alınır."),
    ("IEA-PVPS Task 13", "Performans ve belirsizlik raporlama kılavuzu",
     "P50 / P75 / P90 aşılma olasılığı dili ve hata raporlama geleneği."),
    ("EPRI Forecast Arbiter", "Tahmin doğrulama çerçevesi",
     "Kazanç puanının tanımı ve naif referans olarak akıllı süreklilik seçimi."),
]

SINIR = [
    ("Hava modeli sabitlenmemiştir",
     "Hava tahmini sağlayıcısından “en uygun model” seçeneğiyle alınır; hangi sayısal hava "
     "modelinin döndüğü tahmin kaydına işlenmez. Bu, tahminin geriye dönük denetiminde tek "
     "eksik halkadır ve geliştirme listesindedir."),
    ("Santral verisi kapsaması hedefin altındadır",
     "Tüm arşivde %71; hedef en az %80. Kaynak dosyadaki bozuk yıl bloğu düzeltilene kadar "
     "kalibrasyon, olması gerekenden az saatle çalışmaktadır (sayfa 10)."),
    ("Normal dağılım varsayımı yalnızca yıllık eğride kullanılır",
     "Sayfa 11'deki aşılma olasılığı eğrisi normal dağılım varsayar; bu bilinçli bir "
     "basitleştirmedir. Günlük ve saatlik aralıklar bu varsayımı kullanmaz."),
]


def evrim(W=1000, H=286, ml=62, mb=52, fs=14):
    MR, MT = 92, 26
    PW, PH = W - ml - MR, H - MT - mb
    n = len(EVRIM)
    step = PW / (n - 1)
    cx = lambda i: ml + step * i
    y = lambda v: MT + PH * (76 - v) / (76 - 52)
    o = []
    for t in range(52, 77, 6):
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.3"/>'
                 % (ml, y(t), W - MR, y(t), GRID))
        o.append('<text x="%.1f" y="%.1f" text-anchor="end" font-family="PlexSans" font-size="%d"'
                 ' font-weight="500" fill="#2B3439">%d</text>' % (ml - 9, y(t) + fs * .34, fs, t))
    ust = " ".join("%.1f,%.1f" % (cx(i), y(v + b)) for i, (_, v, b) in enumerate(EVRIM))
    alt = " ".join("%.1f,%.1f" % (cx(i), y(v - b))
                   for i, (_, v, b) in reversed(list(enumerate(EVRIM))))
    o.append('<polygon points="%s %s" fill="%s"/>' % (ust, alt, FAN_AREA))
    for sgn in (1, -1):
        o.append('<path d="M %s" fill="none" stroke="%s" stroke-width="1.3"/>'
                 % (" L ".join("%.1f,%.1f" % (cx(i), y(v + sgn * b))
                               for i, (_, v, b) in enumerate(EVRIM)), FAN_EDGE))
    son = EVRIM[-1][1]
    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#9AA5AB" stroke-width="1.2" '
             'stroke-dasharray="5 4"/>' % (ml, y(son), W - MR + 46, y(son)))
    o.append('<path d="M %s" fill="none" stroke="%s" stroke-width="3" stroke-linejoin="round"/>'
             % (" L ".join("%.1f,%.1f" % (cx(i), y(v)) for i, (_, v, _b) in enumerate(EVRIM)),
                BRAND))
    for i, (_, v, _b) in enumerate(EVRIM):
        o.append('<circle cx="%.1f" cy="%.1f" r="4" fill="#fff" stroke="%s" stroke-width="2.2"/>'
                 % (cx(i), y(v), BRAND))
    for i in (0, n - 1):
        b = EVRIM[i][2]
        o.append('<text x="%.1f" y="%.1f" text-anchor="%s" font-family="PlexSans" font-size="%d" '
                 'font-weight="600" fill="#8A6A28">±%s MWh</text>'
                 % (cx(i) + (6 if i == 0 else -6), y(EVRIM[i][1] + b) - 8,
                    "start" if i == 0 else "end", fs, tr(b)))
    o.append('<text x="%.1f" y="%.1f" font-family="PlexSans" font-size="%d" font-weight="600" '
             'fill="%s">son tahmin</text>' % (W - MR + 6, y(son) - 7, fs, INK))
    o.append('<text x="%.1f" y="%.1f" font-family="PlexSans" font-size="%d" font-weight="600" '
             'fill="%s">%s MWh</text>' % (W - MR + 6, y(son) + 9, fs, INK, tr(son)))
    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#7C8781" stroke-width="1.5"/>'
             % (ml, y(52), W - MR, y(52)))
    for i, (ad, _v, _b) in enumerate(EVRIM):
        o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" '
                 'font-size="%d" font-weight="500" fill="#2B3439">%s</text>'
                 % (cx(i), y(52) + fs * 1.5, fs, ad))
    o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" font-size="%d" '
             'font-weight="600" fill="%s">Tahminin hazırlandığı gün</text>'
             % (ml + PW / 2, y(52) + fs * 3, fs + 1, INK))
    o.append('<text transform="translate(13,%.1f) rotate(-90)" text-anchor="middle" '
             'font-family="PlexSans" font-size="%d" font-weight="600" fill="%s">05 Ağustos '
             'beklentisi [MWh]</text>' % (MT + PH / 2, fs + 1, INK))
    return ('<svg class="fig" viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" role="img" '
            'aria-label="Ayni gun icin ardisik tahminler">%s</svg>' % (W, H, "".join(o)))


std = "".join('<tr><td class="ad">%s</td><td class="kn">%s</td><td>%s</td></tr>' % s
              for s in STANDART)
sinir = "".join('<div class="sn"><b>%s</b><span>%s</span></div>' % s for s in SINIR)

CSS = """
h2{font-size:10.5pt;font-weight:600;padding-bottom:2mm;border-bottom:.9pt solid BRAND;
  margin-top:7mm}
table{margin-top:3mm}
th{font-size:7.9pt;padding:1.7mm 2.5mm}
td{font-size:8.4pt;padding:1.6mm 2.5mm;vertical-align:top}
td.ad{font-weight:600;width:38mm}
td.kn{width:56mm}
.sn{padding:3mm 0;border-bottom:.6pt solid #E8EDEA}
.sn b{display:block;font-size:9.2pt;font-weight:600;margin-bottom:1.2mm}
.sn span{display:block;font-size:8.7pt;line-height:1.5;color:#2B3532}
.fig{margin-top:5mm}
""".replace("BRAND", BRAND)

BODY = """<div class="page"><div class="sheet">
""" + HEAD + """
  <div class="eyebrow">Metodoloji · devam</div>
  <h1>Standartlar, sınırlar ve tahmin evrimi</h1>
  <p class="lead" style="max-width:162mm">Bu sayfa raporun dayandığı çerçeveleri, bilinen
  eksiklerini ve tahminin zaman içinde nasıl olgunlaştığını gösterir. Bir tahmin sisteminin
  güvenilirliği, neyi bilmediğini de yazmasıyla ölçülür.</p>

  <h2>Dayanılan çerçeveler</h2>
  <table>
    <tr><th>Çerçeve</th><th>Nedir</th><th>Raporda nerede kullanılır</th></tr>
    """ + std + """
  </table>

  <h2>Bilinen sınırlar</h2>
  """ + sinir + """

  <h2>Aynı gün için ardışık tahminler</h2>
  """ + evrim() + """
    <div class="figcap"><b>Şekil 14.1</b>&nbsp;&nbsp;05 Ağustos hedef günü için son yedi
      tahmin. Tahminler güncellenmez, üst üste eklenir; böylece aynı gün için verilen her
      beklenti geriye dönük karşılaştırılabilir. Gün yaklaştıkça beklenti 63,2'den 65,8 MWh'e
      yakınsamış, olasılık aralığı ±7,4'ten ±2,8 MWh'e daralmıştır. 3 Ağustos'taki geçici
      düşüş, o gün modele giren hava senaryosundaki bulutluluğun ertesi gün geri
      alınmasındandır — evrim grafiği tam da bu tür oynaklığı görünür kılmak için vardır.</div>
""" + foot(14) + """
</div></div>"""

build("PVQuant_Konya_GES_s14_standartlar", CSS, BODY,
      "PVQuant — Konya GES · Standartlar ve tahmin evrimi")
