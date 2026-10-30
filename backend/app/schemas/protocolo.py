"""Modelos de protocolo configuráveis pela psicóloga (Configurações →
"Modelos De Protocolo"). Guardados em `ReportTemplate.schema_json` com
`rule_type: "protocolo"` — formato próprio, independente do `schema_json`
antigo de escalas (`schemas/report_template.py`). O formulário e o texto do
relatório são montados no navegador (`frontend/src/laudo/`); o backend só
valida o modelo, guarda e gera PDF/Word a partir do HTML pronto."""

import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

TipoPergunta = Literal["texto_curto", "texto_longo", "sim_nao", "multipla_escolha", "caixas", "data", "numero"]
TipoSecao = Literal["perguntas", "escala", "fotos", "texto"]
FormatoRelatorio = Literal["lista", "tabela", "so_texto"]

_ID = r"^[a-z0-9_]{1,40}$"
# {q:id} no texto padrão — resposta de uma pergunta do próprio modelo.
_VARIAVEL_PERGUNTA = re.compile(r"\{q:([^}]+)\}")


class OpcaoPergunta(BaseModel):
    rotulo: str = Field(min_length=1, max_length=200)
    # Trecho que entra no relatório quando esta opção é escolhida.
    texto_relatorio: str | None = Field(default=None, max_length=4000)


class Pergunta(BaseModel):
    id: str = Field(pattern=_ID)
    rotulo: str = Field(min_length=1, max_length=500)
    tipo: TipoPergunta
    ajuda: str | None = Field(default=None, max_length=1000)
    opcoes: list[OpcaoPergunta] | None = None
    obrigatoria: bool = False
    # sim_nao: mostra um campo "Descreva" quando a resposta é Sim.
    detalhar_quando_sim: bool = False

    @model_validator(mode="after")
    def opcoes_por_tipo(self) -> "Pergunta":
        if self.tipo in ("multipla_escolha", "caixas") and not self.opcoes:
            raise ValueError(f"Pergunta '{self.rotulo}': informe as opções de resposta.")
        if self.opcoes:
            rotulos = [o.rotulo.strip().lower() for o in self.opcoes]
            if len(rotulos) != len(set(rotulos)):
                raise ValueError(f"Pergunta '{self.rotulo}': há opções repetidas.")
        return self


class ItemEscala(BaseModel):
    id: str = Field(pattern=_ID)
    rotulo: str = Field(min_length=1, max_length=500)


class OpcaoEscala(BaseModel):
    rotulo: str = Field(min_length=1, max_length=100)
    valor: float


class FaixaEscala(BaseModel):
    min: float
    max: float
    rotulo: str = Field(min_length=1, max_length=200)
    texto_relatorio: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def ordem(self) -> "FaixaEscala":
        if self.max < self.min:
            raise ValueError(f"Faixa '{self.rotulo}': o máximo precisa ser maior ou igual ao mínimo.")
        return self


class Escala(BaseModel):
    itens: list[ItemEscala] = Field(min_length=1)
    opcoes: list[OpcaoEscala] = Field(min_length=2)
    faixas: list[FaixaEscala] = Field(default_factory=list)
    grafico: Literal["barras", "nenhum"] = "barras"

    @model_validator(mode="after")
    def faixas_sem_sobreposicao(self) -> "Escala":
        ordenadas = sorted(self.faixas, key=lambda f: f.min)
        for anterior, atual in zip(ordenadas, ordenadas[1:]):
            if atual.min <= anterior.max:
                raise ValueError(f"As faixas '{anterior.rotulo}' e '{atual.rotulo}' se sobrepõem.")
        return self


class RelatorioDaSecao(BaseModel):
    mostrar: bool = True
    formato: FormatoRelatorio = "lista"
    texto_padrao: str | None = Field(default=None, max_length=20000)


class Secao(BaseModel):
    id: str = Field(pattern=_ID)
    titulo: str = Field(min_length=1, max_length=200)
    tipo: TipoSecao = "perguntas"
    ajuda: str | None = Field(default=None, max_length=2000)
    perguntas: list[Pergunta] | None = None
    escala: Escala | None = None
    relatorio: RelatorioDaSecao = Field(default_factory=RelatorioDaSecao)

    @model_validator(mode="after")
    def conteudo_por_tipo(self) -> "Secao":
        if self.tipo == "perguntas" and not self.perguntas:
            raise ValueError(f"Seção '{self.titulo}': adicione pelo menos uma pergunta.")
        if self.tipo == "escala" and self.escala is None:
            raise ValueError(f"Seção '{self.titulo}': configure a escala.")
        return self


class ProtocoloSchemaJSON(BaseModel):
    rule_type: Literal["protocolo"] = "protocolo"
    name: str = Field(min_length=1, max_length=255)
    descricao: str | None = Field(default=None, max_length=2000)
    titulo_relatorio: str = Field(default="RELATÓRIO", min_length=1, max_length=300)
    secoes: list[Secao] = Field(min_length=1)

    @model_validator(mode="after")
    def ids_e_variaveis(self) -> "ProtocoloSchemaJSON":
        ids_secao = [s.id for s in self.secoes]
        if len(ids_secao) != len(set(ids_secao)):
            raise ValueError("Há seções com o mesmo identificador.")
        ids_pergunta: list[str] = []
        for secao in self.secoes:
            ids_pergunta += [p.id for p in secao.perguntas or []]
            if secao.escala:
                itens = [i.id for i in secao.escala.itens]
                if len(itens) != len(set(itens)):
                    raise ValueError(f"Seção '{secao.titulo}': há itens da escala repetidos.")
        if len(ids_pergunta) != len(set(ids_pergunta)):
            raise ValueError("Há perguntas com o mesmo identificador.")
        existentes = set(ids_pergunta)
        for secao in self.secoes:
            for ref in _VARIAVEL_PERGUNTA.findall(secao.relatorio.texto_padrao or ""):
                if ref not in existentes:
                    raise ValueError(
                        f"Seção '{secao.titulo}': o texto do relatório usa {{q:{ref}}}, "
                        "mas essa pergunta não existe no modelo."
                    )
        return self


class ProtocoloIn(BaseModel):
    schema_json: ProtocoloSchemaJSON


class ProtocoloOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    version: int
    schema_json: dict
    arquivado: bool
    created_at: datetime
