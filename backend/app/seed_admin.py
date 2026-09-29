"""Garante que exista a conta de psicóloga definida pelas variáveis de
ambiente ADMIN_EMAIL / ADMIN_PASSWORD (e, opcionalmente, ADMIN_NAME).
Roda sozinho a cada start do container (ver CMD do Dockerfile), depois das
migrations. Uso manual:

    python -m app.seed_admin

- Sem ADMIN_EMAIL ou ADMIN_PASSWORD definidos, não faz nada.
- Se a conta ainda não existe, é criada.
- Se já existe, a senha é atualizada caso seja diferente da variável — ou
  seja, a variável é a fonte da verdade: trocar ADMIN_PASSWORD e reiniciar
  o container redefine a senha.
"""

from sqlalchemy.orm import Session

from app import models  # noqa: F401 -- garante que todos os modelos sejam registrados no ORM
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password, verify_password
from app.models.psychologist import Psychologist

NOME_PADRAO = "Administrador"


def garantir_admin(db: Session, email: str, password: str, name: str | None = None) -> str:
    """Cria ou atualiza a conta. Retorna "criada", "senha atualizada" ou
    "sem alterações"."""
    if not 8 <= len(password) <= 72:
        raise ValueError("ADMIN_PASSWORD precisa ter entre 8 e 72 caracteres")

    email = email.strip()
    psychologist = db.query(Psychologist).filter(Psychologist.email == email).first()

    if psychologist is None:
        db.add(
            Psychologist(
                name=(name or "").strip() or NOME_PADRAO,
                email=email,
                password_hash=hash_password(password),
            )
        )
        db.commit()
        return "criada"

    if not verify_password(password, psychologist.password_hash):
        psychologist.password_hash = hash_password(password)
        db.commit()
        return "senha atualizada"

    return "sem alterações"


def main() -> None:
    if not settings.admin_email or not settings.admin_password:
        print("seed_admin: ADMIN_EMAIL/ADMIN_PASSWORD não definidos, nada a fazer.")
        return

    db = SessionLocal()
    try:
        resultado = garantir_admin(db, settings.admin_email, settings.admin_password, settings.admin_name)
    finally:
        db.close()
    print(f"seed_admin: conta {settings.admin_email.strip()} — {resultado}.")


if __name__ == "__main__":
    main()
