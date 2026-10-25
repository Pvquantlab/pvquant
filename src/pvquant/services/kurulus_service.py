"""26.10 Faz 6 — KURULUŞ AYARLARI (kiracı yöneticisi): şimdilik tek politika, «yöneticiler için 2FA zorunlu». Kiracı kimliği jetondan gelir;
yazım sistem bağlamında ama WHERE id = kiracı. Politika açılınca auth_service oturum önbelleği düşer: 2FA'sız yönetici bir sonraki istekte
kurulum ekranına iner (deps.MUSTERI_KURULUM_YOLLARI)."""
from __future__ import annotations

from sqlalchemy import text

from pvquant.db import sistem_baglami
from pvquant.services import auth_service


def ayarlar(tenant_id) -> dict:
    with sistem_baglami() as s:
        r = s.execute(text("SELECT yonetici_2fa_zorunlu, "
                           "(SELECT count(*) FROM users u WHERE u.tenant_id = t.id AND u.role = 'admin' AND u.aktif AND NOT u.totp_aktif) AS iki_adimsiz_yonetici "
                           "FROM tenants t WHERE t.id = CAST(:t AS uuid)"), {"t": str(tenant_id)}).first()
    return {"yonetici_2fa_zorunlu": bool(r.yonetici_2fa_zorunlu), "iki_adimsiz_yonetici": int(r.iki_adimsiz_yonetici)} if r else {"yonetici_2fa_zorunlu": False, "iki_adimsiz_yonetici": 0}


def ayar_guncelle(tenant_id, *, yonetici_2fa_zorunlu: bool) -> dict:
    with sistem_baglami() as s:
        s.execute(text("UPDATE tenants SET yonetici_2fa_zorunlu = :v, updated_at = now() WHERE id = CAST(:t AS uuid)"),
                  {"v": bool(yonetici_2fa_zorunlu), "t": str(tenant_id)})
    auth_service.oturum_onbellegi_dusur()
    return ayarlar(tenant_id)
