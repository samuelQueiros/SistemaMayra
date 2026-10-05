from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_psychologist
from app.core.config import settings
from app.core.database import get_db
from app.core.security import decrypt_secret, encrypt_secret
from app.models.ai_settings import AISettings
from app.models.psychologist import Psychologist
from app.schemas.ai_settings import AISettingsOut, AISettingsUpdate, ProvedorOut
from app.services.ai.provedores import PROVEDORES

router = APIRouter(prefix="/api/settings/ai", tags=["ai-settings"])


def _mask(api_key: str) -> str:
    if len(api_key) <= 4:
        return "*" * len(api_key)
    return f"{'*' * 6}{api_key[-4:]}"


@router.get("/provedores", response_model=list[ProvedorOut])
def listar_provedores(_: Psychologist = Depends(get_current_psychologist)) -> list[ProvedorOut]:
    """Provedores aceitos, com modelos sugeridos e como cada um lê os PDFs
    do Relatório Por IA (ver services/ai/provedores.py)."""
    return [
        ProvedorOut(
            id=p.id,
            nome=p.nome,
            leitura_pdf=p.leitura_pdf,
            modelos=p.modelos,
            link_chave=p.link_chave,
            observacao=p.observacao,
        )
        for p in PROVEDORES.values()
    ]


@router.get("", response_model=AISettingsOut)
def get_ai_settings(
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> AISettingsOut:
    row = db.query(AISettings).filter(AISettings.owner_id == current.id).first()
    if row is None:
        # Sem configuração própria ainda: mostra o padrão do servidor (se
        # houver) só como referência, mas deixa claro que não está pronta.
        tem_chave_no_servidor = bool(
            settings.anthropic_api_key if settings.ai_provider == "anthropic" else settings.openai_api_key
        )
        return AISettingsOut(
            provider=settings.ai_provider,
            model=settings.ai_model,
            api_key_configured=tem_chave_no_servidor,
            api_key_preview="(chave padrão do servidor)" if tem_chave_no_servidor else None,
        )
    return AISettingsOut(
        provider=row.provider,
        model=row.model,
        api_key_configured=True,
        api_key_preview=_mask(decrypt_secret(row.api_key)),
    )


@router.put("", response_model=AISettingsOut)
def update_ai_settings(
    data: AISettingsUpdate,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> AISettingsOut:
    api_key_criptografada = encrypt_secret(data.api_key)
    row = db.query(AISettings).filter(AISettings.owner_id == current.id).first()
    if row is None:
        row = AISettings(owner_id=current.id, provider=data.provider, model=data.model, api_key=api_key_criptografada)
        db.add(row)
    else:
        row.provider = data.provider
        row.model = data.model
        row.api_key = api_key_criptografada
    db.commit()
    db.refresh(row)
    return AISettingsOut(
        provider=row.provider,
        model=row.model,
        api_key_configured=True,
        api_key_preview=_mask(data.api_key),
    )
