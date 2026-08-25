# PVQuant Go-Live Günlük Raporu

_Zeyilname v2.25 mühürlü format — 5 gün yeşil = MVP sprint fiilen kapanır._

## Format (Fable 5 v2.25)

Her sabah 09:00'dan önce, ~10 dakikada 5 kontrol → tek satır ekle:

    GÜN N | jobs: 4/4 ok | smoke: yeşil | yedek: X,XMB | sentry: 0 | pürüz: —

**5 kontrol (sırasıyla):**

1. **Gece fotoğrafı** — jobs_log 24 saatlik özet, 4 iş sıfır error
2. **Smoke** — PYTHONPATH=src python scripts/smoke.py; echo exit=$? → 8/8 + exit=0 (v2.160: eski adım-8/ui_kit gömüldü)
3. **Yedek log/boyut** — cron koştu mu (elle koşma, denetle)
4. **Sentry inbox** = 0
5. **alerts yeni satır** — varsa meşru mu

## İlk kırmızıda protokol

Panik-düzeltme YOK →
1. Önce teşhis (jobs_log.detail + Sentry trace)
2. Mini-commit
3. Smoke yeniden
4. Günlüğe sebep+çözüm satırı

Aynı gün kapanmayan pürüz: tarih ve etki notuyla pürüz listesine.

## Pilot görünürlüğü

GÜN 0-5 senin gözetim haftandır. Pilot yok — pilot imzalanınca El Kitabı'nın 5-günlük onboarding senaryosu ayrıca ve o zaman koşar.

Pilot hiçbir zaman görmez: smoke tenant'ı, jobs_log, Sentry, günlük.
Pilot yalnız kendi tenant'ını görür — RLS'in üç aydır taşıdığı söz.

---

## GÜN 0 — Kurulum

**Tarih:** YYYY-MM-DD
**Sunucu:** (VM adı/IP)

**9 madde kontrol listesi (Zeyilname v2.25 S1):**

- [ ] 1. Sunucu + .env (git'e girmez)
- [ ] 2. Sırlar (JWT + DB), grep dev-secret = 0
- [ ] 3. pvq_app_login rol geçişi, rolbypassrls = f
- [ ] 4. Sentry DSN, panel event kanıtı
- [ ] 5. SMTP beşlisi, test alarmı kutuya düştü
- [ ] 6. KVKK parantezleri = 0 + hukuk onayı
- [ ] 7. Yedek cron + üç-sayı prod tatbikatı
- [ ] 8. TLS, curl -I 308
- [ ] 9. Prod smoke, 8/8 + exit=0 → GO-LIVE BELGESİ

---

## Günlük Kayıtlar

| GÜN | jobs | smoke | yedek | sentry | pürüz |
|-----|------|-------|-------|--------|-------|
| 1 |      |       |       |        |       |
| 2 |      |       |       |        |       |
| 3 |      |       |       |        |       |
| 4 |      |       |       |        |       |
| 5 |      |       |       |        |       |

---

## Pürüz Listesi

| Tarih | Pürüz | Etki | Durum |
|-------|-------|------|-------|
|       |       |      |       |

---

## 5 Sabah Yeşil = MVP Kapanır

Zeyilname v2.25: "P4-D'nin kabulü kod değil, beş günlük yeşil günlüktür."

5 satır dolduğunda + hepsi yeşil → go-live imzalı, pilot çağrısı başlar.
