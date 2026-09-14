"""Cadastra os templates de referência (CARS, ATA, SNAP-IV) para uma
psicóloga já existente. Uso:

    python -m app.seed_templates psicologa@exemplo.com

Os arquivos-fonte ficam em app/rules_engine/fixtures/*.json e são a mesma
base usada nos testes automatizados (ver TEMPLATES_LAUDOS.md).

IMPORTANTE: o fixture da ATA (ata.json) está incompleto — o manual oficial
tem 22 itens e só 3 estão documentados em TEMPLATES_LAUDOS.md seção 3. A
psicóloga precisa revisar e completar antes de usar em produção.

IMPORTANTE: o fixture do Portage/IPO (portage.json) é só um EXEMPLO com 2
áreas e 2 faixas etárias cada, para mostrar o formato `age_brackets`
funcionando de ponta a ponta — não é o inventário oficial completo (~580
habilidades). Use a tela "Modelos de Laudo" (importação por IA) ou edite o
JSON diretamente para completar com os itens reais antes de uso clínico.
"""

import json
import sys
from pathlib import Path

from app.core.database import SessionLocal
from app.models.psychologist import Psychologist
from app.models.report_template import ReportTemplate
from app.schemas.report_template import ReportTemplateSchemaJSON

FIXTURES_DIR = Path(__file__).resolve().parent / "rules_engine" / "fixtures"
FIXTURES = ["cars.json", "ata.json", "snap_iv.json", "portage.json"]


def seed(owner_email: str) -> None:
    db = SessionLocal()
    try:
        owner = db.query(Psychologist).filter(Psychologist.email == owner_email).first()
        if owner is None:
            raise SystemExit(
                f"Nenhuma psicóloga cadastrada com o e-mail '{owner_email}'. "
                "Cadastre primeiro via POST /api/auth/register."
            )

        for fixture_name in FIXTURES:
            raw = json.loads((FIXTURES_DIR / fixture_name).read_text(encoding="utf-8"))
            schema = ReportTemplateSchemaJSON.model_validate(raw)

            existing = (
                db.query(ReportTemplate)
                .filter(ReportTemplate.owner_id == owner.id, ReportTemplate.name == schema.name)
                .first()
            )
            if existing is not None:
                print(f"- '{schema.name}' já existe para {owner_email}, pulando.")
                continue

            template = ReportTemplate(
                owner_id=owner.id,
                name=schema.name,
                version=1,
                schema_json=schema.model_dump(mode="json"),
            )
            db.add(template)
            print(f"+ '{schema.name}' cadastrado para {owner_email}.")

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Uso: python -m app.seed_templates <email-da-psicologa>")
    seed(sys.argv[1])
