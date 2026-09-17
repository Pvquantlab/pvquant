"""v2335_parola_sifirlama

Revision ID: v2335_parola_sifirlama
Revises: v2328_vitrin_basvuru
Create Date: 2026-09-17

v2.335 — "şifremi unuttum" akışı: tek kullanımlık, kısa ömürlü sıfırlama
jetonları. Jetonun kendisi SAKLANMAZ (API anahtarı kalıbı): yalnız SHA-256
özeti yazılır — tablo sızsa bile bağlantılar kullanılamaz. Kiracı tablosu
değil: kullanıcı e-postası küresel benzersiz (users_email_key) ve akış
oturum açılmadan koşar; erişim yalnız sistem bağlamından.
"""
from alembic import op

revision = "v2335_parola_sifirlama"
down_revision = "v2328_vitrin_basvuru"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE parola_sifirlama(
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      token_hash TEXT NOT NULL UNIQUE,
      expires_at TIMESTAMPTZ NOT NULL,
      used_at TIMESTAMPTZ,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now());
    GRANT SELECT, INSERT, UPDATE, DELETE ON parola_sifirlama TO pvq_app;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE parola_sifirlama")
