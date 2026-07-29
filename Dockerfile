# PVQuant worker imaji (v2.63) — GUN 0: compose servisi + restart policy zemini
# Tek imaj, tek is: apscheduler'li worker. Frontend bu imaja GIRMEZ
# (streamlit'siz kapanis v2.61 ile kanitli: pip install . yeterli).
FROM python:3.12-slim

# lightgbm calisma zamani OpenMP ister (libgomp1); gerisi wheel'le gelir
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# once metadata + kaynak, tek katman pip (proje kucuk, ayri katman oyunu gereksiz)
COPY pyproject.toml README.md ./
COPY src ./src
COPY apps ./apps
COPY alembic ./alembic
COPY alembic.ini ./

RUN pip install --no-cache-dir .

# varsayilan: surekli zamanlayici; tek tur icin: docker compose run --rm worker \
#   python -m apps.worker.main --once
CMD ["python", "-m", "apps.worker.main"]
