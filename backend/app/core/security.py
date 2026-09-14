import base64
import hashlib
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from uuid import UUID

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(psychologist_id: UUID) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expires_minutes)
    payload = {"sub": str(psychologist_id), "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> UUID | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    subject = payload.get("sub")
    if subject is None:
        return None
    try:
        return UUID(subject)
    except ValueError:
        return None


@lru_cache
def _fernet() -> Fernet:
    """Chave de criptografia simétrica para segredos guardados no banco
    (hoje: a chave de IA de cada psicóloga, tabela `ai_settings`).
    Derivada do JWT_SECRET via SHA-256 em vez de reaproveitá-lo
    diretamente — separa criptograficamente as duas finalidades sem
    exigir uma variável de ambiente nova obrigatória."""
    chave_derivada = hashlib.sha256(settings.jwt_secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(chave_derivada))


def encrypt_secret(valor: str) -> str:
    return _fernet().encrypt(valor.encode("utf-8")).decode("utf-8")


def decrypt_secret(valor: str) -> str:
    """Descriptografa um segredo salvo com `encrypt_secret`. Se `valor`
    não for um token Fernet válido (ex.: chave salva em texto puro antes
    desta funcionalidade existir), devolve o valor original — a próxima
    vez que a psicóloga salvar a chave, ela já é recriptografada."""
    try:
        return _fernet().decrypt(valor.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return valor
