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
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não autenticado",
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
