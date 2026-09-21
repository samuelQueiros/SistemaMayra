# SPEC.md — Especificação Técnica

Complementa o `CLAUDE.md`. Aqui está o detalhamento de dados, regras e API.

> **⚠️ Aviso de 2026-09-20 — leia antes de qualquer coisa:** o restante
> deste documento (seções 1-4) descreve o **motor de templates
> configuráveis original**, que deixou de ser o caminho principal do
> sistema (decisão do usuário — ver `CLAUDE.md` seção 1/9). Hoje o
> protocolo de avaliação é **fixo**, implementado em
> `frontend/public/formulario-novo-paciente.html` (HTML standalone), não
> em `schema_json` cadastrado pela psicóloga. As entidades/endpoints
> abaixo **continuam existindo no código** (não foram removidos) e o
> `rule_type` `"sum_threshold"/"count_threshold"/"age_equivalent_percentage"`
> ainda funciona para quem cadastrar um template manualmente via API — mas
> nenhuma tela do frontend chama mais isso. Ver seção 7 (nova) para a
> arquitetura atual, que é a que importa para trabalho novo.

---

## 1. Entidades principais

### `Psychologist` (psicólogo — usuário do sistema)
| Campo | Tipo | Observação |
|---|---|---|
| id | UUID | |
| name | string | |
| email | string | único, usado no login |
| password_hash | string | bcrypt/argon2 |
| created_at | datetime | |

### `Patient` (paciente)
| Campo | Tipo | Observação |
|---|---|---|
| id | UUID | |
| owner_id | UUID | FK → Psychologist |
| name | string | |
| birth_date | date | |
| notes | text | opcional, observações gerais |
| created_at | datetime | |

### `ReportTemplate` (modelo de laudo — legado, ver aviso no topo)
Representa um tipo de laudo/escala (ex.: CARS, ATA, SNAP-IV, avaliação de
funções executivas). Era a peça central do "motor de regras" original.
**Hoje só existe uma linha real em uso**, criada automaticamente
(`POST /api/templates/custom-form-avaliacao`, idempotente) com
`rule_type = "custom_form"` — um "porta-laudo" técnico para o protocolo
fixo do HTML standalone, sem pontuação nenhuma calculada pelo backend (ver
seção 7).

| Campo | Tipo | Observação |
|---|---|---|
| id | UUID | |
| owner_id | UUID | FK → Psychologist |
| name | string | ex.: "Escala CARS" |
| version | int | permite versionar o modelo sem quebrar laudos antigos |
| schema_json | JSON | ver formato completo na seção 3 |
| created_at | datetime | |

### `Report` (laudo gerado)
| Campo | Tipo | Observação |
|---|---|---|
| id | UUID | |
| patient_id | UUID | FK → Patient |
| template_id | UUID | FK → ReportTemplate |
| answers_json | JSON | respostas preenchidas pelo psicólogo no formulário |
| computed_json | JSON | resultado calculado pelo motor de regras (pontuações, classificação) |
| generated_text | text | texto descritivo gerado com apoio de IA |
| pdf_path | string | caminho/URL do PDF exportado |
| created_at | datetime | também serve como "data do atendimento" no histórico |

---

## 2. Endpoints da API (REST, prefixo `/api`)

### Autenticação
- `POST /api/auth/register` — cria conta do psicólogo
- `POST /api/auth/login` — retorna JWT
- `GET  /api/auth/me` — dados do psicólogo autenticado

### Pacientes
- `GET    /api/patients` — lista pacientes do psicólogo logado
- `POST   /api/patients` — cria paciente
- `GET    /api/patients/{id}` — detalhe do paciente
- `PUT    /api/patients/{id}` — edita
- `DELETE /api/patients/{id}` — remove

### Modelos de laudo (templates) — legado, ver aviso no topo
- `GET  /api/templates` — lista modelos cadastrados pelo psicólogo
- `POST /api/templates` — cadastra um novo modelo (`schema_json`)
- `GET  /api/templates/{id}` — detalhe do modelo
- `POST /api/templates/custom-form-avaliacao` — **em uso hoje.** Garante
  (cria se não existir) o `ReportTemplate` fixo `rule_type="custom_form"`
  usado pelo HTML standalone. Idempotente por psicóloga.

### Laudos / histórico
- `POST /api/patients/{id}/reports` — cria um laudo (recebe `template_id` +
  `answers`). Para `rule_type` legados, aplica o motor de regras e calcula
  `computed_json`; para `"custom_form"` (caminho atual), `computed_json`
  fica `{}` — o HTML standalone já calculou tudo sozinho.
- `GET  /api/patients/{id}/reports` — histórico de laudos do paciente
- `GET  /api/reports/{id}` — detalhe de um laudo
- `PUT  /api/reports/{id}/answers` — **novo (2026-09-20).** Autosave:
  substitui `answers_json` inteiro. É o que o HTML standalone chama a cada
  campo alterado (debounce ~1,2s), depois que o laudo já existe.
- `PUT  /api/reports/{id}/text` — substitui `generated_text`. No caminho
  atual, recebe o HTML já pronto do laudo (montado pelo próprio formulário
  standalone), não texto gerado por IA.
- `GET  /api/reports/{id}/pdf` — baixa o PDF gerado. Para
  `rule_type="custom_form"`, pega `generated_text` (HTML completo, com
  `<style>` embutido) e manda direto pro WeasyPrint (`services/pdf.py`),
  sem passar pelas tabelas de pontuação/gráfico Matplotlib do motor legado.

---

## 3. Formato do modelo de laudo (`schema_json`)

Isto é o que a psicóloga precisa encaminhar para cada novo tipo de laudo.
Pode ser preenchido por ela em um formulário de cadastro de modelo (dentro
do próprio sistema) ou enviado como JSON pronto.

```json
{
  "name": "Escala CARS",
  "areas": [
    {
      "key": "comunicacao",
      "label": "Comunicação",
      "fields": [
        {
          "key": "iniciativa_social",
          "label": "Iniciativa de interação social",
          "type": "scale",
          "min": 1,
          "max": 4,
          "weight": 1
        }
      ]
    }
  ],
  "classification_ranges": [
    { "label": "Normal", "min": 15, "max": 29.5 },
    { "label": "Leve-moderado", "min": 30, "max": 36.5 },
    { "label": "Grave", "min": 37, "max": 60 }
  ],
  "chart": {
    "type": "bar",
    "group_by": "areas"
  }
}
```

- `type` de campo suportado inicialmente: `scale` (numérico com min/max),
  `boolean`, `select` (opções fixas), `text`.
- `chart.type` suportado inicialmente: `bar`, `radar`, `pie`.
- O motor de regras soma/calcula conforme `weight`, compara o total (ou por
  área) contra `classification_ranges` e devolve a classificação.

## 4. Motor de regras — pseudocódigo

> **Atualização:** ao detalhar as escalas reais da clínica (ver
> `TEMPLATES_LAUDOS.md`), identificamos que nem toda escala se encaixa em
> "somar e comparar contra uma faixa". O motor de regras deve suportar ao
> menos três tipos de `rule_type`, escolhido por `schema_json.rule_type`:
>
> - `sum_threshold` (padrão, usado por CARS e ATA): soma os campos e
>   compara o total contra `classification_ranges`. É o pseudocódigo abaixo.
> - `count_threshold` (usado por SNAP-IV): conta quantos campos de uma
>   área atingiram um valor específico e compara contra uma quantidade
>   mínima.
> - `age_equivalent_percentage` (usado pelo Portage/IPO): calcula uma
>   "idade de desenvolvimento" por área a partir dos itens atingidos,
>   comparando com a idade cronológica do paciente.
>
> Implemente `sum_threshold` primeiro (Semana 2), depois `count_threshold`.
> Trate `age_equivalent_percentage` como funcionalidade avançada — ver
> `TEMPLATES_LAUDOS.md`, seção 7, para a ordem de prioridade recomendada.

```
function generate_report(template, answers):
    scores = {}
    for area in template.areas:
        area_score = sum(answers[field.key] * field.weight for field in area.fields)
        scores[area.key] = area_score

    total_score = sum(scores.values())
    classification = find_range(template.classification_ranges, total_score)

    chart_data = build_chart_data(template.chart, scores)
    ai_text = call_ai_service(template, answers, scores, classification)
    pdf = render_pdf(patient, template, scores, classification, chart_data, ai_text)

    return Report(
        answers_json=answers,
        computed_json={ "scores": scores, "total": total_score, "classification": classification },
        generated_text=ai_text,
        pdf_path=pdf.path,
    )
```

## 5. Integração com IA (texto assistido)

- Chamada feita **no backend** (nunca no frontend) para a API da Anthropic.
- Prompt enviado deve incluir: nome da escala, respostas marcadas, pontuações
  calculadas e classificação — e pedir um texto descritivo objetivo, no
  padrão clínico, **sem inventar dados que não estejam nas respostas**.
- O texto gerado é sempre revisável/editável pelo psicólogo antes da
  exportação final em PDF (nunca exportar automaticamente sem exibir para
  revisão).

## 6. Requisitos não funcionais

- **Deploy de um único serviço:** o FastAPI deve servir os arquivos
  estáticos do `frontend/dist` (via `StaticFiles`) além da API. Não criar
  dependência de um servidor Node em produção.
- Variáveis de ambiente (`.env`): `DATABASE_URL`, `JWT_SECRET`,
  `ANTHROPIC_API_KEY`, `ENV`.
- Todas as rotas de dados de pacientes exigem JWT válido **e** checam
  `owner_id` (um psicólogo não pode acessar pacientes de outro).
- Testes automatizados mínimos: motor de regras (cálculo e classificação) e
  autenticação/autorização.

---

## 7. Arquitetura atual: protocolo fixo (2026-09-20)

Substitui, na prática, as seções 3 e 4 como caminho principal (que
continuam documentadas acima só porque o código legado ainda existe — ver
aviso no topo do arquivo).

### O arquivo

`frontend/public/formulario-novo-paciente.html` — HTML/CSS/JS autocontido
(sem framework, sem bundler), cópia funcional e byte-a-byte fiel do
protótipo original da psicóloga (fonte intocada fora do repositório, em
`/home/samu/formpsico/.claude/formulario_prototipo_cliente.html`). Contém:

- Identificação, gestação/parto/desenvolvimento, escola, convivência
  social.
- Protocolos CARS, ATA, SNAP-IV, TOD, M-CHAT (condicionado a idade
  estimada ≤ 30 meses) e Portage/IPO (por faixa etária), cada um com sua
  própria lógica de pontuação em JavaScript puro.
- Motor de interpretação por casamento de palavras-chave sobre os campos
  de texto livre (estudo de caso, observações clínicas, queixas),
  associando comportamentos observados a critérios do DSM-5-TR.
- Cálculo de "probabilidades" heurísticas por hipótese diagnóstica (TEA,
  TDAH, TOD, DI, Transtorno de Aprendizagem, TPAC).
- `gerarRelatorio()`: monta o HTML final do laudo (identificação,
  anamnese, quadro de observações, gráfico de probabilidades via
  Chart.js, assinatura) dentro de `#relatorio`.

Nenhuma dessas ~897 linhas originais foi alterada. Toda a integração com o
sistema entra como um **segundo `<script>`, acrescentado no fim do
arquivo**, que usa as funções já globais do script original (`setValor`,
`valor`, `coletarDados`, `gerarRelatorio`) para ler/escrever dados e chamar
a API.

### O que o bootstrap faz

1. Lê `?paciente=<uuid>` da querystring (opcional) e `formpsico_token` do
   `localStorage` (mesma origem/chave que `frontend/src/api/client.ts` usa
   — o HTML roda dentro de um `<iframe>` do próprio app, mesma origem).
2. Se `paciente` veio, pré-carrega identificação via `GET
   /api/patients/{id}`.
3. Botão "Salvar No Sistema" (primeira vez): cria o paciente se necessário
   (`POST /api/patients`), garante o template fixo (`POST
   /api/templates/custom-form-avaliacao`), cria o laudo (`POST
   /api/patients/{id}/reports`, `answers` = `coletarDados()` — todos os
   campos do formulário), congela o gráfico de probabilidades como `<img>`
   (`canvas.toDataURL`, porque WeasyPrint não executa JS/Canvas) e salva o
   HTML final do laudo (`PUT /api/reports/{id}/text`).
4. **A partir daí**, qualquer campo alterado dispara (debounce ~1,2s) `PUT
   /api/reports/{id}/answers` sozinho — autosave real no banco, não só
   `localStorage`. O botão vira "Atualizar No Sistema".
5. Botão "Concluir E Ver Histórico" navega `window.top` (a janela real do
   app, não o iframe) para `/pacientes/{id}/historico`.

### Fotos

O formulário standalone embute fotos como base64 dentro de
`fotosPacienteDados` (mecanismo original, inalterado) — elas vão dentro de
`answers_json` e aparecem no laudo/PDF (`gerarFotosRelatorio()` original).
Além disso (2026-09-20), o bootstrap também envia cada foto para a galeria
oficial `/api/patients/{id}/photos` assim que o paciente existe no banco, e
recarrega as fotos já existentes na galeria quando o formulário abre para
um paciente com atendimento anterior. Remover uma foto no formulário
também apaga da galeria, se já tinha sido enviada. Ver `CLAUDE.md` seção 9
para os detalhes de implementação (funções `enviarFotosNovasParaGaleria`,
`carregarFotosDaGaleria`, `interceptarRemocaoDeFoto`).
