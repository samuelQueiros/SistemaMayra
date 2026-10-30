"""Pendências de um laudo: o que ficou sem resposta depois do Laudo por IA,
organizado para a psicóloga completar na tela.

Calculado pelo sistema (sem IA), a partir do catálogo do protocolo (o mesmo
que a IA recebeu — `catalogoParaIA()` do formulário) e das respostas do
laudo. Nenhum id técnico de campo é usado como texto: os rótulos vêm do
próprio formulário.

- Seções com nome amigável e essenciais primeiro. Os essenciais das seções
  1 a 4 são os mesmos do formulário (`REGRAS` em
  formulario-novo-paciente.html — um teste confere que continuam iguais).
- Cada escala vira uma pendência só ("Pontuações da ATA: 22 itens"), e só
  aparece se foi aplicada: PDF daquela escala lido, algum item preenchido ou
  marcada pela psicóloga em "Também apliquei".
- Checkbox (hipóteses, encaminhamentos) não é pendência: desmarcado já é
  resposta. Percentuais calculados pelo formulário ficam de fora.
- Descrição "(se Sim)" só aparece quando a resposta de origem é Sim; pares
  ano/mês ("Andou com") viram um item só."""

import re
from dataclasses import dataclass

from app.services.laudo_ia import CatalogoDoProtocolo, CampoDoCatalogo


@dataclass(frozen=True)
class Secao:
    numero: str  # número do <h2> no formulário
    chave: str
    titulo: str
    essenciais: frozenset[str] = frozenset()


SECOES = (
    Secao("1", "identificacao", "Identificação e escola", frozenset({"responsavel", "escola", "anoEscolar"})),
    Secao(
        "2",
        "gestacao",
        "Gestação e parto",
        frozenset(
            {"idadeMaeGestacao", "idadeGestacional", "intercorrenciasGestacionais", "parto", "complicacaoParto",
             "usoMedicamentosGestacao", "sofrimentoFetal"}
        ),
    ),
    Secao(
        "3",
        "desenvolvimento",
        "Desenvolvimento",
        frozenset({"filhoUnico", "filhoUnicoDescricao", "convivenciaSocial", "andouAno", "falouAno", "desfralde", "desfraldeAno"}),
    ),
    Secao(
        "4",
        "historico",
        "Histórico clínico e queixas",
        frozenset(
            {"encaminhamento", "diagnosticoAtual", "laudoAnterior", "familiaLaudo", "transtornoFamilia", "irmaosDiagnostico",
             "terapias", "queixaFamiliar", "queixaEscolarCuidador"}
        ),
    ),
    Secao("6", "observacoes", "Observações clínicas"),
    Secao("8", "habilidades", "Habilidades acadêmicas"),
    Secao("12", "funcoes_executivas", "Funções executivas"),
    Secao("17", "dominios", "Distribuição das dificuldades por domínio"),
)
SECOES_DO_ESTUDO_DE_CASO = frozenset({"identificacao", "gestacao", "desenvolvimento", "historico"})


@dataclass(frozen=True)
class Escala:
    chave: str
    titulo: str
    padrao: re.Pattern
    tipos_de_documento: frozenset[str]


ESCALAS = (
    Escala("ata", "Pontuações da ATA", re.compile(r"^ata_item_\d+$"), frozenset({"ata"})),
    Escala("cars", "CARS", re.compile(r"^cars_\d+$"), frozenset({"cars"})),
    Escala("snap", "SNAP-IV", re.compile(r"^snap_\d+$"), frozenset({"snap_iv"})),
    Escala("tod", "TOD", re.compile(r"^tod_\d+$"), frozenset({"tod"})),
    Escala("portage", "Portage", re.compile(r"^portage_"), frozenset({"portage"})),
    Escala("mchat", "M-CHAT", re.compile(r"^mchat_\d+$"), frozenset({"m_chat"})),
)


def metodos_nao_aplicados(answers: dict, tipos_de_documento: set[str]) -> list[str]:
    """Escalas sem PDF próprio e sem nenhuma resposta: saem dos "Métodos do
    relatório" (a psicóloga pode marcá-las de volta nas pendências)."""
    return [
        e.chave
        for e in ESCALAS
        if not tipos_de_documento & e.tipos_de_documento
        and not any(e.padrao.match(chave) and not _vazio(valor) for chave, valor in answers.items())
    ]


# Percentuais da tabela da ATA: complementam a escala, opcionais.
_ATA_PERCENTUAIS = re.compile(r"^ata_perc_\d+$")
# Preenchidos pelo próprio formulário a partir dos itens.
_CALCULADOS = frozenset({"ataPercentual", "carsPercentualFalhas"})

# Só faz sentido perguntar quando a resposta de origem pede.
_CONDICOES = {
    "idadeLaudoAno": ("laudoAnterior", {"Sim"}),
    "idadeLaudoMes": ("laudoAnterior", {"Sim"}),
    # Irmãos (idade e laudo): pergunta-se quando NÃO é filho único.
    "filhoUnicoDescricao": ("filhoUnico", {"Não"}),
    "desfraldeAno": ("desfralde", {"Controle Total", "Controle Diurno", "Escapes"}),
    "desfraldeMes": ("desfralde", {"Controle Total", "Controle Diurno", "Escapes"}),
}
_SUFIXO_DESCRICAO = "Descricao"


def _numero_da_secao(titulo: str) -> str:
    return titulo.split(".", 1)[0].strip()


def _vazio(valor) -> bool:
    return valor is None or valor is False or (isinstance(valor, str) and not valor.strip())


def _subcampo(campo: CampoDoCatalogo) -> dict:
    tipo = campo.tipo
    if tipo == "opcao" and [o.valor for o in campo.opcoes] == ["Sim", "Não"]:
        tipo = "simnao"
    elif tipo == "texto" and "data" in campo.rotulo.lower().split():
        tipo = "data"
    return {
        "id": campo.id,
        "tipo": tipo,
        "opcoes": [{"valor": o.valor, "rotulo": o.rotulo or o.valor} for o in campo.opcoes],
        "min": campo.min,
        "max": campo.max,
    }


def _nomes_das_habilidades(contexto: str, ano: str | None) -> list[str]:
    """Lista de habilidades do ano escolar, a partir do contexto do catálogo
    ("- 2º Ano: 0=Leitura; 1=Escrita")."""
    if not ano:
        return []
    for linha in contexto.splitlines():
        if linha.startswith(f"- {ano}:"):
            return [item.split("=", 1)[1].strip() for item in linha.split(":", 1)[1].split(";") if "=" in item]
    return []


class Pendencias:
    def __init__(
        self,
        catalogo: CatalogoDoProtocolo,
        answers: dict,
        dados: dict | None,
        tipos_de_documento: list[str],
        escalas_adicionadas: list[str],
        sugestoes: list[dict],
    ):
        self.catalogo = catalogo
        self.answers = answers or {}
        self.dados = dados or {}
        self.tipos = set(tipos_de_documento)
        self.adicionadas = set(escalas_adicionadas)
        self.sugestoes: dict[str, list[dict]] = {}
        for s in sugestoes:
            self.sugestoes.setdefault(s["campo_id"], []).append(s)
        self.por_id = {c.id: c for c in catalogo.campos}

    # -- valores -------------------------------------------------------------

    def valor(self, campo_id: str):
        dado = self.dados.get(campo_id)
        if dado and dado.get("situacao") == "preenchido":
            return dado.get("valor")
        return self.answers.get(campo_id)

    def _pendente_no_laudo(self, campo_id: str) -> bool:
        return _vazio(self.answers.get(campo_id))

    def _estado(self, ids: list[str]) -> dict:
        principal = ids[0]
        dado = self.dados.get(principal) or {}
        sugestoes = [s for i in ids for s in self.sugestoes.get(i, []) if not self.dados.get(i)]
        return {
            "valores": {i: (self.dados.get(i) or {}).get("valor") for i in ids},
            "situacao": dado.get("situacao"),
            "origem": dado.get("origem"),
            "sugestoes": sugestoes,
        }

    def _relevante(self, campo: CampoDoCatalogo) -> bool:
        if campo.tipo == "marcar" or campo.id in _CALCULADOS:
            return False
        condicao = _CONDICOES.get(campo.id)
        if condicao:
            return self.valor(condicao[0]) in condicao[1]
        if campo.id.endswith(_SUFIXO_DESCRICAO):
            return self.valor(campo.id[: -len(_SUFIXO_DESCRICAO)]) == "Sim"
        return True

    # -- montagem -------------------------------------------------------------

    def _item(self, campos: list[CampoDoCatalogo], rotulo: str, essencial: bool) -> dict:
        ids = [c.id for c in campos]
        return {
            "chave": ids[0],
            "rotulo": rotulo,
            "essencial": essencial,
            "campos": [_subcampo(c) for c in campos],
            **self._estado(ids),
        }

    def _itens_da_secao(self, secao: Secao, campos: list[CampoDoCatalogo]) -> list[dict]:
        itens: list[dict] = []
        por_rotulo: dict[str, dict] = {}
        for campo in campos:
            if not self._relevante(campo) or not self._pendente_no_laudo(campo.id):
                continue
            # "Andou com": ano + mês num item só; observação do mesmo rótulo à parte.
            if campo.id.endswith("Mes") and campo.id[:-3] + "Ano" in self.por_id:
                dono = por_rotulo.get(campo.id[:-3] + "Ano")
                if dono is not None:
                    dono["campos"].append(_subcampo(campo))
                    continue
            rotulo = f"{campo.grupo} — {campo.rotulo}" if campo.grupo else campo.rotulo
            if campo.id == "filhoUnicoDescricao":
                rotulo = "Irmãos — idade e se tem laudo"
            elif campo.id.endswith(_SUFIXO_DESCRICAO):
                rotulo = rotulo.replace("— descrição (se Sim)", "— descreva").strip()
            elif campo.tipo == "texto" and any(i["rotulo"] == rotulo for i in itens):
                rotulo += " — observações"
            item = self._item([campo], rotulo, campo.id in secao.essenciais)
            itens.append(item)
            por_rotulo[campo.id] = item
        return sorted(itens, key=lambda i: not i["essencial"])

    def _habilidades(self, secao: Secao, campos: list[CampoDoCatalogo]) -> tuple[str, list[dict]]:
        ano = self.valor("anoEscolar")
        nomes = _nomes_das_habilidades(self.catalogo.contexto, ano)
        itens = []
        for indice, nome in enumerate(nomes):
            status_id, obs_id = f"hab_status_{indice}", f"hab_obs_{indice}"
            if status_id in self.por_id and self._pendente_no_laudo(status_id):
                itens.append(self._item([self.por_id[status_id]], nome, True))
            if obs_id in self.por_id and self._pendente_no_laudo(obs_id):
                itens.append(self._item([self.por_id[obs_id]], f"{nome} — observação", False))
        titulo = f"Habilidades acadêmicas do {ano}" if ano else secao.titulo
        return titulo, sorted(itens, key=lambda i: not i["essencial"])

    def _escala_aplicada(self, escala: Escala, campos: list[CampoDoCatalogo]) -> bool:
        return (
            escala.chave in self.adicionadas
            or bool(self.tipos & escala.tipos_de_documento)
            or any(not _vazio(self.answers.get(c.id)) for c in campos)
        )

    def montar(self) -> dict:
        grupos: list[dict] = []
        por_secao: dict[str, list[CampoDoCatalogo]] = {}
        for campo in self.catalogo.campos:
            por_secao.setdefault(_numero_da_secao(campo.secao), []).append(campo)

        for secao in SECOES:
            campos = por_secao.get(secao.numero, [])
            if secao.chave == "habilidades":
                titulo, itens = self._habilidades(secao, campos)
            else:
                titulo, itens = secao.titulo, self._itens_da_secao(secao, campos)
            if itens:
                grupos.append({"chave": secao.chave, "titulo": titulo, "escala": False, "itens": itens})

        escalas_fora: list[dict] = []
        for escala in ESCALAS:
            if escala.chave in self.answers.get("__metodosExcluidos", []):
                continue
            campos = [c for c in self.catalogo.campos if escala.padrao.match(c.id)]
            if not campos:
                continue
            if not self._escala_aplicada(escala, campos):
                escalas_fora.append({"chave": escala.chave, "titulo": escala.titulo})
                continue
            itens = [self._item([c], c.rotulo, True) for c in campos if self._pendente_no_laudo(c.id)]
            if escala.chave == "ata":
                itens += [
                    self._item([c], f"{c.rotulo} — % na tabela", False)
                    for c in self.catalogo.campos
                    if _ATA_PERCENTUAIS.match(c.id) and self._pendente_no_laudo(c.id)
                ]
            if itens:
                grupos.append({"chave": f"escala_{escala.chave}", "titulo": escala.titulo, "escala": True, "itens": itens})

        # Progresso: cada item essencial conta 1; cada escala conta 1 (resolvida
        # quando todos os seus itens essenciais estão resolvidos).
        total = resolvidos = 0
        for grupo in grupos:
            grupo["essencial"] = any(i["essencial"] for i in grupo["itens"])
            contados = [i for i in grupo["itens"] if i["essencial"]] if grupo["essencial"] else grupo["itens"]
            grupo["pendentes"] = sum(1 for i in contados if not i["situacao"])
            if grupo["escala"] and grupo["essencial"]:
                total += 1
                resolvidos += grupo["pendentes"] == 0
            else:
                essenciais = [i for i in grupo["itens"] if i["essencial"]]
                total += len(essenciais)
                resolvidos += sum(1 for i in essenciais if i["situacao"])
        grupos.sort(key=lambda g: not g["essencial"])

        return {
            "essenciais": {"total": total, "resolvidos": resolvidos},
            "grupos": grupos,
            "escalas_para_adicionar": escalas_fora,
        }


def _para_o_formulario(valor):
    """Valor confirmado no formato que o formulário guarda (texto)."""
    if isinstance(valor, float):
        return f"{valor:g}"
    return valor


def aplicar_dados_confirmados(catalogo: CatalogoDoProtocolo, answers: dict, dados: dict | None) -> tuple[dict, set[str]]:
    """Copia para as respostas do laudo os dados confirmados pela psicóloga
    ("preenchido") de campos do protocolo que estão vazios. Nunca sobrescreve
    o que já tem resposta; dispensados ("não se aplica"/"não informado") não
    vão para o laudo."""
    novas = dict(answers or {})
    aplicados: set[str] = set()
    ids = {c.id for c in catalogo.campos}
    for campo_id, dado in (dados or {}).items():
        if campo_id not in ids or dado.get("situacao") != "preenchido" or _vazio(dado.get("valor")):
            continue
        if _vazio(novas.get(campo_id)):
            novas[campo_id] = _para_o_formulario(dado["valor"])
            aplicados.add(campo_id)
    return novas, aplicados


def estudo_de_caso_editado(answers: dict, computed: dict) -> bool:
    """A psicóloga mudou o estudo de caso escrito pela IA? Sem o original
    guardado (laudos antigos), considera editado — nunca sobrescreve à toa."""
    original = (computed or {}).get("estudo_de_caso_ia")
    if original is None:
        return True
    return (answers or {}).get("estudoCaso", "").strip() != original.strip()


def dados_confirmados_como_documento(catalogo: CatalogoDoProtocolo, answers: dict, ids: set[str]) -> dict:
    """Dados novos no mesmo formato dos documentos lidos dos PDFs, para o
    redator do estudo de caso (que não relê os PDFs)."""
    rotulos = {c.id: c for c in catalogo.campos}
    return {
        "arquivo": "",
        "tipo": "outro",
        "titulo": "Dados complementares confirmados pela profissional",
        "respondente": "",
        "data": "",
        "respostas": [
            {"pergunta": f"{rotulos[i].secao} — {rotulos[i].rotulo}", "resposta": str(answers[i])}
            for i in sorted(ids)
        ],
        "observacoes": "",
    }


def campos_novos_para_o_estudo(catalogo: CatalogoDoProtocolo, answers: dict, dados: dict | None, integrados: list[str] | None) -> set[str]:
    """Dados confirmados, já no laudo, das seções que alimentam o estudo de
    caso e que o texto ainda não incorporou (`computed_json.estudo_campos_integrados`)."""
    numeros = {s.numero for s in SECOES if s.chave in SECOES_DO_ESTUDO_DE_CASO}
    do_estudo = {c.id for c in catalogo.campos if _numero_da_secao(c.secao) in numeros}
    confirmados = {
        campo_id
        for campo_id, dado in (dados or {}).items()
        if dado.get("situacao") == "preenchido" and not _vazio((answers or {}).get(campo_id))
    }
    return (confirmados & do_estudo) - set(integrados or [])
