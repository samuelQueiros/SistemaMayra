# PROMPTS.md — Roteiro de prompts para o assistente

Copie e cole os prompts abaixo, um de cada vez, na ordem. Espere o assistente
Code terminar e revise antes de colar o próximo. Eles seguem o mesmo
cronograma de 4 semanas da proposta.

Antes de começar: coloque `docs/ARQUITETURA.md`, `SPEC.md`, `TEMPLATES_LAUDOS.md` e
`ENTREGAS.md` na raiz do projeto — o assistente os lê automaticamente
como contexto.

**Depois de cada prompt concluído, o assistente deve atualizar
`ENTREGAS.md` sozinho** (isso já está instruído em `docs/ARQUITETURA.md`, seção 8).
Se ele não fizer isso, cole este lembrete antes de seguir para o próximo
prompt:
```
Antes de continuar, atualize o ENTREGAS.md: marque este item como
concluído no checklist e adicione uma entrada detalhada descrevendo o que
foi feito, os arquivos alterados e como testar.
```

---

## Prompt 0 — Kickoff (rodar uma vez, antes de tudo)

```
Leia docs/ARQUITETURA.md e SPEC.md nesta pasta. Antes de escrever qualquer código,
me dê um resumo em poucas linhas confirmando que entendeu:
1. A arquitetura (backend único em Python servindo a API e o frontend estático)
2. O modelo de dados principal
3. Como funciona o motor de regras baseado em templates fornecidos pela psicóloga

Não crie nenhum arquivo ainda, só confirme o entendimento.
```

---

## Semana 1 — Levantamento e Design

### Prompt 1.1 — Estrutura inicial do projeto
```
Crie a estrutura inicial do projeto conforme a seção 3 do SPEC.md:
- /backend com FastAPI, SQLAlchemy, Alembic e Pydantic configurados
- /frontend com React + Vite + TypeScript
- .env.example com as variáveis descritas no SPEC.md (seção 6)
- README.md raiz explicando como rodar backend e frontend em modo dev

Não implemente lógica de negócio ainda — só o esqueleto rodando (uma rota
GET /api/health no backend, uma página inicial simples no frontend).
```

### Prompt 1.2 — Modelagem do banco de dados
```
Implemente os modelos SQLAlchemy para Psychologist, Patient, ReportTemplate
e Report, conforme a seção 1 do SPEC.md. Crie a migration inicial com
Alembic. Use UUID como chave primária em todas as tabelas.
```

### Prompt 1.3 — Protótipo de telas (sem lógica ainda)
```
Crie no frontend as páginas (sem funcionalidade real ainda, só layout e
navegação): Login, Dashboard (lista de pacientes), Novo Atendimento
(formulário), Histórico do Paciente. Use componentes simples e limpos,
sem se preocupar com integração com a API por enquanto.
```

---

## Semana 2 — Backend e Motor de Regras

### Prompt 2.1 — Autenticação
```
Implemente autenticação JWT no backend: registro e login de psicólogo
(POST /api/auth/register, POST /api/auth/login, GET /api/auth/me),
conforme a seção 2 do SPEC.md. Senha com hash (bcrypt). Adicione um
dependency do FastAPI que valida o token e injeta o psicólogo autenticado
nas rotas protegidas.
```

### Prompt 2.2 — CRUD de pacientes e templates
```
Implemente os endpoints de pacientes e de modelos de laudo (templates)
descritos na seção 2 do SPEC.md. Todas as rotas devem exigir autenticação
e filtrar sempre por owner_id (um psicólogo só vê os próprios registros).
Adicione validação Pydantic completa para o schema_json do template,
seguindo o formato da seção 3 do SPEC.md.
```

### Prompt 2.3 — Motor de regras
```
Implemente o motor de regras em /backend/app/rules_engine, seguindo o
pseudocódigo da seção 4 do SPEC.md: cálculo de pontuação por área,
pontuação total, e classificação a partir de classification_ranges.
Escreva testes automatizados cobrindo: pontuação correta, classificação
em cada faixa, e um caso de borda (valor exatamente no limite de uma faixa).
```

### Prompt 2.3b — Tipos de regra adicionais (escalas reais da clínica)
```
Leia TEMPLATES_LAUDOS.md. Estenda o motor de regras para suportar os
tipos de rule_type descritos lá: sum_threshold (já implementado no prompt
anterior), count_threshold (usado pelo SNAP-IV — conta quantos campos de
uma área bateram em um valor específico, ex. "bastante" ou "demais", e
compara contra uma quantidade mínima) e um stub para
age_equivalent_percentage (Portage/IPO) que pode lançar
NotImplementedError por enquanto. Cadastre os templates de CARS, ATA e
SNAP-IV do TEMPLATES_LAUDOS.md como seed de dados (fixtures ou script de
seed) para facilitar os testes das próximas semanas. Escreva testes para
o count_threshold cobrindo o caso "exatamente 4 itens em bastante/demais".
```

### Prompt 2.4 — Endpoint de geração de laudo (sem IA/PDF ainda)
```
Implemente POST /api/patients/{id}/reports: recebe template_id e answers,
usa o motor de regras da Semana 2 para calcular scores e classification,
salva o Report no banco e retorna o resultado em JSON. Ainda não gere PDF
nem texto de IA — isso vem no próximo prompt.
```

---

## Semana 3 — Frontend e Integração

### Prompt 3.1 — Integração do formulário com a API
```
Conecte a página "Novo Atendimento" do frontend à API: buscar templates
disponíveis, renderizar o formulário dinamicamente a partir do schema_json
do template escolhido (campos do tipo scale, boolean, select e text,
conforme SPEC.md seção 3), enviar as respostas para
POST /api/patients/{id}/reports e mostrar o resultado calculado.
```

### Prompt 3.2 — Histórico e dashboard
```
Implemente a listagem de pacientes no Dashboard e o histórico de laudos por
paciente, consumindo GET /api/patients e GET /api/patients/{id}/reports.
Mostre data, template usado e classificação de cada laudo no histórico.
```

### Prompt 3.3 — Gráficos automáticos
```
Adicione a geração de gráficos no frontend usando Chart.js, a partir de
computed_json.scores de cada laudo, respeitando o chart.type definido no
template (bar, radar ou pie), conforme a seção 3 do SPEC.md.
```

### Prompt 3.4 — Build único servido pelo backend
```
Configure o build de produção do frontend (npm run build) e ajuste o
main.py do FastAPI para servir os arquivos de /frontend/dist via
StaticFiles, conforme a seção 6 do SPEC.md (um único serviço em produção).
Teste rodando só o backend e acessando o frontend pela mesma porta da API.
```

---

## Semana 4 — Testes e Entrega

### Prompt 4.1 — Integração com IA para o texto do laudo
```
Implemente a chamada à API da Anthropic no backend (nunca no frontend),
conforme a seção 5 do SPEC.md: monta um prompt com a escala, respostas,
scores e classification, e retorna um texto descritivo objetivo. Salve o
texto em generated_text no Report. Exiba esse texto no frontend como
editável antes da exportação final.
```

### Prompt 4.2 — Exportação em PDF
```
Implemente a geração de PDF do laudo (WeasyPrint) incluindo: dados do
paciente, tabela de pontuações, gráfico (renderizado com Matplotlib para o
PDF), classificação e o texto gerado por IA (já revisado). Salve o arquivo
e implemente GET /api/reports/{id}/pdf para download.
```

### Prompt 4.3 — Testes finais e revisão de segurança
```
Revise todas as rotas que retornam dados de pacientes ou laudos e confirme
que exigem autenticação E checam owner_id (seção 5 do docs/ARQUITETURA.md). Rode
todos os testes automatizados. Liste qualquer ponto de segurança ou dado
sensível que ficou exposto sem proteção.
```

### Prompt 4.4 — Preparar para implantação
```
Prepare o projeto para deploy: Dockerfile único para o backend (que já
serve o frontend), instruções de variáveis de ambiente necessárias em
produção, e um checklist de implantação (migrations, build do frontend,
variáveis de ambiente, HTTPS). Não faça o deploy, apenas deixe tudo pronto.
```

---

## Dicas gerais de uso

- Se o assistente sugerir mudar a arquitetura (ex.: separar frontend em
  outro serviço Node), isso está fora do que foi combinado — recuse ou
  pergunte antes de aceitar.
- Sempre que cadastrar um novo tipo de laudo, valide o `schema_json` no
  formato da seção 3 do `SPEC.md` antes de salvar.
- Depois de cada prompt, rode o projeto localmente e confira visualmente
  antes de seguir para o próximo.
- Abra o `ENTREGAS.md` de vez em quando para acompanhar o andamento — é o
  arquivo pensado para você (ou a psicóloga) ler sem precisar entender
  código.
