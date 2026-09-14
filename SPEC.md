# SPEC.md — Especificação Técnica

Complementa o `CLAUDE.md`. Aqui está o detalhamento de dados, regras e API.

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

### `ReportTemplate` (modelo de laudo — **fornecido pelo psicólogo**)
Representa um tipo de laudo/escala (ex.: CARS, ATA, SNAP-IV, avaliação de
funções executivas). É a peça central do "motor de regras".

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

### Modelos de laudo (templates)
- `GET  /api/templates` — lista modelos cadastrados pelo psicólogo
- `POST /api/templates` — cadastra um novo modelo (`schema_json`)
- `GET  /api/templates/{id}` — detalhe do modelo

### Laudos / histórico
- `POST /api/patients/{id}/reports` — gera um novo laudo
  (recebe `template_id` + `answers`, aplica o motor de regras, chama a IA
  para o texto, gera gráfico e PDF, salva e retorna o laudo)
- `GET  /api/patients/{id}/reports` — histórico de laudos do paciente
- `GET  /api/reports/{id}` — detalhe de um laudo
- `GET  /api/reports/{id}/pdf` — baixa o PDF gerado

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
