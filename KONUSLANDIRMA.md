# PVQuant Konuşlandırma Notları (E.4 — v2.110)

## Düzen
- **Asıl çalışma ortamı: Docker compose yığını.** 8000'in sahibi compose api'sidir.
- Konteynerler: db (Timescale/pg16, YAŞAMALI), api (uvicorn :8000), worker (apscheduler),
  frontend (Streamlit, eski UI — bkz. Açık defter), caddy (80/443).
- Tek Postgres vardır: compose db'si `5432:5432` yayınlar; Mac'teki araçlar da ona bağlanır.
- SPA geliştirmede vite ile koşar (:5173) ve `VITE_API_URL=http://127.0.0.1:8000` üzerinden
  konteyner api'sine konuşur (`web/.env.local`, gitignore'da — yeni makinede elle).

## Ritüeller
- Yığın aç: `docker compose up -d api worker` (db bağımlılıkla kalkar; caddy/frontend gerekmedikçe kapalı kalabilir)
- Yığın kapat: `docker compose stop` (db'yi de durdurur; yalnız api/worker için: `docker compose stop api worker`)
- İmaj yenile (kod değişince): `docker compose build api worker && docker compose up -d api worker && until curl -sf http://127.0.0.1:8000/v1/healthz >/dev/null; do sleep 1; done`
- Açılış beklemesi (v2.154 — zincirlerde `up`'tan sonra, login/istek atmadan ÖNCE):
  `until curl -sf http://127.0.0.1:8000/v1/healthz >/dev/null; do sleep 1; done`
  Gerekçe: api hazır olmadan atılan login 401 yakar ve 5/dk sınırını tüketir
  (taze-kabuk dersi); Caddy üzerinden test için `curl -ksf https://localhost/v1/healthz`.
- Migration (elle ve bilinçli — otomatik açılış-migration YOK):
  `docker compose run --rm api alembic upgrade head`
  Durum bakışı: `docker compose run --rm --entrypoint "" api alembic current`
- Konteyner-içi rapor kalkanı (imaj değişince):
  `docker compose run --rm --no-deps --entrypoint "" api sh -c 'cd /app/reporting/html && python3 uret.py'`
  → 16 sayfa + kanonik md5 ada7b10b4b328f5dfb8cd7197d4f2d8d beklenir.
  (v2.153'te yenilendi — s08 kural 3/5 gerçeğe çekildi + s01 "Metrik
  penceresi" etiketi; önceki f0dbc1401d9674858dd39ba6ca22310c, v2.146–v2.152.)

## İmaj içeriği (v2.109+)
- Dockerfile: src, apps, alembic, **reporting**, **scripts**; WeasyPrint sistem kütüphaneleri
  (pango/cairo/gdk-pixbuf/libffi8/shared-mime-info/fonts-dejavu-core); `ENV PYTHONUNBUFFERED=1`.
- pyproject: `weasyprint>=61` bağımlılık (CI da kurar).
- `.dockerignore`'dan `scripts` çıkarıldı (seed konteynerde kullanılabilir).

## Kararlar (E.4)
- Migration elle koşulur; şema değişikliği bilinçli adımdır (teşhis-önce).
- Frontend dar kapsam: Streamlit imajı yerinde bırakıldı; SPA konteynerizasyonu
  (çok aşamalı build + Caddy statik servis) açık defterde.
- restart: unless-stopped kalır — asıl ortam compose olduğu için diriliş artık istenen davranıştır.

## Açık defter (E.4 sonrası)
- dev.sh uvicorn'u 8010'a taşınmalı (compose ile çakışmasın); api sabrı 2sn→5sn; 5432 yoklaması lsof'a.
- SPA konteynerizasyonu + Caddyfile güncellemesi (frontend:8501 → statik SPA).
- Sunucuya taşıma: .env (DB_PASSWORD, PVQ_JWT_SECRET, PVQ_DOMAIN) doldurulmadan yayına çıkılmaz.
