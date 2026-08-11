# PVQuant worker imaji (v2.63) — GUN 0: compose servisi + restart policy zemini
# Tek imaj, tek is: apscheduler'li worker. Frontend bu imaja GIRMEZ
# (streamlit'siz kapanis v2.61 ile kanitli: pip install . yeterli).
FROM python:3.12-slim

# lightgbm calisma zamani OpenMP ister (libgomp1); gerisi wheel'le gelir
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libcairo2 \
    libffi8 shared-mime-info fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# v2.113: bagimliliklar KAYNAKTAN ONCE ayri katmanda — src degisince ~2 dk pip
# tekrari biter (v2.63'un 'ayri katman gereksiz' karari WeasyPrint+lightgbm
# yigini buyuyunce gecersizlesti). pyproject degismedikce bu katman onbellekten.
COPY pyproject.toml README.md ./
RUN python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print('\n'.join(d['project']['dependencies']))" > /tmp/reqs.txt \
    && pip install --no-cache-dir -r /tmp/reqs.txt
COPY src ./src
COPY apps ./apps
COPY alembic ./alembic
COPY alembic.ini ./
COPY reporting ./reporting
COPY scripts ./scripts

RUN pip install --no-cache-dir --no-deps .

# varsayilan: surekli zamanlayici; tek tur icin: docker compose run --rm worker \
#   python -m apps.worker.main --once
CMD ["python", "-m", "apps.worker.main"]
