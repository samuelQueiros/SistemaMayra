import base64
import io
from datetime import date, datetime

import matplotlib

matplotlib.use("Agg")  # backend sem interface gráfica, seguro em servidor
import matplotlib.pyplot as plt
from weasyprint import HTML

from app.services.laudo_documento import _buscador_somente_data_uri, html_para_pdf
from app.services.storage import get_photos_storage, get_reports_storage

_COR_PRIMARIA = "#7561ae"
_CORES = ["#7561ae", "#d9709f", "#8fb4d6", "#f5a623", "#3fa35b", "#b3a5e2", "#e7a8c8", "#dce9f5"]


# Laudos cujo documento final (HTML completo) é montado no navegador e salvo
# em generated_text: o protocolo fixo, os modelos de protocolo configuráveis
# e o relatório por IA a partir de PDFs de formulários.
RULE_TYPES_COM_HTML_PRONTO = {"custom_form", "protocolo", "relatorio_ia_pdf"}


def render_report_pdf(*, patient, template, report, psychologist=None) -> tuple[str, bytes]:
    """Gera o PDF do laudo (dados do paciente, tabela de pontuações,
    gráfico, classificação e texto revisado — SPEC.md seção 2/Prompt 4.2),
    incluindo as seções clínicas opcionais, fotos do paciente e assinatura
    profissional quando presentes (ver ENTREGAS.md — "PDF completo"), e
    salva via `services/storage` (disco local ou S3, conforme configurado),
    devolvendo a chave de armazenamento do arquivo e o conteúdo do PDF."""

    chave = f"{report.id}.pdf"

    if template.schema_json.get("rule_type") in RULE_TYPES_COM_HTML_PRONTO:
        # O laudo já vem pronto (HTML completo, com <style> embutido) do
        # formulário standalone, salvo em generated_text via PUT
        # /api/reports/{id}/text — não passa pelas tabelas de
        # pontuação/gráfico Matplotlib do motor de regras dinâmico.
        pdf_bytes = html_para_pdf(report.generated_text or "<p>Laudo vazio.</p>")
        get_reports_storage().save(chave, pdf_bytes)
        return chave, pdf_bytes

    grafico_data_uri = _gerar_grafico(template.schema_json, report.computed_json or {})
    html = _montar_html(patient, template, report, grafico_data_uri, psychologist)

    # Só imagens embutidas (data:): o texto do laudo vem do usuário e não pode
    # puxar arquivos do servidor (file://) nem URLs externas para dentro do PDF.
    pdf_bytes = HTML(string=html, url_fetcher=_buscador_somente_data_uri()).write_pdf()
    get_reports_storage().save(chave, pdf_bytes)
    return chave, pdf_bytes


def _eh_resultado_idade_equivalente(computed: dict) -> bool:
    """`age_equivalent_percentage` (Portage) devolve {"areas": {...}} em vez
    de {"scores": {...}} — ver rules_engine/age_equivalent_percentage.py."""
    return "areas" in computed and "scores" not in computed


def _gerar_grafico(schema: dict, computed: dict) -> str | None:
    if _eh_resultado_idade_equivalente(computed):
        return _gerar_grafico_idade_equivalente(schema, computed)

    scores = computed.get("scores")
    if not scores:
        return None

    areas = schema.get("areas", [])
    labels = [a["label"] for a in areas if a["key"] in scores]
    values = [scores[a["key"]] for a in areas if a["key"] in scores]
    if not values:
        return None

    chart_type = schema.get("chart", {}).get("type", "bar")

    # Barras horizontais: com escalas de muitas áreas (ex.: CARS tem 15), um
    # gráfico de barras verticais amontoa e sobrepõe os rótulos do eixo X.
    # Deitar as barras dá espaço de sobra para o texto de cada área, sem
    # rotação nem sobreposição.
    if chart_type == "bar":
        return _grafico_barra_horizontal(labels, values, schema.get("name", ""))

    fig = plt.figure(figsize=(6, 4))
    if chart_type == "pie":
        ax = fig.add_subplot(111)
        ax.pie(values, labels=labels, colors=_CORES, autopct="%1.0f%%")
    else:  # radar
        ax = fig.add_subplot(111, polar=True)
        angulos = [n / float(len(labels)) * 2 * 3.14159265 for n in range(len(labels))]
        valores_fechados = values + values[:1]
        angulos_fechados = angulos + angulos[:1]
        ax.plot(angulos_fechados, valores_fechados, color=_COR_PRIMARIA, linewidth=2)
        ax.fill(angulos_fechados, valores_fechados, color=_COR_PRIMARIA, alpha=0.25)
        ax.set_xticks(angulos)
        ax.set_xticklabels(labels, fontsize=7)

    ax.set_title(schema.get("name", ""))
    fig.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=150)
    plt.close(fig)
    buffer.seek(0)
    base64_png = base64.b64encode(buffer.read()).decode("ascii")
    return f"data:image/png;base64,{base64_png}"


def _gerar_grafico_idade_equivalente(schema: dict, computed: dict) -> str | None:
    areas_resultado = computed.get("areas", {})
    areas_schema = schema.get("areas", [])
    labels = [a["label"] for a in areas_schema if a["key"] in areas_resultado]
    values = [areas_resultado[a["key"]]["percentage"] for a in areas_schema if a["key"] in areas_resultado]
    if not values:
        return None

    return _grafico_barra_horizontal(
        labels,
        values,
        schema.get("name", ""),
        linha_referencia=100,
        rotulo_eixo_x="% Da Idade Cronológica",
    )


def _grafico_barra_horizontal(
    labels: list[str],
    values: list[float],
    titulo: str,
    *,
    linha_referencia: float | None = None,
    rotulo_eixo_x: str | None = None,
) -> str:
    altura = max(3.2, 0.4 * len(labels) + 1)
    fig = plt.figure(figsize=(7.5, altura))
    ax = fig.add_subplot(111)

    posicoes = range(len(labels))
    ax.barh(list(posicoes), values, color=_COR_PRIMARIA)
    ax.set_yticks(list(posicoes))
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()  # primeira área do modelo aparece no topo
    ax.tick_params(axis="x", labelsize=8)

    if linha_referencia is not None:
        ax.axvline(linha_referencia, color="#999", linestyle="--", linewidth=1)
    if rotulo_eixo_x:
        ax.set_xlabel(rotulo_eixo_x, fontsize=8)

    ax.set_title(titulo, fontsize=11)
    fig.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=150)
    plt.close(fig)
    buffer.seek(0)
    base64_png = base64.b64encode(buffer.read()).decode("ascii")
    return f"data:image/png;base64,{base64_png}"


def _formatar_data(valor: date | datetime) -> str:
    return valor.strftime("%d/%m/%Y")


def _cabecalho_tabela_pontuacao(computed: dict) -> str:
    if _eh_resultado_idade_equivalente(computed):
        return "<tr><th>Área</th><th>Idade De Desenvolvimento</th><th>Classificação</th></tr>"
    if computed.get("classifications"):
        return "<tr><th>Área</th><th>Pontuação</th><th>Classificação Da Área</th></tr>"
    # rule_type "sum_threshold" (ex.: CARS/ATA) só classifica o total geral,
    # não cada área — mostrar uma coluna "Classificação Da Área" sempre
    # vazia confundia mais do que ajudava (a classificação geral já aparece
    # logo abaixo da tabela).
    return "<tr><th>Área</th><th>Pontuação</th></tr>"


def _linhas_pontuacao(schema: dict, computed: dict) -> str:
    if _eh_resultado_idade_equivalente(computed):
        areas_resultado = computed.get("areas", {})
        linhas = []
        for area in schema.get("areas", []):
            resultado = areas_resultado.get(area["key"])
            if resultado is None:
                continue
            linhas.append(
                f"<tr><td>{area['label']}</td>"
                f"<td>{resultado['developmental_age_label']} ({resultado['percentage']}%)</td>"
                f"<td>{resultado.get('classification') or ''}</td></tr>"
            )
        return "".join(linhas)

    scores = computed.get("scores", {})
    classifications = computed.get("classifications")
    linhas = []
    for area in schema.get("areas", []):
        area_key = area["key"]
        if area_key not in scores:
            continue
        if classifications:
            linhas.append(
                f"<tr><td>{area['label']}</td><td>{scores[area_key]}</td>"
                f"<td>{classifications.get(area_key) or ''}</td></tr>"
            )
        else:
            linhas.append(f"<tr><td>{area['label']}</td><td>{scores[area_key]}</td></tr>")
    return "".join(linhas)


def _fotos_html(patient) -> str:
    fotos = getattr(patient, "photos", None)
    if not fotos:
        return ""

    fotos_storage = get_photos_storage()
    figuras = []
    for foto in fotos:
        if not fotos_storage.exists(foto.file_path):
            continue
        base64_img = base64.b64encode(fotos_storage.read(foto.file_path)).decode("ascii")
        mime = "image/png" if foto.file_path.lower().endswith(".png") else "image/jpeg"
        legenda = f"<figcaption>{foto.caption}</figcaption>" if foto.caption else ""
        figuras.append(
            f'<figure style="display:inline-block;margin:4px;">'
            f'<img src="data:{mime};base64,{base64_img}" style="max-width:150px;max-height:150px;">'
            f"{legenda}</figure>"
        )
    if not figuras:
        return ""
    return f"<h2>Fotos Do Paciente</h2><div>{''.join(figuras)}</div>"


def _secoes_clinicas_html(report) -> str:
    secoes = report.clinical_sections_json or {}
    if not secoes:
        return ""

    blocos = []
    _TITULOS = {
        "anamnese": "Anamnese Inicial",
        "historico_desenvolvimento": "Histórico De Desenvolvimento",
        "encaminhamento_queixas": "Encaminhamento, Histórico E Queixas",
        "metodologia": "Metodologia",
        "estudo_de_caso": "Estudo De Caso E Observações Clínicas",
        "plano_intervencao": "Plano De Intervenção",
        "consideracoes_finais": "Considerações Finais",
    }
    for campo, titulo in _TITULOS.items():
        texto = secoes.get(campo)
        if not texto:
            continue
        paragrafos = "".join(f"<p>{p}</p>" for p in texto.split("\n\n") if p.strip())
        blocos.append(f"<h2>{titulo}</h2>{paragrafos}")

    hipoteses = secoes.get("diagnostic_hypotheses")
    if hipoteses:
        # O relatório mostra só a hipótese marcada como selecionada, nunca
        # a lista completa das hipóteses investigadas. Laudos salvos antes
        # desse campo existir (nenhuma com `selected=True`) caem para a
        # primeira hipótese registrada, também sem listar as demais.
        selecionadas = [h for h in hipoteses if h.get("selected")]
        hipotese = (selecionadas or hipoteses)[0]
        cid = f" (CID: {hipotese['cid']})" if hipotese.get("cid") else ""
        blocos.append(f"<h2>Hipótese Diagnóstica</h2><ul><li>{hipotese['label']}{cid}</li></ul>")

    encaminhamentos = secoes.get("encaminhamentos")
    if encaminhamentos:
        itens = "".join(f"<li>{e}</li>" for e in encaminhamentos)
        blocos.append(f"<h2>Encaminhamentos</h2><ul>{itens}</ul>")

    return "".join(blocos)


# Texto padrão do bloco "Sobre A Profissional Responsável" — usado quando
# `Psychologist.bio_profissional` ainda não foi configurado (mesmo padrão
# do formulário standalone, ver perfilProfissional() em
# formulario-novo-paciente.html). Editável por psicólogo via PUT /auth/me.
_BIO_PROFISSIONAL_PADRAO = (
    "Este relatório foi elaborado por Mayra Vanessa Andrade da Cunha, "
    "Neuropsicopedagoga Clínica (CBO 2394-40) e Institucional (CBO "
    "2394-45), com formação especializada em Análise do Comportamento "
    "Aplicada (ABA) e atuação profissional voltada ao desenvolvimento, "
    "aprendizagem e acompanhamento de crianças neurodivergentes. Possui "
    "mais de 25 anos de experiência profissional na área educacional e "
    "mais de 15 anos de atuação com crianças com Transtorno do Espectro "
    "Autista (TEA), integrando experiência educacional, conhecimento "
    "técnico e prática clínica neuropsicopedagógica na análise "
    "individualizada de cada caso."
)


def _sobre_a_profissional_html(psychologist) -> str:
    if psychologist is None:
        return ""
    bio = psychologist.bio_profissional or _BIO_PROFISSIONAL_PADRAO
    return f"<h2>Sobre A Profissional Responsável</h2><p>{bio}</p>"


def _assinatura_html(psychologist, report) -> str:
    if psychologist is None:
        return ""
    registro = (
        f" — {psychologist.professional_registration}" if psychologist.professional_registration else ""
    )
    return f"""
    <div style="margin-top:40px;text-align:center;">
      <p>_____________________________________</p>
      <p><strong>{psychologist.name}</strong>{registro}</p>
      <p>{_formatar_data(report.created_at)}</p>
    </div>"""


def _montar_html(patient, template, report, grafico_data_uri: str | None, psychologist=None) -> str:
    computed = report.computed_json or {}
    # Correções manuais feitas no histórico (ver ReportChangeLog) têm
    # prioridade sobre o valor calculado originalmente.
    nome_modelo = report.template_name_override or template.name
    classification = report.classification_override or computed.get("classification")
    total = computed.get("total")

    texto_html = ""
    if report.generated_text:
        paragrafos = "".join(f"<p>{p}</p>" for p in report.generated_text.split("\n\n") if p.strip())
        texto_html = f"<h2>Parecer Descritivo</h2>{paragrafos}"

    resumo_geral = ""
    if classification:
        resumo_geral += f"<p><strong>Classificação geral:</strong> {classification}</p>"
    if total is not None:
        resumo_geral += f"<p><strong>Pontuação total:</strong> {total}</p>"

    grafico_html = (
        f'<img src="{grafico_data_uri}" style="max-width:100%">' if grafico_data_uri else ""
    )

    identificacao_extra = ""
    if patient.sex:
        identificacao_extra += f"<p><strong>Sexo:</strong> {patient.sex}</p>"
    if patient.school_info:
        identificacao_extra += f"<p><strong>Escola:</strong> {patient.school_info}</p>"

    fotos_html = _fotos_html(patient)
    secoes_clinicas_html = _secoes_clinicas_html(report)
    sobre_profissional_html = _sobre_a_profissional_html(psychologist)
    assinatura_html = _assinatura_html(psychologist, report)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: Arial, Helvetica, sans-serif; font-size: 11pt; color: #222; }}
  h1 {{ color: #5d52a5; font-size: 16pt; text-align: center; }}
  h2 {{ color: #443b91; background: #f5f2ff; border-left: 6px solid #7466b5; padding: 6px 10px; font-size: 12pt; }}
  table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
  th, td {{ border: 1px solid #999; padding: 6px; text-align: left; font-size: 10pt; }}
  th {{ background: #f5f2ff; }}
  .cabecalho {{ border-bottom: 3px solid #7466b5; padding-bottom: 10px; margin-bottom: 16px; }}
  .rodape {{ margin-top: 30px; font-size: 8pt; color: #666; border-top: 1px solid #ccc; padding-top: 8px; }}
</style>
</head>
<body>
  <div class="cabecalho">
    <h1>{nome_modelo}</h1>
    <p><strong>Paciente:</strong> {patient.name}</p>
    <p><strong>Data de nascimento:</strong> {_formatar_data(patient.birth_date)}</p>
    <p><strong>Data do atendimento:</strong> {_formatar_data(report.created_at)}</p>
    {identificacao_extra}
  </div>

  {fotos_html}

  <h2>Pontuações Por Área</h2>
  <table>
    {_cabecalho_tabela_pontuacao(computed)}
    {_linhas_pontuacao(template.schema_json, computed)}
  </table>
  {resumo_geral}

  {grafico_html}

  {secoes_clinicas_html}

  {texto_html}

  {sobre_profissional_html}

  {assinatura_html}

  <div class="rodape">
    <p>OBSERVAÇÃO: Este documento é gerado automaticamente com apoio de
    inteligência artificial a partir de dados informados pela profissional
    responsável e não substitui avaliação, diagnóstico ou laudo médico. A
    responsabilidade final pelo conteúdo é do profissional que assina o
    laudo.</p>
  </div>
</body>
</html>"""


