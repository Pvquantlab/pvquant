"""v2.510 (04 #11) — Şeffaflık uç gövdeleri şemayla (swagger v1.15.8) uyumlu: uevcb-list {organizationId, startDate} (endDate yok);
organization-list {startDate, endDate}; uevcb-list-by-power-plant-id {powerPlantId, startDate}. Ağsız: httpx.MockTransport."""
import json

import httpx
import pytest

from pvquant.ext.turkiye import epias


def _istemci(kayit: list):
    def h(req: httpx.Request):
        if "cas/v1/tickets" in str(req.url):
            return httpx.Response(201, text="TGT-sahte")
        kayit.append((req.method, req.url.path, json.loads(req.content or b"null")))
        return httpx.Response(200, json={"items": [{"id": 1, "eic": "40X", "name": "UEVÇB-1"}]})
    return epias.Istemci(kullanici="u", sifre="p", transport=httpx.MockTransport(h))


def test_uevcb_listesi_govdesi_semaya_uygun():
    kayit = []; c = _istemci(kayit)
    assert c.uevcb_listesi(1234, "2026-10-01")[0]["eic"] == "40X"
    _, yol, govde = kayit[-1]
    assert yol.endswith("/v1/generation/data/uevcb-list")
    assert govde == {"startDate": "2026-10-01T00:00:00+03:00", "organizationId": 1234}       # endDate YOK, organizationId VAR


def test_uevcb_listesi_organizationid_zorunlu():
    c = _istemci([])
    with pytest.raises(ValueError, match="organizationId"):
        c.ham("uevcb_listesi", "2026-10-01", "2026-10-01")


def test_organizasyon_ve_santral_uclari():
    kayit = []; c = _istemci(kayit)
    c.organizasyon_listesi("2026-10-01", "2026-10-31")
    assert kayit[-1][1].endswith("/organization-list") and set(kayit[-1][2]) == {"startDate", "endDate"}
    c.uevcb_santraldan(15909, "2026-10-01")
    assert kayit[-1][1].endswith("/uevcb-list-by-power-plant-id") and kayit[-1][2] == {"startDate": "2026-10-01T00:00:00+03:00", "powerPlantId": 15909}
    c.ham("ptf", "2026-10-01", "2026-10-02")                                                 # diğer uçlarda endDate sürüyor
    assert "endDate" in kayit[-1][2]
