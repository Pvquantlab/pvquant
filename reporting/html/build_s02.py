from pvq import *
from veri import GUN_SAYISI  # v2.156: ufuk kopyası tek kaynaktan
from veri import IKLIM_ARALIK

CSS = """
.cols{display:flex;gap:12mm;margin-top:8mm}
.toc{flex:1.45}
.guide{flex:1}

/* --- ana bölüm satırı: kod + başlık + sayfa, kalın --- */
.grp{display:flex;align-items:baseline;gap:4mm;margin-top:5mm;padding-bottom:1.8mm;
  border-bottom:.9pt solid BRAND}
.grp:first-child{margin-top:0}
.grp .t{font-size:11pt;font-weight:600;color:INK;flex:1;line-height:1.2}
.grp .pg{font-size:11pt;font-weight:600;color:INK;width:8mm;text-align:right;flex:none}

/* --- alt satırlar --- */
.item{display:flex;align-items:baseline;gap:4mm;padding:1.6mm 0 1.6mm 8mm;
  border-bottom:.6pt solid #E8EDEA}
.item .t{font-size:9.4pt;line-height:1.35;flex:1}
.item .t em{font-style:normal;color:SEC;font-size:8.4pt}
.item .pg{font-size:9.4pt;font-weight:600;width:8mm;text-align:right;flex:none}

.guide h3{font-size:10pt;font-weight:600;color:INK;padding-bottom:2mm;
  border-bottom:.9pt solid BRAND}
.pr{padding:3.6mm 0;border-bottom:.6pt solid #E8EDEA}
.pr b{display:block;font-size:9.4pt;font-weight:600;margin-bottom:1.2mm}
.pr span{font-size:8.5pt;line-height:1.52;color:#2B3532;display:block}

.keybox{background:WASH;padding:4.5mm 5mm;margin-top:7mm}
.keybox h3{font-size:10pt;font-weight:600;color:INK;padding-bottom:2mm;
  border-bottom:.9pt solid BRAND2;margin-bottom:1mm}
.key{padding:2.4mm 0;border-bottom:.6pt solid #C6DBE4}
.key:last-child{border-bottom:0;padding-bottom:0}
.key b{display:block;font-size:9pt;font-weight:600;margin-bottom:.8mm}
.key span{font-size:8.4pt;line-height:1.48;color:#2B3532}
""".replace("BRAND2", BRAND2).replace("BRAND", BRAND).replace("RULE", RULE) \
   .replace("SEC", SEC).replace("WASH", WASH).replace("INK", INK)

# (kod, başlık, kendi sayfası|None, [(alt başlık, açıklama, sayfa)])
TOC = [
    ("S2", "Yönetici özeti", 3, []),
    ("S3", "Tahmin detayı", None, [
        ("Günlük üretim ve olasılık bandı", None, 4),
        ("Saatlik profiller", "tipik gün ve ilk sekiz gün", 5),
        ("Saat × gün matrisi", "analist görünümü", 6)]),
    ("S4", "Doğruluk karnesi", None, [
        ("Her tahmin, ertesi gün sınava girer", "naif referans ve skill", 7),
        ("Saçılım, sapma ve bütünlük kuralları", None, 8)]),
    ("S5", "Kalibrasyon", None, [
        ("Fizikten hibrite: iyileşmenin kanıtı", "katsayılar ve şelale", 9),
        ("Bağımsız test ve veri kalitesi", "holdout ve kapsama", 10)]),
    ("S6", "İklim bağlamı", None, [
        ("İklim zarfı ve aşılma olasılıkları", None, 11),
        ("Yıl × ay üretim matrisi", IKLIM_ARALIK, 12)]),
    ("S7", "Model zinciri ve veri künyesi", 13, []),
    ("S8", "Standartlar, sınırlar ve tahmin evrimi", 14, []),
    ("EK", "Ekler", None, [
        ("EK-A · Metrikler, belirsizlik bütçesi ve kısaltmalar", None, 15),
        ("EK-B · Sözlük, referanslar ve yasal bilgi", None, 16)]),
]

rows = []
for code, title, pg, kids in TOC:
    rows.append('<div class="grp"><div class="t">%s</div>'
                '<div class="pg">%s</div></div>' % (title, pg if pg else ""))
    for t, sub, p in kids:
        t = t + (' <em>· %s</em>' % sub if sub else "")
        rows.append('<div class="item"><div class="t">%s</div><div class="pg">%d</div></div>'
                    % (t, p))

BODY = """<div class="page"><div class="sheet">
""" + HEAD + """
  <div class="eyebrow">İçindekiler</div>
  <h1>Bu raporda ne var?</h1>
  <p class="lead" style="max-width:150mm">Rapor sekiz bölümden oluşur. İlk üç bölüm önümüzdeki
  """ + str(GUN_SAYISI) + """ günü anlatır; dördüncü bölüm geçmiş tahminlerin ne kadar tuttuğunu gösterir; kalan bölümler
  bu sayıların nasıl üretildiğini ve hangi belirsizlikleri taşıdığını açıklar.</p>

  <div class="cols">
    <div class="toc">""" + "".join(rows) + """</div>
    <div class="guide">
      <h3>Raporun üç kuralı</h3>
      <div class="pr"><b>Veri yoksa boş kalır</b><span>Ölçülmemiş bir gün ya da hesaplanamayan
        bir değer sıfırla doldurulmaz; “—” olarak basılır. Veriyle dolamayan bölüm hiç
        yayımlanmaz.</span></div>
      <div class="pr"><b>Her sayı tek bir kaynaktan gelir</b><span>Bu PDF'te gördüğünüz her değer,
        çevrimiçi raporda ve size iletilen veri dosyasında birebir aynıdır.</span></div>
      <div class="pr"><b>Her tahmin ertesi gün sınanır</b><span>Yayımlanan her tahmin, ertesi gün
        gerçekleşen üretimle karşılaştırılır ve sonuç kalıcı olarak saklanır; S4 bunun
        120 günlük özetidir.</span></div>

      <div class="keybox">
        <h3>Okuma anahtarı</h3>
        <div class="key"><b>P50</b><span>En olası üretim; aşılma olasılığı %50.</span></div>
        <div class="key"><b>P10–P90 bandı</b><span>On raporun sekizinde gerçekleşen bu aralıkta
          kalır; alt sınır taahhüt için önerilir.</span></div>
        <div class="key"><b>WMAPE</b><span>Üretimle ağırlıklandırılmış ortalama hata
          oranı.</span></div>
        <div class="key"><b>Skill</b><span>Basit bir referans yönteme kıyasla kazanılan isabet;
          0 = referansla aynı.</span></div>
      </div>
    </div>
  </div>
""" + foot(2) + """
</div></div>"""

build("PVQuant_Konya_GES_s02_icindekiler", CSS, BODY, "PVQuant — Konya GES · İçindekiler")
