"""FastAPI uygulamasının kök modülü.

Uygulamayı çalıştırmak için:

.. code:: bash

    uvicorn pvquant.api.main:app --reload

Swagger UI:   http://localhost:8000/docs
ReDoc:        http://localhost:8000/redoc
OpenAPI JSON: http://localhost:8000/openapi.json
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pvquant import __version__
from pvquant.api.routes import calibration, calibration_scada, forecast
from pvquant.config import get_settings


def create_app() -> FastAPI:
    """FastAPI uygulamasını yapılandırır ve döner.

    Factory pattern kullanılır → test izolasyonu kolaylaşır,
    farklı yapılandırmalarla birden fazla instance açılabilir.
    """
    settings = get_settings()

    app = FastAPI(
        title="PVQuant API",
        description=(
            "Saha-kalibre PV performans analitiği. "
            "Open-Meteo forecast verisinden 7 günlük üretim tahmini ve "
            "SCADA verisinden parametre kalibrasyonu sunar."
        ),
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS — frontend domain'lerinden gelen istekleri kabul et
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Route'ları kaydet
    app.include_router(forecast.router)
    app.include_router(calibration.router)
    app.include_router(calibration_scada.router)

    @app.get("/", tags=["health"])
    def root() -> dict[str, str]:
        """Basit healthcheck endpoint'i."""
        return {
            "name": "PVQuant API",
            "version": __version__,
            "status": "ok",
            "docs": "/docs",
        }

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        """Liveness/readiness probe için."""
        return {"status": "ok"}

    return app


# Uvicorn'un import edebilmesi için top-level instance
app = create_app()
