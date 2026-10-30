"""Laudo Por IA: catálogo do protocolo fixo e validação da resposta da IA.

O catálogo vem do próprio formulário (`catalogoParaIA()` em
frontend/public/formulario-novo-paciente.html): a lista de campos que a IA
pode preencher, com tipo e opções. Assim o formulário continua sendo a única
fonte da verdade (itens da CARS, ATA, SNAP-IV, Portage da faixa etária...).
Aqui o catálogo vira texto para o prompt e serve de régua para descartar
qualquer campo ou valor que a IA invente."""

import re
import time
from dataclasses import dataclass, field
from functools import partial
from typing import Literal

from pydantic import BaseModel, Field

from app.services.ai.agentes import (
    ANAMNESE,
    DESENVOLVIMENTO,
    ESCALAS,
    DocumentoExtraido,
    Especialista,
    documentos_em_texto,
    em_paralelo,
    extrair_documentos,
    preencher_campos,
    redigir_estudo_de_caso,
)
from app.services.ai.agentes.extracao import AoProgredir, ErroNaEtapaDaIA, sem_aviso, motivo_do_erro
from app.services.ai.erros import cota_diaria_esgotada
from app.services.ai.schemas import ProtocoloPorIA

MAXIMO_DE_CAMPOS = 3000
TAMANHO_MAXIMO_TEXTO = 8000


class OpcaoDoCatalogo(BaseModel):
    valor: str = Field(max_length=200)
    rotulo: str = Field(default="", max_length=1500)  # opções da CARS trazem a descrição clínica do grau


class CampoDoCatalogo(BaseModel):
    id: str = Field(max_length=120, pattern=r"^[A-Za-z0-9_\-]+$")
    secao: str = Field(default="", max_length=200)
    grupo: str = Field(default="", max_length=200)
    rotulo: str = Field(default="", max_length=1500)
    tipo: Literal["texto", "numero", "opcao", "marcar"]
    opcoes: list[OpcaoDoCatalogo] = Field(default_factory=list, max_length=60)
    min: float | None = None
    max: float | None = None


class CatalogoDoProtocolo(BaseModel):
    campos: list[CampoDoCatalogo] = Field(max_length=MAXIMO_DE_CAMPOS)
    # Orientações extras do formulário (ex.: lista de habilidades por ano escolar).
    contexto: str = Field(default="", max_length=20000)


def formatar_catalogo(catalogo: CatalogoDoProtocolo) -> str:
    """Catálogo em texto compacto, agrupado por seção e grupo."""
    linhas: list[str] = []
    secao_atual = grupo_atual = None
    for campo in catalogo.campos:
        if campo.secao != secao_atual:
            secao_atual, grupo_atual = campo.secao, None
            linhas.append(f"\n## {campo.secao or 'Outros'}")
        if campo.grupo and campo.grupo != grupo_atual:
            grupo_atual = campo.grupo
            linhas.append(f"### {campo.grupo}")
        if campo.tipo == "opcao":
            opcoes = " | ".join(
                o.valor if not o.rotulo or o.rotulo == o.valor else f"{o.valor}={o.rotulo}" for o in campo.opcoes
            )
            descricao = f"opções: {opcoes}"
        elif campo.tipo == "numero":
            faixa = f" ({campo.min:g} a {campo.max:g})" if campo.min is not None and campo.max is not None else ""
            descricao = f"número{faixa}"
        elif campo.tipo == "marcar":
            descricao = "marcar: sim/não"
        else:
            descricao = "texto livre"
        linhas.append(f"- [{campo.id}] {campo.rotulo} · {descricao}")
    if catalogo.contexto.strip():
        linhas.append("\n## Orientações do protocolo\n" + catalogo.contexto.strip())
    return "\n".join(linhas).strip()


def _numero(valor: str) -> float | None:
    try:
        return float(valor.strip().replace("%", "").replace(",", "."))
    except ValueError:
        return None


def _normalizar(texto: str) -> str:
    return " ".join(texto.lower().split())


_ANOS = re.compile(r"(\d+)\s*anos?\b")
_MESES = re.compile(r"(\d+)\s*m[eê]s(?:es)?\b")


def _idade_em_anos_e_meses(valor: str) -> tuple[int, int] | None:
    """'2 anos e 6 meses', '1 ano e meio', '18 meses', 'com 3 anos' → (anos, meses)."""
    texto = _normalizar(valor)
    anos, meses = _ANOS.search(texto), _MESES.search(texto)
    if not anos and not meses:
        return None
    total = (int(anos.group(1)) if anos else 0) * 12 + (int(meses.group(1)) if meses else 0)
    if "e meio" in texto and not meses:
        total += 6
    return total // 12, total % 12


def _opcao_de_anos(campo: CampoDoCatalogo, anos: int) -> str | None:
    """Opção do select de anos ("Antes de 1 ano", "2 anos", "6 anos ou mais")."""
    for opcao in campo.opcoes:
        rotulo = _normalizar(opcao.valor)
        numero = re.match(r"(\d+)", rotulo)
        if anos == 0 and rotulo.startswith("antes de 1"):
            return opcao.valor
        if numero and (int(numero.group(1)) == anos or ("ou mais" in rotulo and anos >= int(numero.group(1)))):
            return opcao.valor
    return None


def _opcao_de_meses(campo: CampoDoCatalogo, meses: int) -> str | None:
    return next((o.valor for o in campo.opcoes if re.match(rf"{meses}\s*m", _normalizar(o.valor))), None)


def _idades_em_partes(protocolo: ProtocoloPorIA, por_id: dict[str, CampoDoCatalogo]) -> dict[str, str]:
    """A IA às vezes devolve a idade inteira num campo de anos ("2 anos e 6
    meses" em desfraldeAno). Divide nos selects de ano e mês do formulário."""
    partes: dict[str, str] = {}
    for item in protocolo.campos:
        campo = por_id.get(item.id)
        if (
            campo is None
            or campo.tipo != "opcao"
            or not item.id.endswith("Ano")
            or any(o.valor == item.valor for o in campo.opcoes)
        ):
            continue
        idade = _idade_em_anos_e_meses(item.valor or "")
        if idade is None:
            continue
        anos = _opcao_de_anos(campo, idade[0])
        if anos:
            partes[item.id] = anos
        campo_mes = por_id.get(item.id[: -len("Ano")] + "Mes")
        meses = campo_mes and _opcao_de_meses(campo_mes, idade[1])
        if meses:
            partes[campo_mes.id] = meses
    return partes


def respostas_para_answers(protocolo: ProtocoloPorIA, catalogo: CatalogoDoProtocolo) -> tuple[dict, list[str]]:
    """Converte a resposta da IA no `answers_json` do formulário (chaves =
    ids dos campos, mesmo formato de `coletarDados()`). Campos fora do
    catálogo ou com valor inválido são descartados e devolvidos à parte."""
    por_id = {c.id: c for c in catalogo.campos}
    answers: dict = {}
    descartados: list[str] = []
    idades = _idades_em_partes(protocolo, por_id)

    for item in protocolo.campos:
        campo = por_id.get(item.id)
        valor = (item.valor or "").strip()
        if campo is None or not valor:
            descartados.append(item.id)
            continue
        if campo.tipo == "opcao":
            if campo.id in idades and campo.id.endswith("Ano"):  # já dividida em ano + mês acima
                continue
            escolhida = next((o.valor for o in campo.opcoes if o.valor == valor), None)
            if escolhida is None:  # a IA às vezes devolve o rótulo da opção
                escolhida = next((o.valor for o in campo.opcoes if _normalizar(o.rotulo) == _normalizar(valor)), None)
            if escolhida is None:
                descartados.append(item.id)
                continue
            answers[campo.id] = escolhida
        elif campo.tipo == "numero":
            numero = _numero(valor)
            if (
                numero is None
                or (campo.min is not None and numero < campo.min)
                or (campo.max is not None and numero > campo.max)
            ):
                descartados.append(item.id)
                continue
            answers[campo.id] = f"{numero:g}"
        elif campo.tipo == "marcar":
            answers[campo.id] = _normalizar(valor) in {"sim", "s", "true", "x", "marcado", "verdadeiro"}
        else:
            answers[campo.id] = valor[:TAMANHO_MAXIMO_TEXTO]

    # Mês tirado de "2 anos e 6 meses" só entra se a IA não preencheu o mês.
    for campo_id, valor in idades.items():
        if campo_id.endswith("Mes"):
            answers.setdefault(campo_id, valor)
        else:
            answers[campo_id] = valor
    if protocolo.estudo_de_caso.strip():
        answers["estudoCaso"] = protocolo.estudo_de_caso.strip()[: TAMANHO_MAXIMO_TEXTO * 2]
    return answers, descartados


# Escolhidos pela psicóloga na tela do Laudo Por IA, antes de enviar os PDFs
# — a IA não preenche: hipóteses diagnósticas (hip_*), encaminhamentos
# (enc_*), situação e idade do desfralde, ano escolar e o desempenho em cada
# habilidade do ano (hab_status_N). A IA recebe essas respostas como dados
# confirmados e faz o resto com base nelas (inclusive hab_obs_N).
CAMPOS_DA_PROFISSIONAL = re.compile(r"^(hip_|enc_|hab_status_\d+$|anoEscolar$|desfralde(Ano|Mes)?$)")
# Os que a tela envia como valor escolhido (hipóteses e encaminhamentos vão marcados à parte).
CAMPOS_ESCOLHIDOS = re.compile(r"^(hab_status_\d+|anoEscolar|desfralde(Ano|Mes)?)$")


def escolhas_da_profissional(
    catalogo: CatalogoDoProtocolo, hipoteses: list[str], encaminhamentos: list[str]
) -> dict[str, bool]:
    """Caixas marcadas pela psicóloga, só as que existem no catálogo."""
    marcar = {c.id for c in catalogo.campos if c.tipo == "marcar"}
    escolhidas = [i for i in hipoteses if i.startswith("hip_")] + [i for i in encaminhamentos if i.startswith("enc_")]
    return {i: True for i in escolhidas if i in marcar}


def valores_da_profissional(catalogo: CatalogoDoProtocolo, valores: dict) -> dict[str, str]:
    """Desfralde, ano escolar e habilidades escolhidos pela psicóloga: só
    campos que existem no catálogo e só valores que são opções deles."""
    por_id = {c.id: c for c in catalogo.campos}
    aceitos: dict[str, str] = {}
    for campo_id, valor in valores.items():
        campo = por_id.get(campo_id)
        if campo is None or not CAMPOS_ESCOLHIDOS.match(campo_id) or not isinstance(valor, str):
            continue
        if any(o.valor == valor for o in campo.opcoes):
            aceitos[campo_id] = valor
    return aceitos


def _habilidades_do_ano(catalogo: CatalogoDoProtocolo, ano: str) -> list[str]:
    """Nomes das habilidades do ano escolar, da linha "- {ano}: 0=…; 1=…" do contexto."""
    for linha in catalogo.contexto.splitlines():
        if linha.startswith(f"- {ano}: "):
            return [item.split("=", 1)[1] for item in linha.removeprefix(f"- {ano}: ").split("; ") if "=" in item]
    return []


def dados_da_profissional_em_texto(catalogo: CatalogoDoProtocolo, valores: dict[str, str]) -> str:
    """As escolhas da psicóloga como dados confirmados para o prompt da IA."""
    linhas: list[str] = []
    if valores.get("desfralde"):
        idade = " e ".join(v for v in (valores.get("desfraldeAno"), valores.get("desfraldeMes")) if v)
        linhas.append(f"Desfralde: {valores['desfralde']}" + (f", com {idade}" if idade else ""))
    ano = valores.get("anoEscolar")
    if ano:
        linhas.append(f"Ano escolar: {ano}")
        nomes = _habilidades_do_ano(catalogo, ano)
        for i, nome in enumerate(nomes):
            if valores.get(f"hab_status_{i}"):
                linhas.append(f"Habilidade nº {i} ({nome}): {valores[f'hab_status_{i}']}")
    if not linhas:
        return ""
    return "Dados confirmados pela profissional (use como verdade; não os altere):\n" + "\n".join(
        f"- {l}" for l in linhas
    )


# Qual especialista cuida de cada seção do formulário (pelo título da seção;
# o resto fica com a anamnese).
SECOES_POR_ESPECIALISTA: dict[str, tuple[str, ...]] = {
    ESCALAS.nome: ("ATA E CARS", "Protocolo TOD", "SNAP-IV", "M-CHAT"),
    DESENVOLVIMENTO.nome: (
        "Portage",
        "Habilidades Acadêmicas",
        "Habilidades Cognitivas",
        "Funções Executivas",
        "Por Domínio",
    ),
}
ESPECIALISTAS: tuple[Especialista, ...] = (ANAMNESE, ESCALAS, DESENVOLVIMENTO)
ROTULOS_DAS_ETAPAS = {
    ANAMNESE.nome: "anamnese e histórico",
    ESCALAS.nome: "escalas",
    DESENVOLVIMENTO.nome: "desenvolvimento",
    "estudo_de_caso": "estudo de caso",
}


def dividir_catalogo(catalogo: CatalogoDoProtocolo) -> dict[str, CatalogoDoProtocolo]:
    """Parte do catálogo de cada especialista (só os que têm campos)."""
    partes: dict[str, list[CampoDoCatalogo]] = {e.nome: [] for e in ESPECIALISTAS}
    for campo in catalogo.campos:
        if CAMPOS_DA_PROFISSIONAL.match(campo.id):
            continue
        dono = next(
            (
                nome
                for nome, secoes in SECOES_POR_ESPECIALISTA.items()
                if any(s.lower() in campo.secao.lower() for s in secoes)
            ),
            ANAMNESE.nome,
        )
        partes[dono].append(campo)
    return {
        nome: CatalogoDoProtocolo(campos=campos, contexto=catalogo.contexto)
        for nome, campos in partes.items()
        if campos
    }


@dataclass
class ResultadoDaIA:
    protocolo: ProtocoloPorIA
    documentos: list[DocumentoExtraido]
    tempos: dict[str, float] = field(default_factory=dict)


def preencher_protocolo(
    *,
    provider: str,
    model: str,
    api_key: str,
    paciente: str,
    pdfs: list[dict],
    catalogo: CatalogoDoProtocolo,
    observacoes: str | None = None,
    com_estudo_de_caso: bool = True,
    ao_progredir: AoProgredir | None = None,
) -> ResultadoDaIA:
    """Laudo Por IA em duas etapas paralelas:
    1. um agente por PDF transcreve o arquivo em JSON (com cache);
    2. sobre esse JSON, ao mesmo tempo, o redator escreve o estudo de caso e
       cada especialista preenche a sua parte do catálogo."""
    avisar = ao_progredir or sem_aviso
    credenciais = {"provider": provider, "model": model, "api_key": api_key}
    inicio = time.monotonic()
    documentos = extrair_documentos(pdfs=pdfs, ao_progredir=ao_progredir, **credenciais)
    fim_da_extracao = time.monotonic()

    texto = documentos_em_texto(documentos)
    partes = dividir_catalogo(catalogo)
    especialistas = [e for e in ESPECIALISTAS if e.nome in partes]

    def etapa(nome: str, funcao):
        """Avisa o fim de cada agente e diz qual parte falhou."""

        def rodar():
            try:
                resultado = funcao()
            except Exception as exc:
                if cota_diaria_esgotada(exc):
                    raise
                raise ErroNaEtapaDaIA(
                    f'Os documentos foram lidos, mas não foi possível concluir a parte "{ROTULOS_DAS_ETAPAS[nome]}" '
                    f"({motivo_do_erro(exc)}). Tente de novo: os documentos não serão lidos outra vez."
                ) from exc
            avisar("etapa_concluida", etapa=nome)
            return resultado

        return rodar

    tarefas = [
        etapa(
            e.nome,
            partial(
                preencher_campos,
                especialista=e,
                paciente=paciente,
                documentos_texto=texto,
                catalogo_texto=formatar_catalogo(partes[e.nome]),
                observacoes=observacoes,
                **credenciais,
            ),
        )
        for e in especialistas
    ]
    if com_estudo_de_caso:
        tarefas.append(
            etapa(
                "estudo_de_caso",
                partial(
                    redigir_estudo_de_caso,
                    paciente=paciente,
                    documentos_texto=texto,
                    observacoes=observacoes,
                    **credenciais,
                ),
            )
        )
    avisar("preenchendo", etapas=[e.nome for e in especialistas] + (["estudo_de_caso"] if com_estudo_de_caso else []))
    resultados = em_paralelo(tarefas)

    estudo = resultados.pop() if com_estudo_de_caso else ""
    campos = [c for r in resultados for c in r.campos]
    lacunas = [lacuna for r in resultados for lacuna in r.lacunas]
    return ResultadoDaIA(
        protocolo=ProtocoloPorIA(estudo_de_caso=estudo, campos=campos, lacunas=lacunas),
        documentos=documentos,
        tempos={
            "extracao_s": round(fim_da_extracao - inicio, 1),
            "especialistas_s": round(time.monotonic() - fim_da_extracao, 1),
        },
    )
