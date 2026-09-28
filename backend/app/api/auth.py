from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_psychologist
from app.core.database import get_db
from app.core.rate_limit import esta_bloqueado, limpar_falhas, registrar_falha
from app.core.security import create_access_token, hash_password, verify_password
from app.models.psychologist import Psychologist
from app.schemas.auth import (
    PsychologistLogin,
    PsychologistOut,
    PsychologistProfileUpdate,
    PsychologistRegister,
    Token,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=PsychologistOut, status_code=status.HTTP_201_CREATED)
def register(data: PsychologistRegister, db: Session = Depends(get_db)) -> Psychologist:
    existing = db.query(Psychologist).filter(Psychologist.email == data.email).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="E-mail já cadastrado")

    psychologist = Psychologist(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
    )
    db.add(psychologist)
    db.commit()
    db.refresh(psychologist)
    return psychologist


@router.post("/login", response_model=Token)
def login(data: PsychologistLogin, db: Session = Depends(get_db)) -> Token:
    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha inválidos"
    )

    if esta_bloqueado(data.email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Muitas tentativas de login com este e-mail. Aguarde alguns minutos antes de "
                "tentar novamente."
            ),
        )

    psychologist = db.query(Psychologist).filter(Psychologist.email == data.email).first()
    if psychologist is None or not verify_password(data.password, psychologist.password_hash):
        registrar_falha(data.email)
        raise invalid_credentials

    limpar_falhas(data.email)
    return Token(access_token=create_access_token(psychologist.id))


@router.get("/me", response_model=PsychologistOut)
def me(current: Psychologist = Depends(get_current_psychologist)) -> Psychologist:
    return current


@router.put("/me", response_model=PsychologistOut)
def update_me(
    data: PsychologistProfileUpdate,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> Psychologist:
    """Atualiza dados do próprio perfil: registro profissional (ex.: CRP),
    bio exibida no bloco "Sobre A Profissional Responsável" e as linhas de
    credencial da assinatura — todos usados na geração do laudo."""
    current.professional_registration = data.professional_registration
    current.bio_profissional = data.bio_profissional
    current.credenciais_assinatura = data.credenciais_assinatura
    db.commit()
    db.refresh(current)
    return current
