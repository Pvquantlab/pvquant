"""16 sayfayı tek HTML'de birleştirir.

Her sayfanın kendi CSS'i #pNN altında kapsüllenir; böylece sayfalar arasında aynı adı
taşıyan kurallar (h2, table, td …) birbirini ezmez. Yazı tipleri belgeye bir kez gömülür.
"""
import glob, os, re

from pvq import OUT

# E.4 (v2.344): sayfa seçkisi — kopru.py ile AYNI sözleşme (env + ad türetimi;
# değişirse ikisi birlikte değişir). Boş env = tam 16 sayfa, eski davranış.
_SECKI = ([int(x) for x in os.environ["PVQ_SAYFA_SECKISI"].split(",")]
          if os.environ.get("PVQ_SAYFA_SECKISI") else list(range(1, 17)))
_TAM = _SECKI == list(range(1, 17))
RAPOR_AD = ("PVQuant_Konya_GES_RAPOR_16sayfa" if _TAM
            else "PVQuant_Konya_GES_OZET_%dsayfa" % len(_SECKI))

files = sorted(glob.glob(f"{OUT}/PVQuant_Konya_GES_s??_*.html"))
files = [f for f in files
         if int(re.search(r"_s(\d\d)_", os.path.basename(f)).group(1)) in _SECKI]
assert len(files) == len(_SECKI), (len(files), _SECKI)


def bloklar(css):
    """CSS'i üst düzey bloklara ayırır (@media gibi iç içe yapıları korur)."""
    out, derinlik, bas = [], 0, 0
    for i, ch in enumerate(css):
        if ch == "{":
            derinlik += 1
        elif ch == "}":
            derinlik -= 1
            if derinlik == 0:
                out.append(css[bas:i + 1].strip())
                bas = i + 1
    return [b for b in out if b]


GLOBAL_SEC = {"*", "html", "body"}
fontlar, genel, kapsamli, govdeler = "", [], [], []

for n, path in enumerate(files, start=1):
    ham = open(path, encoding="utf-8").read()
    css = re.search(r"<style>(.*?)</style>", ham, re.S).group(1)
    govde = re.search(r"<body>(.*?)</body>", ham, re.S).group(1).strip()
    pid = "p%02d" % n

    for blok in bloklar(css):
        if blok.startswith("@font-face"):
            if n == 1:
                fontlar += blok
            continue
        if blok.startswith("@"):
            if n == 1:
                genel.append(blok)
            continue
        sec, govde_css = blok.split("{", 1)
        yeni = []
        for s in sec.split(","):
            s = s.strip()
            if not s:
                continue
            if s in GLOBAL_SEC:
                if n == 1:
                    genel.append("%s{%s" % (s, govde_css))
                continue
            if s.startswith(".page"):
                yeni.append("#%s%s" % (pid, s[len(".page"):]))
            else:
                yeni.append("#%s %s" % (pid, s))
        if yeni:
            kapsamli.append("%s{%s" % (",".join(yeni), govde_css))

    govde = govde.replace('<div class="page">', '<div class="page" id="%s">' % pid, 1)
    govdeler.append(govde)

HTML = ("<!doctype html>\n<html lang=\"tr\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<title>PVQuant — Konya GES · Üretim Tahmini ve Doğruluk Raporu</title>\n"
        "<style>\n%s\n%s\n%s\n</style>\n</head>\n<body>\n%s\n</body>\n</html>\n"
        % (fontlar, "\n".join(genel), "\n".join(kapsamli), "\n\n".join(govdeler)))

hedef = f"{OUT}/{RAPOR_AD}.html"
open(hedef, "w", encoding="utf-8").write(HTML)
print("yazıldı:", round(len(HTML) / 1024), "KB")

# v2.146: PDF, TEKIL sayfa PDF'lerinin birlesimidir. Birlesik HTML'i
# WeasyPrint'le yeniden basmak 16 sayfanin CSS'lerini ayni belgede
# CAKISTIRIYORDU (yalniz .page secicileri kimliklenir; h2/.fig/table gibi
# kurallar kureseldir, son gelen kazanir) — eski sabit-height bu bulasmayi
# sessizce KIRPARAK gizliyordu (s05/s08 altliklari aylardir murekkepte
# yoktu). Tekil render'lar dogru ve bekcili ("sayfa: 1"); teslim edilen
# PDF onlarin birlesimi olunca cakisma sinifi teslimatta kokten olur.
# Birlesik HTML onizleme/md5 icin uretilmeye devam eder.
from pypdf import PdfWriter
import glob as _g
parcalar = sorted(_g.glob(f"{OUT}/PVQuant_Konya_GES_s??_*.pdf"))
parcalar = [p for p in parcalar
            if int(re.search(r"_s(\d\d)_", os.path.basename(p)).group(1)) in _SECKI]
assert len(parcalar) == len(_SECKI), \
    f"{len(_SECKI)} tekil PDF bekleniyordu, {len(parcalar)} var"
w = PdfWriter()
for p in parcalar:
    w.append(p)
with open(f"{OUT}/{RAPOR_AD}.pdf", "wb") as f:
    w.write(f)
from pypdf import PdfReader
n = len(PdfReader(f"{OUT}/{RAPOR_AD}.pdf").pages)
print("PDF sayfa sayısı:", n)
assert n == len(_SECKI), "birlesik PDF %d sayfa degil" % len(_SECKI)
