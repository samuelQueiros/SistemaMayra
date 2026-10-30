"""Dependências compartilhadas das rotas. `get_current_psychologist` é o que exige login: toda rota
com dados de paciente depende dela e filtra por `owner_id` (docs/ARQUITETURA.md)."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.psychologist import Psychologist

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_psychologist(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Psychologist:
    """Psicóloga dona do token `Authorization: Bearer`. Token ausente, inválido, vencido ou de conta
    apagada responde 401 com a mesma mensagem, sem dizer qual foi o motivo."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sua sessão expirou. Entre novamente para continuar.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    psychologist_id = decode_access_token(credentials.credentials)
    if psychologist_id is None:
        raise unauthorized

    psychologist = db.get(Psychologist, psychologist_id)
    if psychologist is None:
        raise unauthorized

    return psychologist
