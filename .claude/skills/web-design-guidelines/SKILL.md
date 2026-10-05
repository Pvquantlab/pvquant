---
name: web-design-guidelines
description: Use after producing or changing any UI code — reviews it against Vercel Web Interface Guidelines (accessibility, interaction, animation/reduced-motion, layout/optical alignment, forms, performance). This is an AUDIT skill: it rejects, it does not style.
---

# Web Design Guidelines (denetim kapısı)

Kaynak: vercel-labs/web-interface-guidelines (05.10.2026 kopyası, bu klasörde).

UI kodu üretildikten/değiştirildikten SONRA çağrılır; stil ÖNERMEZ, eler.

1. Kuralların tamamı: [AGENTS.md](AGENTS.md) — erişilebilirlik, odak, klavye,
   animasyon (prefers-reduced-motion, kesilebilirlik), layout/optik hizalama, form,
   performans, içerik dili.
2. İnceleme talimatı ve çıktı biçimi: [command.md](command.md) — dosya listesi verilir,
   ihlaller `dosya:satır — kural — düzeltme` biçiminde kısa raporlanır.
3. PVQuant istisnaları: proje kuralları (pvquant-tasarim skill'i + test pinleri) bu
   listeyle çatışırsa PROJE kazanır ve istisna gerekçesiyle not edilir
   (ör. Rozet.tsx satır içi stil istisnası — BENIOKU §6.3).

Güncelleme: bu kopya el ile tazelenir (curl, aynı iki dosya); sürüm notu buraya işlenir.
