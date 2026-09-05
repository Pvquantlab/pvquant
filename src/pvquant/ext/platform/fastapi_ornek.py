"""FastAPI'ye bağlama örneği (çalıştırmak için `pip install fastapi`; paket buna bağımlı değildir).

    from fastapi import FastAPI, Depends, Header, HTTPException, Response
    from pvquant.ext.platform import api_anahtar, tazeleme

    app = FastAPI(); depo = api_anahtar.Depo(); kova = api_anahtar.TokenBucket(120, 2.0); damga = tazeleme.DegisimDamgasi()

    def anahtar_dep(x_api_key: str = Header(...)):
        try:
            k = api_anahtar.dogrula(depo, x_api_key, "tahmin:oku"); api_anahtar.oran_siniri(k, kova); return k
        except PermissionError: raise HTTPException(401)
        except RuntimeError: raise HTTPException(429)

    @app.get("/v1/dis/santral/{plant_id}/tahmin")
    def tahmin(plant_id: str, response: Response, if_none_match: str | None = Header(None), k=Depends(anahtar_dep)):
        kod, basliklar, govde = tazeleme.kosullu_yanit(damga, f"tahmin:{plant_id}", if_none_match, lambda: {"plant": plant_id, "seri": []})
        response.headers.update(basliklar); response.status_code = kod
        return govde if kod == 200 else Response(status_code=304, headers=basliklar)
"""
