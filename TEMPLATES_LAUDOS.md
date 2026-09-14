# TEMPLATES_LAUDOS.md — Regras das escalas para seed inicial do sistema

Este arquivo complementa `SPEC.md` (seção 3, formato de `schema_json`) com
exemplos **prontos para cadastrar** no sistema, baseados nas escalas que
aparecem nos laudos-modelo da clínica (CARS, ATA, SNAP-IV e Portage/IPO).

Use estes exemplos como ponto de partida no Claude Code (ex.: seed inicial
do banco, ou arquivos fixture para testes) — mas a psicóloga deve revisar e
confirmar cada faixa de pontuação e cada campo antes de usar em produção.
Escalas clínicas padronizadas têm regras oficiais de aplicação e pontuação;
o ideal é validar este JSON com o manual/protocolo oficial de cada escala
antes do primeiro uso real.

---

## 1. Estrutura comum — o que toda escala precisa definir

Para transformar uma escala em um `schema_json` (SPEC.md, seção 3), a
psicóloga precisa informar, para cada tipo de laudo:

1. **Áreas/domínios avaliados** (ex.: comunicação, comportamento).
2. **Campos de cada área**: o que é perguntado, e o tipo de resposta
   (`scale` numérica, `boolean` sim/não, `select` com opções fixas).
3. **Peso de cada campo**, se algum contar mais que outro na pontuação.
4. **Como a pontuação total (ou por área) se transforma em uma
   classificação** (ex.: "Normal", "Leve-moderado", "Grave").
5. **Que tipo de gráfico** representa melhor o resultado (barras, radar, pizza).

Duas famílias de regra aparecem nos laudos de referência:

- **Soma + faixa de corte** (CARS, ATA, SNAP-IV): soma-se os pontos e
  compara-se contra faixas fixas.
- **Percentual por área comparado à idade** (Portage/IPO): não é uma soma
  simples — compara o desempenho do paciente com o esperado para a idade
  dele em cada área do desenvolvimento. Ver observação na seção 5.

---

## 2. CARS (Childhood Autism Rating Scale) — exemplo de `schema_json`

15 domínios comportamentais, cada um pontuado de **1 a 4** (quanto maior,
mais distante do esperado). O resultado é a soma dos 15 domínios.

```json
{
  "name": "Escala CARS",
  "areas": [
    { "key": "relacionamento_interpessoal", "label": "Relacionamento interpessoal", "fields": [ { "key": "score", "label": "Pontuação", "type": "scale", "min": 1, "max": 4, "weight": 1 } ] },
    { "key": "imitacao", "label": "Imitação", "fields": [ { "key": "score", "label": "Pontuação", "type": "scale", "min": 1, "max": 4, "weight": 1 } ] },
    { "key": "resposta_emocional", "label": "Resposta emocional", "fields": [ { "key": "score", "label": "Pontuação", "type": "scale", "min": 1, "max": 4, "weight": 1 } ] },
    { "key": "uso_corporal", "label": "Uso corporal", "fields": [ { "key": "score", "label": "Pontuação", "type": "scale", "min": 1, "max": 4, "weight": 1 } ] },
    { "key": "uso_de_objetos", "label": "Uso de objetos", "fields": [ { "key": "score", "label": "Pontuação", "type": "scale", "min": 1, "max": 4, "weight": 1 } ] },
    { "key": "adaptacao_a_mudancas", "label": "Adaptação a mudanças", "fields": [ { "key": "score", "label": "Pontuação", "type": "scale", "min": 1, "max": 4, "weight": 1 } ] },
    { "key": "resposta_visual", "label": "Uso do olhar / resposta visual", "fields": [ { "key": "score", "label": "Pontuação", "type": "scale", "min": 1, "max": 4, "weight": 1 } ] },
    { "key": "resposta_auditiva", "label": "Uso da audição / resposta auditiva", "fields": [ { "key": "score", "label": "Pontuação", "type": "scale", "min": 1, "max": 4, "weight": 1 } ] },
    { "key": "resposta_paladar_olfato_tato", "label": "Resposta e uso do paladar, olfato e tato", "fields": [ { "key": "score", "label": "Pontuação", "type": "scale", "min": 1, "max": 4, "weight": 1 } ] },
    { "key": "medo_ou_nervosismo", "label": "Medo ou nervosismo", "fields": [ { "key": "score", "label": "Pontuação", "type": "scale", "min": 1, "max": 4, "weight": 1 } ] },
    { "key": "comunicacao_verbal", "label": "Comunicação verbal", "fields": [ { "key": "score", "label": "Pontuação", "type": "scale", "min": 1, "max": 4, "weight": 1 } ] },
    { "key": "comunicacao_nao_verbal", "label": "Comunicação não verbal", "fields": [ { "key": "score", "label": "Pontuação", "type": "scale", "min": 1, "max": 4, "weight": 1 } ] },
    { "key": "nivel_de_atividade", "label": "Nível de atividade", "fields": [ { "key": "score", "label": "Pontuação", "type": "scale", "min": 1, "max": 4, "weight": 1 } ] },
    { "key": "consistencia_resposta_intelectual", "label": "Nível e consistência da resposta intelectual", "fields": [ { "key": "score", "label": "Pontuação", "type": "scale", "min": 1, "max": 4, "weight": 1 } ] },
    { "key": "impressao_geral", "label": "Impressão geral", "fields": [ { "key": "score", "label": "Pontuação", "type": "scale", "min": 1, "max": 4, "weight": 1 } ] }
  ],
  "classification_ranges": [
    { "label": "Normal", "min": 15, "max": 29.5 },
    { "label": "Autismo leve-moderado", "min": 30, "max": 36.5 },
    { "label": "Autismo grave", "min": 37, "max": 60 }
  ],
  "chart": { "type": "bar", "group_by": "areas" }
}
```

> A soma mínima possível é 15 (1 ponto × 15 áreas) e a máxima é 60 (4 × 15).
> Confirme essas faixas com o manual oficial da CARS antes de usar em
> produção — o exemplo acima replica as faixas citadas no laudo de
> referência, mas o manual completo pode detalhar meio-pontos (ex.: 2,5)
> que o tipo `scale` deve permitir.

---

## 3. ATA (Escala de Traços Autísticos) — exemplo de `schema_json`

22 itens (dificuldade na interação social, manipulação do ambiente,
resistência a mudanças, etc.), cada um pontuado numa faixa curta (ex.: 0 a
2 ou 0 a 3, conforme o manual oficial). A soma total é comparada a dois
limites.

```json
{
  "name": "Escala ATA",
  "areas": [
    { "key": "dificuldade_interacao_social", "label": "Dificuldade na interação social", "fields": [ { "key": "score", "label": "Pontuação", "type": "scale", "min": 0, "max": 2, "weight": 1 } ] },
    { "key": "manipulacao_do_ambiente", "label": "Manipulação do ambiente", "fields": [ { "key": "score", "label": "Pontuação", "type": "scale", "min": 0, "max": 2, "weight": 1 } ] },
    { "key": "resistencia_a_mudancas", "label": "Resistência a mudanças", "fields": [ { "key": "score", "label": "Pontuação", "type": "scale", "min": 0, "max": 2, "weight": 1 } ] }
    // ... repetir o mesmo padrão para os demais 19 itens da escala,
    // usando os nomes de domínio do manual oficial da ATA.
  ],
  "classification_ranges": [
    { "label": "Sem indicação de atraso", "min": 0, "max": 16 },
    { "label": "Atraso no desenvolvimento", "min": 16.01, "max": 20 },
    { "label": "Traços autísticos", "min": 20.01, "max": 66 }
  ],
  "chart": { "type": "bar", "group_by": "areas" }
}
```

> Os cortes reais são "acima de 16 pontos" e "acima de 20 pontos" — ajuste
> os limites exatos (`min`/`max`) com a psicóloga para refletir se o corte
> é inclusivo ou exclusivo. Complete a lista de 22 itens com os nomes
> oficiais do manual da ATA antes de cadastrar de verdade.

---

## 4. SNAP-IV — exemplo de `schema_json`

18 itens (9 de desatenção + 9 de hiperatividade/impulsividade), cada um
pontuado de 0 a 3 (`nem um pouco`, `só um pouco`, `bastante`, `demais`).
Aqui a classificação **não é uma soma única** — é uma contagem de quantos
itens de cada bloco foram marcados "bastante" ou "demais".

```json
{
  "name": "Escala SNAP-IV",
  "areas": [
    {
      "key": "desatencao",
      "label": "Desatenção (itens 1 a 9)",
      "fields": [
        { "key": "item_1", "label": "Item 1", "type": "select", "options": ["nem um pouco", "só um pouco", "bastante", "demais"], "weight": 1 }
        // ... item_2 até item_9, mesmo formato
      ]
    },
    {
      "key": "hiperatividade_impulsividade",
      "label": "Hiperatividade / Impulsividade (itens 10 a 18)",
      "fields": [
        { "key": "item_10", "label": "Item 10", "type": "select", "options": ["nem um pouco", "só um pouco", "bastante", "demais"], "weight": 1 }
        // ... item_11 até item_18, mesmo formato
      ]
    }
  ],
  "classification_rule": "count_threshold",
  "classification_ranges": [
    { "label": "Sem indicação de sintomas de desatenção", "area": "desatencao", "rule": "menos de 4 itens em 'bastante' ou 'demais'" },
    { "label": "Indicação de sintomas de desatenção", "area": "desatencao", "rule": "4 ou mais itens em 'bastante' ou 'demais'" },
    { "label": "Sem indicação de sintomas de hiperatividade", "area": "hiperatividade_impulsividade", "rule": "menos de 4 itens em 'bastante' ou 'demais'" },
    { "label": "Indicação de sintomas de hiperatividade", "area": "hiperatividade_impulsividade", "rule": "4 ou mais itens em 'bastante' ou 'demais'" }
  ],
  "chart": { "type": "bar", "group_by": "response_option" }
}
```

> **Atenção para quem for programar o motor de regras:** este caso não se
> encaixa no `classification_rule` padrão de "somar e comparar contra uma
> faixa" usado em CARS e ATA. É preciso um segundo tipo de regra —
> `count_threshold` — que conta quantos campos de uma área bateram em um
> valor específico (`"bastante"` ou `"demais"`) e compara contra uma
> quantidade mínima (aqui, 4). Adicione esse tipo de regra ao motor
> descrito em `SPEC.md` (seção 4) antes de cadastrar esta escala.

---

## 5. Portage / IPO (Inventário Portage Operacionalizado) — implementado por faixas etárias

**Atualização (motor de regras `age_equivalent_percentage` implementado):**
o inventário oficial completo (~580 habilidades, cada uma com a idade exata
em que é esperada) nunca chegou a ser fornecido pela clínica. Em vez de
deixar o Portage bloqueado esperando por ele, o motor de regras foi
implementado de forma **genérica por faixas etárias**: a psicóloga organiza
os itens que já tem, por área, em faixas (ex.: "0 a 24 meses", "24 a 48
meses") — cadastrando isso via a tela "Modelos de Laudo" (upload do
documento da escala + revisão do `schema_json` extraído por IA) ou editando
o JSON diretamente. Quanto mais faixas/itens ela cadastrar, mais preciso
fica o cálculo; não é necessário ter as ~580 habilidades de uma vez.

O Portage continua **não classificando por soma total**: para cada área do
desenvolvimento (Socialização, Linguagem, Autocuidados, Cognição, Motor), o
motor estima uma **idade de desenvolvimento** a partir de quais faixas
etárias a criança já domina, e compara com a idade cronológica dela
(percentual = idade de desenvolvimento ÷ idade cronológica × 100).

Cada item é marcado como `sim` (1,0), `as_vezes` (0,5) ou `nao` (0,2) —
configurável em `item_scoring`.

```json
{
  "name": "Inventário Portage Operacionalizado (IPO)",
  "rule_type": "age_equivalent_percentage",
  "item_scoring": { "sim": 1.0, "as_vezes": 0.5, "nao": 0.2 },
  "areas": [
    {
      "key": "socializacao",
      "label": "Socialização",
      "age_brackets": [
        {
          "label": "0 a 24 meses",
          "max_age_months": 24,
          "fields": [
            { "key": "sorri_para_pessoas_conhecidas", "label": "Sorri para pessoas conhecidas", "type": "select", "options": ["sim", "as_vezes", "nao"] }
          ]
        },
        {
          "label": "24 a 48 meses",
          "max_age_months": 48,
          "fields": [
            { "key": "brinca_cooperativamente_com_outras_criancas", "label": "Brinca cooperativamente com outras crianças", "type": "select", "options": ["sim", "as_vezes", "nao"] }
          ]
        }
      ]
    }
  ],
  "classification_ranges": [
    { "label": "Atraso significativo", "min": 0, "max": 69.9 },
    { "label": "Atraso leve", "min": 70, "max": 89.9 },
    { "label": "Adequado", "min": 90, "max": 200 }
  ],
  "chart": { "type": "bar", "group_by": "areas", "compare_to": "idade_cronologica" }
}
```

### Como o cálculo funciona

1. Para cada faixa etária de uma área, calcula-se a "taxa de acerto":
   soma de `item_scoring` das respostas ÷ número de itens da faixa.
2. A maior faixa com taxa de acerto ≥ 75% define a idade de desenvolvimento
   atingida por completo; a próxima faixa (a primeira não totalmente
   atingida) soma um crédito parcial interpolado, em vez de "tudo ou nada".
3. Idade de desenvolvimento ÷ idade cronológica do paciente na data da
   avaliação × 100 = percentual, comparado contra `classification_ranges`.

Ver `backend/app/rules_engine/age_equivalent_percentage.py` para a
implementação e `backend/app/rules_engine/fixtures/portage.json` para um
exemplo funcional (com só 2 áreas/2 faixas — ilustrativo, não o inventário
completo).

---

## 6. Resumo do que falta a psicóloga fornecer, por escala

| Escala | O que falta confirmar/fornecer |
|---|---|
| CARS | Confirmar se o manual usa meio-pontos (2,5, 3,5) e os textos oficiais de cada nível (1 a 4) por domínio. |
| ATA | Lista completa dos 22 itens com nome oficial e pontuação máxima de cada um (o exemplo trouxe só 3 de 22). |
| SNAP-IV | Confirmar o texto exato dos 18 itens (o manual costuma ser público, mas os textos completos não estavam nos documentos enviados). |
| Portage/IPO | O cálculo já funciona por faixas etárias (seção 5) — falta a psicóloga cadastrar os itens reais de cada área/faixa (o `portage.json` atual é só um exemplo com 2 áreas). Pode ser feito aos poucos, sem precisar do inventário completo de uma vez. |

## 7. Recomendação de prioridade para a Semana 2 (motor de regras)

1. Implementar primeiro o tipo `sum_threshold` (cobre CARS e ATA).
2. Implementar `count_threshold` (cobre SNAP-IV).
3. `age_equivalent_percentage` (Portage) — **implementado** (fora do
   cronograma original das 4 semanas, ver `ENTREGAS.md`) usando faixas
   etárias por área em vez do inventário oficial completo, que nunca
   chegou a ser fornecido.
