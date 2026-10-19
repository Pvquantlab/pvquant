# Süreç denetimi (bağımsız doğrulama) — yeniden üretilebilir kontroller.
# Kullanım (depo kökünden): python3 -I perf/dogrulama/surec-denetimi.py
# 1) Temel matrisin iki sürümü (49d8f2b'deki ilk ölçüm ↔ HEAD'de yeniden ölçülen) ve «sonra» matrisleri:
#    soğuk TTFB / FCP medyanı, motor × kısıtlı ağ. TTFB ön yüz kodundan bağımsızdır; oturumlar arası fark düzenek kaynaklıdır.
# 2) web/src/features/vitrin/varlik/* — d6ab50a ↔ HEAD sha256.
import hashlib, json, statistics as st, subprocess, sys

def git(*a, ikili=False):
    return subprocess.run(["git", *a], check=True, capture_output=True, text=not ikili).stdout

def satirlar(ref, yol):
    return [json.loads(l) for l in git("show", f"{ref}:{yol}").splitlines() if l.strip()]

kaynaklar = [
    ("once @49d8f2b (12:10-14:04Z)", satirlar("49d8f2b", "perf/baseline/matris.jsonl")),
    ("once @HEAD (kisitli satirlar 20:34-21:23Z)", satirlar("HEAD", "perf/baseline/matris.jsonl")),
    ("ara-sonra1 (16:37-17:31Z)", satirlar("HEAD", "perf/analiz/ara-sonra1/matris.jsonl")),
    ("sonra @HEAD (ch/wk 17:38-18:31Z)", satirlar("HEAD", "perf/after/matris.jsonl")),
]
print("== Soğuk TTFB medyanı (ms)")
for ad, rows in kaynaklar:
    h = []
    for m in ("chromium", "firefox", "webkit"):
        for ag in ("hizli3g", "yavas4g"):
            v = [r["soguk"]["ttfb"] for r in rows if r["motor"] == m and r["ag"] == ag and r["soguk"].get("ttfb") is not None]
            h.append(f"{m[:2]}-{ag}={st.median(v):.0f}")
    print(f"  {ad:44s} " + " ".join(h))

print("== Chromium soğuk FCP medyanı (ms): once@49d8f2b | once@HEAD | sonra")
def med(rows, anahtar):
    d = {}
    for r in rows:
        v = r["soguk"].get(anahtar)
        if v is not None:
            d.setdefault((r["sayfa"], r["ag"], r["motor"], r["gorunum"]), []).append(v)
    return {k: st.median(v) for k, v in d.items()}
b0, b1, a = (med(kaynaklar[i][1], "fcp") for i in (0, 1, 3))
for s in ("ana", "yontem"):
    for ag in ("hizli3g", "yavas4g"):
        for g in ("390x844", "768x1024", "1440x900", "1920x1080"):
            k = (s, ag, "chromium", g)
            print(f"  {s:6s} {ag:7s} {g:9s} {b0[k]:6.0f} | {b1[k]:6.0f} | {a[k]:6.0f}")

print("== Medya sha256: d6ab50a ↔ HEAD (web/src/features/vitrin/varlik)")
dosyalar = git("ls-tree", "-r", "--name-only", "d6ab50a", "--", "web/src/features/vitrin/varlik").split()
farkli = 0
for f in dosyalar:
    h0 = hashlib.sha256(git("show", f"d6ab50a:{f}", ikili=True)).hexdigest()
    h1 = hashlib.sha256(git("show", f"HEAD:{f}", ikili=True)).hexdigest()
    farkli += h0 != h1
print(f"  {len(dosyalar)} dosya, farklı: {farkli}")
sys.exit(0)
