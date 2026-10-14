import mimetypes
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_psychologist
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import MAX_TENTATIVAS_POR_IP, esta_bloqueado, limpar_falhas, registrar_falha
from app.core.security import create_access_token, hash_password, verify_password
from app.models.psychologist import Psychologist
from app.schemas.auth import (
    CapaConfig,
    PsychologistLogin,
    PsychologistOut,
    PsychologistProfileUpdate,
    PsychologistRegister,
    Token,
)
from app.services.storage import get_covers_storage

router = APIRouter(prefix="/api/auth", tags=["auth"])

_HASH_FICTICIO = hash_password("senha-ficticia-so-para-igualar-o-tempo")
_EXTENSOES_CAPA = {".jpg", ".jpeg", ".png", ".webp"}
_TAMANHO_MAXIMO_CAPA = 10 * 1024 * 1024


@router.post("/register", response_model=PsychologistOut, status_code=status.HTTP_201_CREATED)
def register(data: PsychologistRegister, db: Session = Depends(get_db)) -> Psychologist:
    if not settings.cadastro_publico:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="O cadastro de novas contas está desativado. Fale com o administrador do sistema.",
        )
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
def login(data: PsychologistLogin, request: Request, db: Session = Depends(get_db)) -> Token:
    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha inválidos"
    )
    # IP real do cliente (o uvicorn roda com --proxy-headers atrás do Caddy).
    chave_ip = f"ip:{request.client.host if request.client else 'desconhecido'}"

    if esta_bloqueado(chave_ip, MAX_TENTATIVAS_POR_IP):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login a partir desta rede. Aguarde alguns minutos antes de tentar novamente.",
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
    # Com e-mail inexistente também roda o bcrypt (hash fictício): o tempo de
    # resposta não revela quais e-mails têm conta.
    hash_conferido = psychologist.password_hash if psychologist else _HASH_FICTICIO
    senha_ok = verify_password(data.password, hash_conferido)
    if psychologist is None or not senha_ok:
        registrar_falha(data.email)
        registrar_falha(chave_ip)
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


@router.put("/me/capa", response_model=PsychologistOut)
def upload_capa(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> Psychologist:
    """Capa padrão dos relatórios, enviada pela própria psicóloga. Substitui
    a anterior (se houver); o nome do paciente é escrito por cima pelo
    formulário, conforme `capa_config`."""
    extensao = Path(file.filename or "").suffix.lower()
    if extensao not in _EXTENSOES_CAPA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato de imagem não suportado: '{file.filename}'. Envie JPG, PNG ou WEBP.",
        )
    conteudo = file.file.read(_TAMANHO_MAXIMO_CAPA + 1)
    if len(conteudo) > _TAMANHO_MAXIMO_CAPA:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="A imagem da capa passa de 10 MB. Exporte em tamanho A4 (2480×3508) e tente de novo.",
        )

    storage = get_covers_storage()
    anterior = current.capa_arquivo
    chave = f"{current.id}/{uuid.uuid4()}{extensao}"
    storage.save(chave, conteudo)
    current.capa_arquivo = chave
    db.commit()
    if anterior:
        storage.delete(anterior)
    db.refresh(current)
    return current


@router.get("/me/capa/arquivo")
def download_capa(current: Psychologist = Depends(get_current_psychologist)) -> Response:
    if not current.capa_arquivo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma capa personalizada enviada")
    conteudo = get_covers_storage().read(current.capa_arquivo)
    tipo_mime = mimetypes.guess_type(current.capa_arquivo)[0] or "application/octet-stream"
    return Response(content=conteudo, media_type=tipo_mime, headers={"Cache-Control": "no-store"})


@router.delete("/me/capa", response_model=PsychologistOut)
def delete_capa(
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> Psychologist:
    """Volta para a capa padrão do sistema (capa-relatorio.jpg)."""
    anterior = current.capa_arquivo
    current.capa_arquivo = None
    current.capa_config = None
    db.commit()
    if anterior:
        get_covers_storage().delete(anterior)
    db.refresh(current)
    return current


@router.put("/me/capa/config", response_model=PsychologistOut)
def update_capa_config(
    data: CapaConfig,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> Psychologist:
    current.capa_config = data.model_dump()
    db.commit()
    db.refresh(current)
    return current
