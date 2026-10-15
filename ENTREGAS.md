# ENTREGAS.md — Registro de entregas prontas

**Este arquivo é atualizado pelo Claude Code, não pela psicóloga.** Sempre
que uma funcionalidade dos `PROMPTS.md` for concluída, adicione (ou marque)
uma entrada aqui **antes de seguir para o próximo prompt**. Não apague
entradas antigas — isso é o histórico do que já foi construído.

## Como preencher cada entrega

```
## [Semana X] Nome da funcionalidade
- **Status:** ✅ Pronto | 🟡 Parcial | ⬜ Pendente
- **Data:**
- **Prompt de origem:** (ex.: Prompt 2.3 do PROMPTS.md)
- **O que foi feito:** descrição em linguagem simples, sem jargão técnico
  — a psicóloga também vai ler isto.
- **Arquivos criados/alterados:** lista de arquivos principais
- **Como testar/ver funcionando:** passo a passo curto
- **Pendências/observações:** o que ficou faltando ou precisa de decisão
```

---

## Checklist geral (marque conforme for concluindo)

### Semana 1 — Levantamento e Design
- [x] Estrutura inicial do projeto (Prompt 1.1)
- [x] Modelagem do banco de dados (Prompt 1.2)
- [x] Protótipo de telas (Prompt 1.3)

### Semana 2 — Backend e Motor de Regras
- [x] Autenticação (Prompt 2.1)
- [x] CRUD de pacientes e templates (Prompt 2.2)
- [x] Motor de regras — sum_threshold (Prompt 2.3)
- [x] Motor de regras — count_threshold e seed CARS/ATA/SNAP-IV (Prompt 2.3b)
- [x] Endpoint de geração de laudo, sem IA/PDF (Prompt 2.4)

### Semana 3 — Frontend e Integração
- [x] Formulário dinâmico integrado à API (Prompt 3.1)
- [x] Histórico e dashboard (Prompt 3.2)
- [x] Gráficos automáticos (Prompt 3.3)
- [x] Build único servido pelo backend (Prompt 3.4)

### Semana 4 — Testes e Entrega
- [x] IA gerando o texto do laudo (Prompt 4.1)
- [x] Exportação em PDF (Prompt 4.2)
- [x] Testes finais e revisão de segurança (Prompt 4.3)
- [x] Preparação para implantação (Prompt 4.4)

---

## Registro detalhado das entregas

> As entradas abaixo são adicionadas pelo Claude Code, uma por
> funcionalidade concluída, na ordem em que forem sendo feitas.

## [Semana 1] Estrutura inicial do projeto
- **Status:** ✅ Pronto
- **Data:** 2026-09-12
- **Prompt de origem:** Prompt 1.1 do PROMPTS.md
- **O que foi feito:** Criado o esqueleto do projeto com backend em Python
  (FastAPI) e frontend em React + Vite + TypeScript, do jeito combinado no
  CLAUDE.md (um único serviço em produção). O backend já sobe com uma rota
  de teste (`/api/health`) e, quando o frontend está compilado, ele mesmo
  serve as telas do site na mesma porta — não existe servidor Node rodando
  em produção. Também foi criado o arquivo `.env.example` com as variáveis
  que o sistema vai precisar (banco de dados, chave de login e chave de IA)
  e um `README.md` explicando como ligar tudo. Nenhuma regra de negócio foi
  implementada ainda, só a base para começar a construir em cima.
- **Arquivos criados/alterados:**
  - `backend/app/main.py`, `backend/app/core/config.py`,
    `backend/requirements.txt`
  - `frontend/` (projeto Vite + React + TypeScript completo, com
    `src/App.tsx`, `src/api/client.ts`, `vite.config.ts` ajustado para
    redirecionar `/api` ao backend em desenvolvimento)
  - `.env.example`, `.gitignore`, `README.md`
- **Como testar/ver funcionando:**
  1. Backend: `cd backend && python3 -m venv .venv && source .venv/bin/activate
     && pip install -r requirements.txt && uvicorn app.main:app --reload` —
     depois abrir `http://localhost:8000/api/health` e ver `{"status":"ok"}`.
  2. Frontend em desenvolvimento (com o backend já ligado):
     `cd frontend && npm install && npm run dev` — abrir
     `http://localhost:5173` e ver a página inicial com o status da API.
  3. Modo produção (um serviço só): `cd frontend && npm run build`, depois
     `cd backend && uvicorn app.main:app --port 8000` e abrir
     `http://localhost:8000` — a mesma porta serve o site e a API.
- **Pendências/observações:** Nenhuma regra de negócio, banco de dados ou
  autenticação ainda — isso é o próximo passo (Prompt 1.2: modelagem do
  banco de dados). O material de referência enviado pela psicóloga
  (protótipo HTML e exemplos de laudo) foi organizado em
  `referencia_cliente/` para consulta durante o desenvolvimento das próximas
  etapas, mas não faz parte do sistema novo.

## [Semana 1] Modelagem do banco de dados
- **Status:** ✅ Pronto
- **Data:** 2026-09-12
- **Prompt de origem:** Prompt 1.2 do PROMPTS.md
- **O que foi feito:** Criadas as quatro tabelas principais do sistema,
  exatamente como descrito no SPEC.md seção 1: `Psychologist` (a conta da
  psicóloga que faz login), `Patient` (os pacientes, sempre amarrados a uma
  psicóloga dona), `ReportTemplate` (os modelos de laudo/escala, como
  CARS/ATA/SNAP-IV, guardados como um "JSON" flexível para não precisar
  mexer no código toda vez que aparecer uma escala nova) e `Report` (cada
  laudo gerado, com as respostas preenchidas, o resultado calculado, o
  texto e o caminho do PDF). Todas as tabelas usam um código único (UUID)
  como identificador, como pedido no SPEC.md. Também foi criada e testada a
  migration inicial do banco (Alembic), que cria essas tabelas do zero.
- **Arquivos criados/alterados:**
  - `backend/app/models/base.py`, `psychologist.py`, `patient.py`,
    `report_template.py`, `report.py`, `__init__.py`
  - `backend/app/core/database.py` (conexão com o banco e sessão)
  - `backend/alembic/env.py` (ajustado para ler a URL do banco do `.env` e
    reconhecer os modelos automaticamente)
  - `backend/alembic/versions/9715ace3d440_modelos_iniciais_*.py` (migration
    inicial)
  - `backend/requirements.txt` (versões de SQLAlchemy e psycopg ajustadas
    para funcionar no Python instalado nesta máquina — trocado
    `psycopg2-binary` por `psycopg[binary]`, que é o sucessor mais novo e
    tem o mesmo papel: conversar com o Postgres)
- **Como testar/ver funcionando:**
  1. `cd backend && source .venv/bin/activate && alembic upgrade head` —
     cria o arquivo `dev.db` (SQLite) com as 4 tabelas.
  2. Conferir as tabelas: abrir `dev.db` em qualquer visualizador de SQLite
     (ex.: extensão "SQLite Viewer" do VS Code) e ver `psychologists`,
     `patients`, `report_templates`, `reports`.
  3. Foi testado manualmente que dá para criar uma psicóloga e um paciente
     vinculado a ela e que o identificador único (UUID) é gerado sozinho.
- **Pendências/observações:** Ainda não existe nenhuma rota de API usando
  essas tabelas (isso é autenticação e CRUD, Prompts 2.1 e 2.2). Em
  produção o banco será Postgres (`DATABASE_URL` no `.env`); em
  desenvolvimento local, por padrão, usamos SQLite para simplificar,
  conforme autorizado no CLAUDE.md seção 2.

## [Semana 1] Protótipo de telas
- **Status:** ✅ Pronto
- **Data:** 2026-09-12
- **Prompt de origem:** Prompt 1.3 do PROMPTS.md
- **O que foi feito:** Criadas as quatro telas principais do sistema, só
  com layout e navegação entre elas (sem ligação com o banco de dados
  ainda): Login, Dashboard (lista de pacientes), Novo Atendimento
  (formulário) e Histórico do Paciente. As telas usam dados de exemplo só
  para mostrar como vai ficar — os números reais (pacientes, laudos)
  entram depois, junto com o login de verdade. Também foi resolvido um
  detalhe técnico importante: como o navegador entende os "endereços" das
  telas (ex.: `/dashboard`), o backend agora sabe devolver a página certa
  mesmo se alguém recarregar o navegador direto numa dessas telas, sem
  quebrar a API.
- **Arquivos criados/alterados:**
  - `frontend/src/pages/Login.tsx`, `Dashboard.tsx`, `NovoAtendimento.tsx`,
    `HistoricoPaciente.tsx` (+ respectivos `.module.css`)
  - `frontend/src/components/Layout.tsx` (menu de navegação compartilhado)
  - `frontend/src/App.tsx` (rotas com `react-router-dom`)
  - `frontend/index.html` (título da aba do navegador)
  - `backend/app/main.py` (ajustado para servir corretamente qualquer tela
    do frontend, mesmo recarregando a página direto numa rota interna)
- **Como testar/ver funcionando:**
  1. Modo desenvolvimento: `cd frontend && npm run dev`, abrir
     `http://localhost:5173`. A tela de Login aparece; ao "entrar" (sem
     senha real ainda), vai para o Dashboard com pacientes de exemplo; o
     menu no topo leva a "Novo Atendimento"; clicar em "Ver histórico" de
     um paciente mostra os laudos de exemplo dele.
  2. Modo produção (um serviço só): `cd frontend && npm run build`, depois
     `cd ../backend && uvicorn app.main:app --port 8000` e testar as
     mesmas telas em `http://localhost:8000` — inclusive recarregando a
     página direto em `http://localhost:8000/dashboard`, que deve
     continuar funcionando (antes desse ajuste, dava erro).
- **Pendências/observações:** Login, listagem de pacientes e histórico
  ainda são só de mentirinha (dados fixos na tela) — a integração real com
  a API é dos Prompts 2.1 (login), 3.1 (formulário) e 3.2
  (dashboard/histórico). Fim da Semana 1 do cronograma.

## [Semana 2] Autenticação
- **Status:** ✅ Pronto
- **Data:** 2026-09-12
- **Prompt de origem:** Prompt 2.1 do PROMPTS.md
- **O que foi feito:** Implementado o login de verdade no backend: a
  psicóloga se cadastra com nome, e-mail e senha (`POST /api/auth/register`),
  faz login com e-mail e senha (`POST /api/auth/login`) e recebe um "crachá
  digital" (token JWT) que prova quem ela é nas próximas requisições
  (`GET /api/auth/me`). A senha nunca é guardada em texto puro — é
  transformada com bcrypt antes de ir para o banco, exatamente como pede o
  CLAUDE.md seção 5. Também foi criada a trava (`dependency`) que qualquer
  rota futura vai usar para exigir login antes de mostrar dados de
  pacientes/laudos.
- **Arquivos criados/alterados:**
  - `backend/app/core/security.py` (hash de senha com `bcrypt` e
    criação/validação do token JWT)
  - `backend/app/schemas/auth.py` (formato de entrada/saída dos dados de
    cadastro, login e token)
  - `backend/app/api/auth.py` (rotas `/api/auth/register`, `/login`, `/me`)
  - `backend/app/api/deps.py` (função que qualquer rota protegida vai usar
    para descobrir "quem está logado")
  - `backend/app/main.py` (rotas de autenticação ligadas ao sistema)
  - `backend/tests/` (7 testes automatizados cobrindo cadastro, e-mail
    duplicado, login certo/errado, e acesso com/sem token)
- **Como testar/ver funcionando:**
  1. Rodar os testes automáticos: `cd backend && source .venv/bin/activate
     && pip install -r requirements.txt && python -m pytest tests/ -v` —
     devem passar 7 de 7.
  2. Testar manualmente: subir o backend (`uvicorn app.main:app --reload`)
     e usar a documentação automática em `http://localhost:8000/docs` para
     experimentar `POST /api/auth/register`, depois `POST /api/auth/login`
     (copiar o `access_token` da resposta) e por fim `GET /api/auth/me`
     colando o token no botão "Authorize" da página.
- **Pendências/observações:** Um detalhe técnico: a biblioteca que o
  SPEC.md sugeria para hash de senha (`passlib`) está com um problema de
  compatibilidade conhecido com versões mais novas do `bcrypt` — trocamos
  por usar a biblioteca `bcrypt` diretamente, que faz a mesma função (hash
  seguro de senha) e é ativamente mantida; não muda nada para quem usa o
  sistema. A tela de Login do frontend (Prompt 1.3) ainda não fala com essa
  API de verdade — essa ligação entra no Prompt 3.1/3.2, junto com o resto
  da integração do frontend.

## [Semana 2] CRUD de pacientes e templates
- **Status:** ✅ Pronto
- **Data:** 2026-09-12
- **Prompt de origem:** Prompt 2.2 do PROMPTS.md
- **O que foi feito:** Criadas as rotas para cadastrar/listar/editar/excluir
  pacientes (`/api/patients`) e para cadastrar/listar/consultar modelos de
  laudo (`/api/templates`). As duas seguem a mesma regra de segurança do
  CLAUDE.md seção 5: exigem login e cada psicóloga só vê os próprios
  pacientes e modelos — se a psicóloga B tentar acessar um paciente da
  psicóloga A pelo número dele, o sistema responde "não encontrado" (não
  entrega nem confirma que existe). Também foi criada uma conferência
  rigorosa do "molde" de cada modelo de laudo (`schema_json`, formato do
  SPEC.md seção 3): por exemplo, um campo do tipo escala numérica precisa
  ter mínimo e máximo definidos, um campo de múltipla escolha precisa ter
  as opções listadas, e as faixas de classificação (Normal / Leve-moderado
  / Grave, etc.) precisam fazer sentido matematicamente. Um modelo malformado
  é recusado com uma mensagem explicando o que falta corrigir, antes mesmo
  de chegar a ser salvo.
- **Arquivos criados/alterados:**
  - `backend/app/schemas/patient.py`, `backend/app/schemas/report_template.py`
    (validação completa do `schema_json`)
  - `backend/app/api/patients.py`, `backend/app/api/templates.py`
  - `backend/app/main.py` (rotas ligadas ao sistema)
  - `backend/tests/test_patients.py`, `backend/tests/test_templates.py`,
    `backend/tests/helpers.py` (10 novos testes: CRUD, isolamento entre
    psicólogas diferentes, e recusa de modelos de laudo malformados)
- **Como testar/ver funcionando:**
  1. `cd backend && source .venv/bin/activate && python -m pytest tests/ -v`
     — devem passar 17 de 17 testes (7 de autenticação + 10 novos).
  2. Manualmente pelo `http://localhost:8000/docs`: fazer login para pegar
     o token, "Authorize", depois testar `POST /api/patients` e
     `POST /api/templates` (dá pra usar o exemplo de CARS do
     `TEMPLATES_LAUDOS.md` seção 2 como corpo da requisição).
- **Pendências/observações:** O `schema_json` validado aqui cobre o formato
  documentado no SPEC.md seção 3 (`rule_type` padrão `sum_threshold`, que
  também serve para o `count_threshold` do SNAP-IV, já que a estrutura de
  áreas/campos é a mesma). O formato especial do Portage/IPO
  (`age_equivalent_percentage`, que usa "idade equivalente" em vez de
  soma/contagem) foi deixado propositalmente flexível — ele só vai ganhar
  validação e cálculo completos no Prompt 2.3b, junto com o motor de regras,
  conforme a prioridade combinada em `TEMPLATES_LAUDOS.md` seção 7. Ainda
  não existe endpoint para gerar o laudo em si (isso é o motor de regras,
  Prompt 2.3, e depois o endpoint de geração, Prompt 2.4).

## [Semana 2] Motor de regras — sum_threshold
- **Status:** ✅ Pronto
- **Data:** 2026-09-12
- **Prompt de origem:** Prompt 2.3 do PROMPTS.md
- **O que foi feito:** Criado o "cérebro" que calcula o resultado de uma
  escala como CARS ou ATA: soma a pontuação de cada área (respeitando o
  peso de cada pergunta, quando algum vale mais que outro), soma tudo, e
  descobre em qual faixa de classificação (ex.: "Normal", "Leve-moderado",
  "Grave") aquele total se encaixa. O código já está pronto para, no
  futuro, reconhecer outros tipos de escala (contagem de itens, idade de
  desenvolvimento) sem precisar mexer no que já funciona — por enquanto,
  se alguém tentar usar um tipo de escala ainda não implementado, o sistema
  avisa claramente em vez de dar um resultado errado. Um detalhe técnico
  importante decidido aqui: como escalas como a CARS repetem o mesmo nome
  de pergunta ("Pontuação") em todas as áreas, as respostas do formulário
  vão precisar chegar organizadas por área (não tudo misturado numa lista
  só), senão o valor de uma área substituiria o de outra.
- **Arquivos criados/alterados:**
  - `backend/app/rules_engine/sum_threshold.py` (cálculo em si)
  - `backend/app/rules_engine/engine.py` (escolhe qual regra usar, olhando
    o tipo de escala do modelo cadastrado)
  - `backend/app/rules_engine/exceptions.py` (erro claro quando faltam
    respostas ou uma resposta não faz sentido, em vez de o sistema quebrar)
  - `backend/tests/test_rules_engine.py` (14 testes: soma com peso,
    classificação certa em cada faixa — incluindo os valores exatamente na
    linha entre duas faixas —, e os erros esperados)
- **Como testar/ver funcionando:**
  `cd backend && source .venv/bin/activate && python -m pytest tests/ -v`
  — devem passar 31 de 31 testes no total do projeto até aqui.
- **Pendências/observações:** Só o `sum_threshold` (CARS/ATA) está
  implementado de verdade. `count_threshold` (SNAP-IV) e
  `age_equivalent_percentage` (Portage) hoje avisam "ainda não
  implementado" em vez de dar um resultado errado — isso é o próximo passo
  (Prompt 2.3b). Também ainda não existe uma rota de API que use esse
  motor de regras (isso é o Prompt 2.4).

## [Semana 2] Motor de regras — count_threshold e seed CARS/ATA/SNAP-IV
- **Status:** ✅ Pronto
- **Data:** 2026-09-12
- **Prompt de origem:** Prompt 2.3b do PROMPTS.md
- **O que foi feito:** Implementado o segundo tipo de cálculo do motor de
  regras: `count_threshold`, usado pelo SNAP-IV. Diferente da CARS/ATA (que
  somam pontos e comparam contra uma única faixa), aqui o sistema conta,
  para cada bloco de perguntas (ex.: "Desatenção" e
  "Hiperatividade/Impulsividade"), quantas respostas caíram em "bastante"
  ou "demais" — e cada bloco recebe sua própria classificação
  independente (é possível, por exemplo, ter indicativo de desatenção sem
  ter indicativo de hiperatividade). O terceiro tipo (`age_equivalent_percentage`,
  usado pelo Portage) continua propositalmente "ainda não implementado",
  como combinado — é o mais trabalhoso dos três e fica para depois, se o
  prazo permitir (ver `TEMPLATES_LAUDOS.md` seção 7).
  Também foram cadastrados, prontos para uso e teste, os três modelos de
  laudo reais da clínica: **CARS** (completo, 15 áreas), **ATA**
  (incompleto de propósito — só 3 dos 22 itens oficiais estavam
  disponíveis nos documentos enviados) e **SNAP-IV** (completo, 18 itens).
- **Arquivos criados/alterados:**
  - `backend/app/rules_engine/count_threshold.py` (cálculo por contagem)
  - `backend/app/rules_engine/engine.py` (agora também reconhece
    `count_threshold`)
  - `backend/app/schemas/report_template.py` (validação Pydantic estendida
    para aceitar o formato do `count_threshold`: `target_values` e faixas
    por área com quantidade mínima)
  - `backend/app/rules_engine/fixtures/cars.json`, `ata.json`,
    `snap_iv.json` (os três modelos prontos, no formato `schema_json`)
  - `backend/app/seed_templates.py` (script para cadastrar esses três
    modelos para uma psicóloga já registrada no sistema)
  - `backend/tests/test_rules_engine_count_threshold.py` (7 testes,
    incluindo o caso pedido: exatamente 4 itens em "bastante"/"demais")
  - `backend/tests/test_seed_fixtures.py` (4 testes que conferem se os
    três modelos reais estão bem formados e calculam certo)
- **Como testar/ver funcionando:**
  1. `cd backend && source .venv/bin/activate && python -m pytest tests/ -v`
     — devem passar 42 de 42 testes.
  2. Para ver os modelos cadastrados de verdade: registrar uma psicóloga
     (`POST /api/auth/register`) e depois rodar
     `python -m app.seed_templates <email-cadastrado>` — os três modelos
     aparecem em `GET /api/templates` (com o token de login).
- **Pendências/observações:**
  - **A ATA está incompleta** — falta a psicóloga confirmar os nomes
    oficiais e a pontuação máxima dos 19 itens restantes (de 22 no total).
    O arquivo `ata.json` está claramente marcado como incompleto no
    próprio nome do template, para não ser confundido com uma versão
    pronta para uso clínico real.
  - `age_equivalent_percentage` (Portage) continua como
    "ainda não implementado" — decisão consciente de prioridade, não uma
    pendência esquecida.
  - Ainda não existe uma rota de API que gere um laudo de verdade usando
    esse motor de regras — isso é o Prompt 2.4, o próximo passo.

## [Semana 2] Endpoint de geração de laudo (sem IA/PDF ainda)
- **Status:** ✅ Pronto
- **Data:** 2026-09-12
- **Prompt de origem:** Prompt 2.4 do PROMPTS.md
- **O que foi feito:** Criada a rota que efetivamente "gera o laudo":
  `POST /api/patients/{id}/reports`. A psicóloga manda o modelo escolhido
  (ex.: CARS) e as respostas preenchidas; o sistema confere se o paciente e
  o modelo são realmente dela, roda o motor de regras (Semana 2, Prompts
  2.3/2.3b) para calcular a pontuação e a classificação, salva tudo no
  histórico do paciente e devolve o resultado. Também foram criadas as
  rotas para consultar o histórico de laudos de um paciente e o detalhe de
  um laudo específico — sempre checando se quem está pedindo é a dona
  daquele paciente/laudo. Testado de ponta a ponta com o modelo real da
  CARS: um conjunto de respostas "2 em tudo" deu pontuação total 30 e
  classificação "Autismo leve-moderado" — batendo com a faixa esperada.
  Ainda não tem texto de IA nem PDF (isso é a Semana 4); por enquanto o
  laudo fica só com os números calculados.
- **Arquivos criados/alterados:**
  - `backend/app/schemas/report.py`
  - `backend/app/api/reports.py` (`POST /api/patients/{id}/reports`,
    `GET /api/patients/{id}/reports`, `GET /api/reports/{id}`)
  - `backend/app/api/patients.py` (função de checar dono do paciente
    reaproveitada pela rota de laudos)
  - `backend/app/main.py` (rota ligada ao sistema)
  - `backend/tests/test_reports.py` (7 testes: geração correta, resposta
    inválida vira erro 400, isolamento entre psicólogas diferentes tanto
    para paciente quanto para modelo, histórico e detalhe do laudo)
- **Como testar/ver funcionando:**
  1. `cd backend && source .venv/bin/activate && python -m pytest tests/ -v`
     — devem passar 49 de 49 testes no total do projeto até aqui.
  2. Fluxo manual completo pela documentação (`/docs`): registrar →
     login → `python -m app.seed_templates <email>` (cadastra CARS/ATA/
     SNAP-IV) → criar um paciente → `POST /api/patients/{id}/reports` com
     o `template_id` da CARS e as 15 respostas → ver a pontuação e a
     classificação na resposta, e depois em
     `GET /api/patients/{id}/reports`.
- **Pendências/observações:** Fim da Semana 2 do cronograma (backend +
  motor de regras). Ainda faltam: ligar o frontend a essas rotas de
  verdade (Semana 3), gerar o texto do laudo com IA via LangChain e
  exportar em PDF (Semana 4). O `age_equivalent_percentage` (Portage)
  continua não implementado — uma tentativa de gerar laudo com um template
  desse tipo retorna erro 501 (não confundir com bug: é a resposta
  correta e esperada por enquanto).

## [Semana 3] Formulário dinâmico, dashboard, histórico e gráficos (Prompts 3.1–3.4)
- **Status:** ✅ Pronto
- **Data:** 2026-09-13
- **Prompt de origem:** Prompts 3.1, 3.2, 3.3 e 3.4 do PROMPTS.md (feitos
  juntos, por serem partes de um mesmo fluxo de tela)
- **O que foi feito:** O frontend deixou de usar dados fixos de mentirinha
  e passou a conversar de verdade com a API:
  - **Login de verdade**: a tela de login agora chama a API, guarda o
    "crachá" (token) no navegador e mantém a psicóloga logada mesmo se
    atualizar a página. Quem não estiver logada é redirecionada para o
    login automaticamente ao tentar acessar qualquer tela interna.
  - **Dashboard**: lista os pacientes de verdade da psicóloga logada, com
    um formulário simples para cadastrar um novo paciente na hora.
  - **Novo Atendimento**: a parte mais trabalhosa — ao escolher um
    paciente e um modelo de laudo (CARS, ATA, SNAP-IV...), o formulário
    é **montado sozinho** a partir das perguntas daquele modelo (campos de
    escala numérica, sim/não, múltipla escolha ou texto livre, cada um
    exibido do jeito certo). Ao clicar em "Gerar Laudo", o sistema manda
    as respostas para o motor de regras (Semana 2) e mostra na hora a
    pontuação, a classificação e um **gráfico automático** (barra, radar
    ou pizza, dependendo do que o modelo pede) com o resultado por área.
  - **Histórico do Paciente**: lista de verdade todos os laudos já
    gerados daquele paciente, com data, modelo usado e a classificação
    obtida.
  - **Build único**: confirmado de novo (com o frontend bem maior agora)
    que o backend sozinho consegue servir todas essas telas na mesma
    porta da API, inclusive recarregando a página direto em qualquer tela
    interna.
- **Arquivos criados/alterados:**
  - `frontend/src/api/client.ts` (agora cuida do token de login também),
    `types.ts`, `auth.ts`, `patients.ts`, `templates.ts`, `reports.ts`
  - `frontend/src/context/AuthContext.tsx`,
    `frontend/src/components/RequireAuth.tsx` (controle de quem está
    logado)
  - `frontend/src/pages/Login.tsx`, `Dashboard.tsx`, `NovoAtendimento.tsx`,
    `HistoricoPaciente.tsx` (reescritas com dados reais)
  - `frontend/src/components/DynamicField.tsx` (um campo do formulário,
    de qualquer tipo) e `ScoreChart.tsx` (o gráfico automático, usando
    Chart.js)
  - `frontend/src/components/Layout.tsx` (mostra o nome de quem está
    logada e um botão de sair)
- **Como testar/ver funcionando:**
  1. Preparar dados de teste: com o backend rodando, registrar uma
     psicóloga (`POST /api/auth/register`) e rodar
     `python -m app.seed_templates <email>` para ter CARS/ATA/SNAP-IV
     disponíveis.
  2. Modo produção (um serviço só): `cd frontend && npm run build`, depois
     `cd ../backend && uvicorn app.main:app --port 8000`, abrir
     `http://localhost:8000`, fazer login, cadastrar um paciente no
     Dashboard, ir em "Novo Atendimento", escolher o paciente e a escala
     CARS, preencher as 15 áreas e clicar em "Gerar Laudo" — deve aparecer
     a pontuação, a classificação e o gráfico de barras. Depois, no
     histórico daquele paciente, o laudo gerado deve aparecer na lista.
  3. Testado de ponta a ponta também via API direta (`curl`), simulando
     exatamente essa sequência, com o build de produção rodando — todos
     os passos responderam corretamente.
- **Pendências/observações:**
  - O formulário automático ainda não sabe lidar com o formato "idade
    equivalente" do Portage (mostra um aviso em vez de quebrar) — só
    funciona de verdade quando o motor de regras implementar esse tipo,
    que continua propositalmente pendente.
  - Ainda não existem testes automatizados de frontend (tipo Jest/Testing
    Library) — a verificação até aqui foi manual e via API; o SPEC.md não
    exige testes de frontend na lista mínima (seção 6), então isso ficou
    como validação manual mesmo.
  - Ainda falta o texto gerado por IA e o PDF exportável (Semana 4) — por
    enquanto o "laudo" na tela é só a pontuação, a classificação e o
    gráfico.

## [Semana 4] IA gerando o texto do laudo (via LangChain)
- **Status:** ✅ Pronto (código e testes; chamada real à IA não pôde ser
  testada ao vivo nesta máquina — ver observações)
- **Data:** 2026-09-13
- **Prompt de origem:** Prompt 4.1 do PROMPTS.md
- **O que foi feito:** Implementada a geração do texto descritivo do laudo
  usando **LangChain**, como combinamos: o provedor de IA (hoje Anthropic,
  mas pode virar OpenAI só trocando `AI_PROVIDER`/as chaves no `.env`, sem
  mexer em código) recebe apenas o nome da escala, as respostas marcadas e
  a pontuação/classificação já calculada pelo motor de regras — nunca
  "inventa" dado que não esteja ali, e nunca afirma um diagnóstico fechado
  (instrução explícita dada à IA). A resposta vem em **três seções
  organizadas** (introdução, análise por área, conclusão/recomendações),
  não um texto solto, o que facilita encaixar no layout do laudo depois.
  O texto gerado fica salvo no laudo, mas a psicóloga pode **editar
  livremente antes de considerá-lo final** — nada é exportado sem essa
  revisão (like combinado com o SPEC.md seção 5). No frontend, a tela de
  "Novo Atendimento" ganhou um botão "Gerar Texto Com IA" e uma caixa de
  texto editável logo depois do resultado calculado.
- **Arquivos criados/alterados:**
  - `backend/app/services/ai/schemas.py` (formato das 3 seções),
    `provider.py` (escolhe Anthropic/OpenAI conforme `.env`), `chains.py`
    (monta o prompt e chama a IA), `exceptions.py`
  - `backend/app/api/reports.py` (`POST /api/reports/{id}/generate-text`,
    `PUT /api/reports/{id}/text`)
  - `backend/app/schemas/report.py` (formato do texto revisado)
  - `backend/tests/test_reports_ai_text.py` (5 testes — usando um "dublê"
    da chamada de IA, para não depender de uma chave de API real rodando
    nos testes automatizados)
  - `frontend/src/api/reports.ts` (chamadas para gerar/salvar o texto)
  - `frontend/src/pages/NovoAtendimento.tsx` (botão de gerar com IA + caixa
    de texto editável + botão de salvar)
- **Como testar/ver funcionando:**
  1. `cd backend && source .venv/bin/activate && python -m pytest tests/ -v`
     — devem passar 54 de 54 testes (os testes de IA usam uma versão falsa
     da chamada, então passam mesmo sem chave de API configurada).
  2. Para testar a chamada de IA de verdade: preencher `ANTHROPIC_API_KEY`
     no `backend/.env`, gerar um laudo normalmente e clicar em "Gerar Texto
     Com IA" na tela de Novo Atendimento (ou chamar
     `POST /api/reports/{id}/generate-text` pelo `/docs`).
- **Pendências/observações:**
  - **Não foi possível testar uma chamada real à IA nesta máquina** —
    não há uma `ANTHROPIC_API_KEY` disponível neste ambiente de
    desenvolvimento. O código está pronto e os testes automatizados
    confirmam que toda a "fiação" (rota, permissões, salvar no banco,
    tratamento de erro de configuração) funciona corretamente; só falta
    validar a qualidade do texto gerado de fato, o que exige a chave real
    da psicóloga/cliente.
  - Se a chave de API não estiver configurada, o sistema não quebra:
    devolve um erro 500 com uma mensagem clara dizendo qual variável falta
    no `.env`, em vez de travar ou mostrar um erro genérico.
  - Ainda falta a exportação em PDF (próximo passo, Prompt 4.2) — o texto
    revisado ainda só existe na tela e no banco de dados.

## [Semana 4] Exportação em PDF
- **Status:** ✅ Pronto
- **Data:** 2026-09-13
- **Prompt de origem:** Prompt 4.2 do PROMPTS.md
- **O que foi feito:** Implementado o download do laudo em PDF de verdade
  (`GET /api/reports/{id}/pdf`), com WeasyPrint (biblioteca preferida no
  SPEC.md). O PDF traz: dados do paciente (nome, data de nascimento, data
  do atendimento), a tabela de pontuação por área com a classificação de
  cada uma, a classificação geral e a pontuação total, um **gráfico**
  gerado com Matplotlib (barra, radar ou pizza — o mesmo tipo configurado
  no modelo de laudo) e o texto do parecer **já revisado pela psicóloga**
  (nunca o texto bruto da IA sem revisão, seguindo a regra do SPEC.md
  seção 5). O PDF é gerado na hora do download, então sempre reflete a
  versão mais recente do texto e das respostas. No frontend, foi
  adicionado um botão "Baixar PDF" tanto na tela de Novo Atendimento
  (logo após gerar o laudo) quanto no Histórico do Paciente (em cada
  laudo já gerado).
- **Arquivos criados/alterados:**
  - `backend/app/services/pdf.py` (monta o HTML do laudo e gera o PDF;
    gera o gráfico com Matplotlib e embute como imagem)
  - `backend/app/api/reports.py` (`GET /api/reports/{id}/pdf`)
  - `backend/tests/test_reports_pdf.py` (4 testes: PDF válido é gerado e
    baixado, reflete o texto revisado, e outra psicóloga não consegue
    baixar o laudo de outra pessoa)
  - `frontend/src/api/reports.ts` (`downloadReportPdf`, que baixa o
    arquivo já autenticado, sem depender de link direto)
  - `frontend/src/pages/NovoAtendimento.tsx`,
    `frontend/src/pages/HistoricoPaciente.tsx` (botão "Baixar PDF")
  - `.gitignore` (os PDFs gerados ficam em `backend/storage/reports/` e
    não devem ser versionados)
- **Como testar/ver funcionando:**
  1. `cd backend && source .venv/bin/activate && python -m pytest tests/ -v`
     — devem passar 57 de 57 testes.
  2. Pela tela: gerar um laudo em "Novo Atendimento" e clicar em "Baixar
     PDF" — o navegador baixa um arquivo PDF de verdade, com tabela,
     gráfico e o texto revisado (se algum tiver sido gerado/editado).
  3. Testado manualmente com o `pdftotext` para conferir que todo o
     conteúdo esperado aparece corretamente no arquivo gerado.
- **Pendências/observações:** O layout do PDF é bem mais simples do que o
  protótipo original da cliente (`referencia_cliente/`), que tem seções
  bem mais elaboradas (anamnese completa, fotos, quadros comportamentais,
  hipóteses diagnósticas com CID, etc.). O que foi entregue aqui cobre
  exatamente o que o SPEC.md pediu para esta etapa (dados do paciente,
  pontuações, gráfico, classificação, texto revisado) — deixar o PDF no
  padrão visual completo do protótipo da clínica é um refinamento visual
  que pode ser feito depois, se a psicóloga quiser aproximar mais o
  layout final do que ela já está acostumada a usar.

## [Semana 4] Testes finais e revisão de segurança
- **Status:** ✅ Pronto
- **Data:** 2026-09-13
- **Prompt de origem:** Prompt 4.3 do PROMPTS.md
- **O que foi feito:** Revisão de ponta a ponta em todas as rotas que
  mexem com dados de paciente ou laudo, conferindo item por item o que o
  CLAUDE.md seção 5 exige: (1) toda rota que devolve dado de paciente
  exige login e (2) cada psicóloga só acessa o que é dela. Resultado:
  **todas as rotas de pacientes, templates e laudos já exigiam login e
  filtravam por dona** desde que foram criadas nas semanas anteriores —
  confirmado revisando o código rota por rota. Também foi checado que o
  sistema nunca grava dados de paciente em log de texto puro (não existe
  nenhum `print`/log de dado clínico no código).
  Durante essa revisão, foi encontrado e corrigido um problema de verdade:
  **excluir um paciente que já tinha laudos no histórico não tinha
  nenhuma proteção** — dependendo do banco, isso poderia apagar um
  paciente e deixar laudos "órfãos" no banco, ou dar um erro feio e
  confuso. Corrigido: agora o sistema recusa a exclusão com uma mensagem
  clara ("Não é possível excluir um paciente com laudos no histórico"),
  protegendo o histórico clínico de ser apagado sem querer.
- **Arquivos criados/alterados:**
  - `backend/app/api/patients.py` (proteção contra excluir paciente com
    laudos)
  - `backend/tests/test_patients.py` (teste novo cobrindo essa proteção)
- **Como testar/ver funcionando:**
  `cd backend && source .venv/bin/activate && python -m pytest tests/ -v`
  — devem passar 58 de 58 testes no total do projeto.
- **Pendências/observações (pontos de atenção para produção, não bugs):**
  - `JWT_SECRET` no `.env.example` tem um valor de exemplo
    (`troque-por-um-segredo-forte`) — é responsabilidade de quem for
    implantar o sistema trocar por um segredo forte de verdade antes de
    ir para produção. Isso vai virar um item do checklist de implantação
    (Prompt 4.4).
  - Não existe limite de tentativas de login (proteção contra "força
    bruta" na senha). O SPEC.md não pede isso na lista mínima de
    segurança (seção 5/6), mas é uma melhoria recomendável antes de expor
    o sistema publicamente na internet.
  - Não há testes automatizados de frontend (Jest/Testing Library) — a
    validação do frontend foi manual e via chamadas diretas à API,
    também compatível com a lista mínima do SPEC.md seção 6 (que só pede
    testes do motor de regras e de autenticação/autorização, ambos
    cobertos).

## [Semana 4] Preparação para implantação
- **Status:** ✅ Pronto
- **Data:** 2026-09-13
- **Prompt de origem:** Prompt 4.4 do PROMPTS.md
- **O que foi feito:** Criado um `Dockerfile` único que compila o
  frontend e empacota tudo com o backend num só serviço (exatamente a
  decisão de arquitetura do CLAUDE.md seção 2 — sem servidor Node em
  produção). O container já sabe rodar as migrations do banco sozinho
  antes de subir. Também foi criado o `DEPLOY.md`, um checklist completo
  de implantação: quais variáveis de ambiente são obrigatórias e por quê
  (com destaque para trocar o `JWT_SECRET` de exemplo), banco de dados e
  backup, HTTPS (obrigatório — hoje o serviço só fala HTTP puro, então
  precisa ficar atrás de um proxy com TLS), e um checklist de segurança
  final antes de ir ao ar.
  O build ficou travado na primeira tentativa por falta de espaço em
  disco nesta máquina de desenvolvimento (compartilhada com outros
  projetos). Com autorização, foi feita uma limpeza pontual de containers
  parados e imagens Docker antigas não usadas por nenhum projeto em
  execução no momento — sem tocar em nada que estivesse rodando (os
  projetos "ferias-*", os dois Postgres e o Portainer continuaram
  intactos). Depois disso, **o build e a execução completa em Docker
  foram testados de ponta a ponta com sucesso**: build da imagem, subida
  do container, migrations automáticas, cadastro de psicóloga, login,
  seed dos templates, criação de paciente, geração de laudo e **download
  de PDF dentro do container** (confirmando que as bibliotecas de sistema
  do WeasyPrint instaladas no `Dockerfile` funcionam corretamente).
- **Arquivos criados/alterados:**
  - `Dockerfile`, `.dockerignore`
  - `DEPLOY.md` (checklist de implantação)
  - `README.md` (seção de como buildar/rodar via Docker)
- **Como testar/ver funcionando:**
  `docker build -t formpsico .` a partir da raiz do projeto, depois
  `docker run -p 8000:8000 --env-file backend/.env formpsico` (com o
  `.env` configurado para um Postgres real). Já testado com sucesso nesta
  máquina.
- **Pendências/observações:**
  - Conforme pedido no `PROMPTS.md`, **o deploy em produção em si não foi
    feito** — só a preparação e a validação local via Docker.
  - A imagem de teste (`formpsico:test`) foi removida depois de validada,
    para não ocupar espaço à toa — quem for implantar de verdade deve
    gerar sua própria imagem com a tag/registro apropriado.
  - Este é o último prompt do roteiro original de 4 semanas
    (`PROMPTS.md`). O sistema cobre o fluxo completo: login → cadastro de
    paciente → escolha de modelo de laudo → formulário dinâmico → motor
    de regras → texto por IA (revisável) → PDF para download — com as
    pendências já listadas em cada entrega anterior (ATA incompleta,
    Portage não implementado, chave de IA não testada ao vivo nesta
    máquina — o build Docker, por outro lado, já foi validado de ponta a
    ponta).

## Ajuste de fluxo: Novo Atendimento, Configurações de IA e correção de erro
- **Status:** ✅ Pronto
- **Data:** 2026-09-13
- **Origem:** Pedido direto no chat (fora da lista numerada do
  PROMPTS.md), ajustando a experiência de uso do sistema depois de ver o
  fluxo funcionando pela primeira vez.
- **O que foi pedido:** Depois do login, a psicóloga deveria conseguir
  cadastrar o paciente e preencher a "planilha" do atendimento no mesmo
  lugar (sem precisar ir ao Dashboard antes); com os dados informados, o
  laudo em PDF com gráficos deveria sair praticamente pronto; o histórico
  do paciente e do laudo deveria ficar salvo, com opção fácil de gerar um
  novo laudo para um paciente já existente; e deveria existir um lugar
  fácil, dentro do próprio sistema, para configurar a chave da IA que
  gera o texto do laudo (antes só dava pra mudar isso editando o arquivo
  `.env` do servidor).
- **O que foi feito:**
  - **Tela "Configurações"** nova: a psicóloga escolhe o provedor de IA
    (Anthropic ou OpenAI), o modelo e cola a própria chave de API, direto
    pela tela — sem precisar de acesso técnico ao servidor. Cada
    psicóloga tem a própria configuração, guardada de forma isolada (uma
    não vê nem usa a chave da outra).
  - **"Novo Atendimento" agora cadastra o paciente no mesmo lugar**: tem
    um "+ Cadastrar Novo Paciente" logo ao lado da lista de pacientes, que
    abre um formulariozinho ali mesmo — não precisa mais ir ao Dashboard
    primeiro.
  - **Geração mais direta**: assim que a pontuação é calculada, o sistema
    já tenta gerar o texto do laudo por IA sozinho, sem precisar de um
    clique extra. A psicóloga só entra em ação se quiser revisar, editar
    ou gerar de novo — e o PDF com os gráficos fica um clique depois
    disso.
  - **"Novo Laudo" a partir do histórico**: tanto no Dashboard quanto no
    Histórico do Paciente, agora tem um atalho "Novo Atendimento" /
    "+ Novo Laudo Para Este Paciente" que já leva para a tela de Novo
    Atendimento com aquele paciente pré-selecionado.
  - **Bug real encontrado e corrigido durante o teste manual**: quando a
    chave de IA configurada estava errada (ou o provedor tinha algum
    problema), o sistema respondia com um erro genérico e sem explicação
    ("Internal Server Error"), sem dizer à psicóloga o que fazer. Agora
    esse tipo de erro vira uma mensagem clara, apontando para a tela de
    Configurações, sem derrubar o resto do sistema.
- **Arquivos criados/alterados:**
  - `backend/app/models/ai_settings.py` (nova tabela `ai_settings`, uma
    configuração por psicóloga) + migration
    `5a34ed7c7607_adiciona_ai_settings.py`
  - `backend/app/schemas/ai_settings.py`, `backend/app/api/ai_settings.py`
    (`GET`/`PUT /api/settings/ai` — a chave nunca volta em texto puro nas
    respostas, só uma prévia mascarada)
  - `backend/app/services/ai/resolver.py` (decide qual chave usar: a da
    psicóloga, cadastrada no banco, ou a do `.env` do servidor como
    reserva)
  - `backend/app/services/ai/provider.py`, `chains.py` (ajustados para
    receber a credencial já resolvida, em vez de ler só do `.env` global)
  - `backend/app/api/reports.py` (usa o resolvedor; e agora captura
    qualquer erro do provedor de IA — não só falta de configuração — e
    devolve uma mensagem clara em vez de um erro genérico)
  - `backend/tests/test_ai_settings.py` (5 testes novos),
    `backend/tests/test_reports_ai_text.py` (atualizado + teste novo do
    erro genérico do provedor)
  - `frontend/src/api/aiSettings.ts`, `frontend/src/pages/Configuracoes.tsx`
  - `frontend/src/pages/NovoAtendimento.tsx` (cadastro de paciente
    embutido, pré-seleção de paciente por link, geração automática do
    texto por IA)
  - `frontend/src/pages/Dashboard.tsx`, `HistoricoPaciente.tsx` (atalhos
    de "Novo Atendimento" por paciente)
  - `frontend/src/components/Layout.tsx` (link "Configurações" no menu)
- **Como testar/ver funcionando:**
  1. `cd backend && source .venv/bin/activate && python -m pytest tests/ -v`
     — devem passar 65 de 65 testes.
  2. Pela tela: entrar em "Configurações" e cadastrar uma chave de IA de
     verdade; ir em "Novo Atendimento", cadastrar um paciente novo ali
     mesmo, escolher a escala CARS, preencher e clicar em "Gerar Laudo" —
     o texto por IA já deve aparecer sozinho, pronto para revisão, com o
     gráfico e o botão "Baixar PDF". No histórico daquele paciente, o
     atalho "+ Novo Laudo Para Este Paciente" já leva de volta para o
     mesmo paciente.
  3. Testado manualmente também o caminho de erro: sem nenhuma chave
     configurada, e depois com uma chave errada de propósito — os dois
     casos agora mostram uma mensagem clara em vez de travar ou mostrar
     um erro genérico (foi assim que o bug do "Internal Server Error" foi
     encontrado).
- **Pendências/observações:** A chave de API fica guardada em texto puro
  na tabela `ai_settings` do banco de dados (não criptografada). Para uma
  clínica real isso merece atenção extra — o banco de dados já precisa
  estar protegido (acesso restrito, backup seguro) como qualquer outro
  dado sensível do sistema (SPEC.md seção 5), mas criptografar a chave
  em repouso seria um reforço extra recomendável antes de um uso mais
  amplo.

## Adição: suporte ao Google Gemini como provedor de IA
- **Status:** ✅ Pronto
- **Data:** 2026-09-13
- **Origem:** Pedido direto no chat — o usuário já paga a assinatura do
  Google (Gemini Advanced/Google AI Pro) e quer usar essa IA em vez de
  Anthropic/OpenAI.
- **O que foi feito:** Adicionado o Gemini como terceiro provedor de IA,
  ao lado de Anthropic e OpenAI, na tela de "Configurações". Como o
  LangChain já foi escolhido desde o início justamente para isso (SPEC.md
  seção 5 e a conversa sobre arquitetura no começo do projeto), trocar de
  provedor não exigiu mexer no motor de regras, no PDF nem em nenhuma
  outra parte do sistema — só a camada de IA precisou aprender a falar
  com mais um provedor.
  **Atenção importante para o usuário:** a assinatura do aplicativo do
  Gemini (Google One AI Premium / Gemini Advanced) é uma assinatura de
  consumidor e **não é a mesma coisa** que uma chave de API para
  desenvolvedor — são cobradas separadamente pelo Google. É preciso gerar
  uma chave própria em https://aistudio.google.com/app/apikey (o Google
  costuma oferecer uma cota gratuita generosa nessa chave, separada da
  mensalidade do app). A tela de Configurações já mostra esse aviso e o
  link direto quando "Google (Gemini)" é escolhido.
- **Arquivos criados/alterados:**
  - `backend/requirements.txt` (`langchain-google-genai`)
  - `backend/app/core/config.py` (`GOOGLE_API_KEY` como opção no `.env`
    do servidor, reserva/padrão)
  - `backend/app/services/ai/provider.py` (reconhece `provider="google"`)
  - `backend/app/services/ai/resolver.py` (também procura
    `GOOGLE_API_KEY` como reserva)
  - `backend/app/schemas/ai_settings.py` (`"google"` como opção válida)
  - `.env.example`, `backend/.env` (variável nova documentada)
  - `backend/tests/test_ai_provider.py` (3 testes: cada provedor
    instancia a classe certa do LangChain, provedor desconhecido dá erro
    claro), `test_ai_settings.py` (teste novo aceitando `"google"`)
  - `frontend/src/api/aiSettings.ts`, `frontend/src/pages/Configuracoes.tsx`
    (Gemini na lista de provedores, com o aviso sobre a chave de API ser
    separada da assinatura do app)
- **Como testar/ver funcionando:**
  1. `cd backend && source .venv/bin/activate && python -m pytest tests/ -v`
     — devem passar 70 de 70 testes.
  2. Em "Configurações", escolher "Google (Gemini)", colar uma chave
     gerada em aistudio.google.com/app/apikey, e usar "Gerar Texto Com
     IA" normalmente em qualquer laudo.
  3. Testado manualmente de ponta a ponta com uma chave falsa: a
     requisição chegou de verdade nos servidores do Google e voltou com
     "chave inválida" (confirma que a integração está correta — só
     faltou uma chave real, que não está disponível nesta máquina de
     desenvolvimento).
- **Pendências/observações:** Assim como Anthropic/OpenAI, não foi
  possível testar com uma chave real do Gemini nesta máquina — só a
  "fiação" completa (configuração → resolução de credenciais →
  chamada real ao Google → tratamento do erro) foi validada.

## Adição: edição do histórico com log de auditoria, e PDF consolidado por IA
- **Status:** ✅ Pronto (funcionalidade e testes; chamada real de IA para
  o PDF consolidado não testada ao vivo nesta máquina, mesma limitação já
  registrada nas entregas anteriores de IA)
- **Data:** 2026-09-13
- **Origem:** Pedido direto no chat, olhando a tela de Histórico do
  Paciente já funcionando.
- **O que foi pedido:** Poder editar e salvar o "Modelo Usado" e a
  "Classificação" de cada linha do histórico, com essas alterações
  guardadas em "Logs"; e poder selecionar um ou mais laudos do histórico
  para a IA ler e gerar um único PDF consolidado a partir deles — com a
  IA tratada, no prompt, como uma assistente experiente em psicologia que
  gera os melhores documentos/laudos possíveis.
- **O que foi feito:**
  - **Edição inline no histórico**: cada linha da tabela agora tem um
    botão "Editar" que transforma "Modelo Usado" e "Classificação" em
    campos de texto editáveis, com "Salvar"/"Cancelar". O valor editado
    não apaga o cálculo original (pontuação, gráfico) — só passa a
    aparecer no lugar dele na tela e no PDF daquele laudo.
  - **Log de auditoria**: toda vez que um desses campos é alterado, fica
    guardado quem mudou, quando, e o valor antes/depois — nada é
    sobrescrito silenciosamente. Um botão "Ver Logs" em cada linha mostra
    esse histórico de edições. Editar com o mesmo valor que já estava
    (sem mudança de verdade) não gera um log à toa.
  - **Seleção múltipla + PDF consolidado**: cada linha do histórico agora
    tem uma caixa de seleção; ao marcar um ou mais laudos, aparece o
    botão "Gerar PDF Consolidado", que manda a IA ler todas as avaliações
    marcadas (pontuações, classificações, texto já revisado de cada uma,
    inclusive as correções manuais feitas via "Editar") e escrever um
    **único parecer integrado**, apontando convergências, divergências e
    evolução ao longo do tempo — seguido de um resumo (tabela + gráfico)
    de cada avaliação de origem, tudo num PDF só.
  - **Prompt da IA atualizado**: conforme pedido, o prompt agora começa
    afirmando explicitamente que a IA "tem formação e experiência sólida
    na área de psicologia e neuropsicopedagogia clínica" e que seu
    objetivo é "produzir o melhor documento clínico possível" — usado
    tanto na geração de texto de um laudo individual quanto no parecer
    consolidado.
- **Arquivos criados/alterados:**
  - `backend/app/models/report.py` (dois campos novos:
    `template_name_override`, `classification_override`),
    `backend/app/models/report_change_log.py` (tabela de auditoria) +
    migration `752d5a642845_adiciona_edicao_log_de_laudos.py`
  - `backend/app/schemas/report.py` (`ReportEditUpdate`,
    `ReportChangeLogOut`, `ConsolidatedPdfRequest`)
  - `backend/app/api/reports.py` (`PATCH /api/reports/{id}`,
    `GET /api/reports/{id}/logs`,
    `POST /api/patients/{id}/consolidated-pdf`)
  - `backend/app/services/ai/chains.py` (persona da IA atualizada +
    `generate_consolidated_report_text`, novo prompt específico para
    síntese de múltiplas avaliações)
  - `backend/app/services/pdf.py` (`render_consolidated_pdf`; e o PDF de
    um laudo individual agora também respeita as correções manuais)
  - `backend/tests/test_reports_edit_log.py` (6 testes),
    `backend/tests/test_consolidated_pdf.py` (4 testes)
  - `frontend/src/api/client.ts` (`apiPatch`, `downloadBlob`),
    `frontend/src/api/reports.ts` (`updateReportEdit`, `getReportLogs`,
    `downloadConsolidatedPdf`)
  - `frontend/src/pages/HistoricoPaciente.tsx` (reescrita: edição inline,
    logs expansíveis, seleção múltipla, botão de PDF consolidado)
- **Como testar/ver funcionando:**
  1. `cd backend && source .venv/bin/activate && python -m pytest tests/ -v`
     — devem passar 79 de 79 testes.
  2. Pela tela: no Histórico do Paciente, clicar em "Editar" numa linha,
     mudar o nome do modelo e a classificação, "Salvar" — depois "Ver
     Logs" mostra a alteração com data/hora e quem editou. Marcar duas ou
     mais linhas e clicar em "Gerar PDF Consolidado" (precisa de uma
     chave de IA configurada em "Configurações") — deve baixar um único
     PDF com o parecer integrado e o resumo de cada avaliação.
  3. Testado manualmente de ponta a ponta via API: edição, log com dois
     registros na ordem certa (mais recente primeiro), e o endpoint do
     PDF consolidado devolvendo a mensagem clara de "sem chave de IA
     configurada" quando aplicável.
- **Pendências/observações:**
  - O PDF consolidado não fica salvo no histórico como um novo laudo —
    é gerado na hora e baixado, sem ficar guardado em lugar nenhum do
    sistema (decisão de escopo: ele é um documento derivado de laudos já
    existentes, não um novo atendimento).
  - Assim como os outros recursos de IA, não foi possível testar a
    geração real do parecer consolidado nesta máquina por falta de uma
    chave de API válida — só a "fiação" completa (seleção → validação de
    propriedade dos laudos → chamada de IA → geração do PDF → erro claro
    quando mal configurado) foi validada.

## Motor de regras: Portage/IPO (age_equivalent_percentage) implementado

- **Status:** ✅ Pronto (motor de regras e formulário; inventário oficial
  completo do Portage continua pendente — ver observações)
- **Data:** 2026-09-13
- **Origem:** Pedido direto no chat, retomando a pendência documentada em
  `TEMPLATES_LAUDOS.md` seção 5/7 (o Portage era o único dos quatro tipos
  de escala sem implementação, porque dependia de um inventário oficial de
  ~580 habilidades que a clínica nunca chegou a enviar).
- **O que foi pedido:** Implementar o cálculo do Portage sem ficar
  esperando o inventário completo — usando uma abordagem genérica que a
  própria psicóloga consiga alimentar aos poucos.
- **O que foi feito:** Em vez de exigir a idade exata de cada uma das ~580
  habilidades (dado que não existe ainda), o motor de regras passou a
  organizar cada área do Portage em **faixas etárias** (ex.: "0 a 24
  meses", "24 a 48 meses"), cada uma com os itens que a psicóloga já tem.
  Para cada área, o sistema calcula o quanto a criança "acertou" em cada
  faixa (respostas "sim"/"às vezes"/"não", com peso 1,0/0,5/0,2) e estima
  uma **idade de desenvolvimento**: a maior faixa totalmente atingida (75%
  ou mais de acerto), mais um crédito parcial proporcional da faixa
  seguinte (não é mais "tudo ou nada"). Essa idade estimada é comparada com
  a idade cronológica do paciente na data da avaliação, virando um
  percentual (ex.: "80% da idade esperada") que é classificado (ex.:
  "Atraso leve") do mesmo jeito que as outras escalas. O formulário de
  "Novo Atendimento" também ganhou suporte a esse formato — antes mostrava
  um aviso de "ainda não suportado", agora mostra os itens agrupados por
  faixa etária normalmente. Foi cadastrado um exemplo (`portage.json`, 2
  áreas com 2 faixas cada) para servir de ponto de partida — **não é o
  inventário completo**, é só para mostrar o formato funcionando.
- **Arquivos criados/alterados:**
  - `backend/app/rules_engine/age_equivalent_percentage.py` (cálculo novo)
  - `backend/app/rules_engine/engine.py` (passa a receber a data de
    nascimento do paciente e despachar para o cálculo novo)
  - `backend/app/schemas/report_template.py` (`AgeBracket`, `TemplateArea`
    ganha `age_brackets` no lugar do antigo `age_range` nunca usado,
    `item_scoring` no schema, validação completa do `rule_type`
    `age_equivalent_percentage`)
  - `backend/app/schemas/report.py` (`ReportCreate.evaluation_date`,
    opcional — usa a data de hoje se não vier)
  - `backend/app/api/reports.py` (passa a idade do paciente para o motor de
    regras)
  - `backend/app/rules_engine/fixtures/portage.json` (exemplo novo),
    `backend/app/seed_templates.py` (cadastra o exemplo também)
  - `backend/tests/test_rules_engine_age_equivalent.py` (10 testes novos:
    cálculo completo, crédito parcial interpolado, faixas fora de ordem,
    idade cronológica maior que a de desenvolvimento, dados inválidos/
    incompletos), `backend/tests/test_rules_engine.py` (teste do stub
    antigo trocado por um teste real), `backend/tests/test_seed_fixtures.py`
    (fixture novo validado + um caso de cálculo completo)
  - `frontend/src/api/types.ts` (`AgeBracket`, `Answers` e `ComputedResult`
    atualizados para o novo formato)
  - `frontend/src/pages/NovoAtendimento.tsx` (formulário e resultado
    passam a exibir faixas etárias/idade de desenvolvimento em vez do
    aviso de "não suportado")
  - `TEMPLATES_LAUDOS.md` seção 5 (documentação da decisão e do algoritmo)
- **Como testar/ver funcionando:**
  1. `cd backend && source .venv/bin/activate && python -m pytest tests/ -v`
     — devem passar 91 de 91 testes.
  2. Pela tela: `python -m app.seed_templates <email>` cadastra também o
     "Inventário Portage Operacionalizado (IPO) — EXEMPLO INCOMPLETO"; em
     "Novo Atendimento", escolher esse modelo, preencher as duas faixas
     etárias das áreas Socialização/Linguagem e clicar em "Gerar Laudo" —
     deve aparecer a idade de desenvolvimento estimada por área, o
     percentual em relação à idade cronológica do paciente e a
     classificação.
- **Pendências/observações:**
  - **O inventário oficial do Portage (~580 habilidades com idade mapeada
    uma a uma) continua não fornecido pela clínica.** A decisão tomada foi
    não bloquear a funcionalidade por causa disso: o `portage.json` atual é
    só um exemplo ilustrativo (2 áreas, 2 faixas cada) — a psicóloga precisa
    completá-lo com os itens reais (aos poucos, sem precisar do inventário
    inteiro de uma vez) antes de uso clínico real. A tela "Modelos de
    Laudo" (próxima entrega, importação de templates via IA) vai facilitar
    isso.
  - O limiar de 75% para considerar uma faixa etária "atingida" é uma
    escolha razoável e documentada no código, mas não é um valor oficial
    do manual do Portage — vale a psicóloga validar/ajustar se tiver
    acesso ao manual completo.

## Cadastro de modelos de laudo por upload de documento (IA)

- **Status:** ✅ Pronto (funcionalidade e testes; chamada real de IA para a
  extração não testada ao vivo nesta máquina, mesma limitação já registrada
  nas outras entregas de IA)
- **Data:** 2026-09-13
- **Origem:** Pedido direto no chat — em vez de eu completar manualmente os
  22 itens que faltam da ATA (ou qualquer outra escala), a psicóloga quer
  poder subir o próprio documento da escala e o sistema usar IA para montar
  o modelo, revisando antes de salvar.
- **O que foi feito:** Nova tela **"Modelos De Laudo"** (não existia
  nenhuma tela para isso antes — só um script de linha de comando). A
  psicóloga sobe um arquivo PDF, DOCX ou TXT com a descrição da escala; o
  sistema extrai o texto do documento e pede para a IA estruturar isso no
  formato que o sistema entende (nome, áreas/domínios, itens de cada área,
  tipo de regra de pontuação mais adequado — soma, contagem ou idade
  equivalente —, e faixas de classificação). O resultado aparece como um
  JSON editável na tela, junto com uma lista de avisos caso alguma parte
  não tenha ficado válida — a psicóloga revisa/corrige à vontade antes de
  clicar em "Salvar Modelo" (que usa exatamente a mesma validação rigorosa
  já existente para cadastro de modelos). Também dá para pular a IA e
  cadastrar/editar um modelo do zero, direto no JSON, com um exemplo em
  branco pronto para editar. Nada é salvo automaticamente — a extração da
  IA só devolve um rascunho, nunca grava nada sozinha.
- **Arquivos criados/alterados:**
  - `backend/requirements.txt` (`pypdf`, `python-docx` — extração de texto)
  - `backend/app/services/document_text.py` (extrai texto de PDF/DOCX/TXT)
  - `backend/app/services/ai/schemas.py` (`ExtractedTemplateDraft` e
    modelos auxiliares — versão mais permissiva do formato de modelo, só
    para a IA preencher), `chains.py`
    (`extract_template_from_document`), `__init__.py`
  - `backend/app/api/templates.py` (`POST /api/templates/import` —
    extrai e devolve o rascunho, não persiste nada)
  - `backend/tests/test_document_text.py` (7 testes: PDF/DOCX/TXT válidos,
    PDF/DOCX corrompidos, formato não suportado)
  - `backend/tests/test_templates_import.py` (9 testes: rascunho válido e
    com erros de validação, formato não suportado, sem configuração de IA,
    erro do provedor, isolamento entre psicólogas — tudo com a chamada de
    IA "dublada", sem depender de uma chave real)
  - `frontend/src/api/client.ts` (`apiPostFile`, upload multipart
    autenticado), `frontend/src/api/templates.ts`
    (`importTemplateFromDocument`, `createTemplate`)
  - `frontend/src/pages/ModelosDeLaudo.tsx` (tela nova)
  - `frontend/src/App.tsx`, `frontend/src/components/Layout.tsx` (rota e
    link "Modelos De Laudo" no menu)
- **Como testar/ver funcionando:**
  1. `cd backend && source .venv/bin/activate && python -m pytest tests/ -v`
     — devem passar 105 de 105 testes.
  2. Pela tela: com uma chave de IA configurada em "Configurações", ir em
     "Modelos De Laudo", subir um `.txt`/`.pdf`/`.docx` com a descrição de
     uma escala qualquer e clicar em "Importar Com IA" — o JSON extraído
     aparece para revisão; ajustar se necessário e "Salvar Modelo". Também
     dá para testar "Ou Cadastrar Um Modelo Manualmente", que abre um
     exemplo em branco editável.
- **Pendências/observações:**
  - Assim como os outros recursos de IA do projeto, a extração real de um
    documento não foi testada com uma chave de API válida nesta máquina —
    só a "fiação" completa (upload → extração de texto → chamada de IA →
    validação → devolução do rascunho → erro claro quando mal configurado)
    foi validada com uma versão dublada da chamada de IA.
  - A revisão do modelo extraído é feita editando o JSON bruto na tela, não
    um formulário visual campo a campo — decisão consciente dado o tamanho
    já grande desta rodada de mudanças; um construtor visual fica como
    possível melhoria futura se a psicóloga achar o JSON difícil de editar.
  - O formato de rascunho da IA (`ExtractedTemplateDraft`) não inclui o
    formato de faixas etárias do Portage (`age_brackets`) — para esse tipo
    de escala, a IA hoje só extrai áreas/itens no formato comum (soma), e a
    psicóloga precisa ajustar manualmente o JSON para o formato
    `age_equivalent_percentage` (ver `TEMPLATES_LAUDOS.md` seção 5). Estender
    a extração por IA para reconhecer faixas etárias diretamente é uma
    melhoria possível para uma próxima rodada.

## PDF completo: seções clínicas, fotos, hipóteses com CID e assinatura

- **Status:** ✅ Pronto
- **Data:** 2026-09-13
- **Origem:** Pedido direto no chat — o PDF gerado (dados, tabela, gráfico,
  classificação, texto por IA) era bem mais simples que o laudo real da
  clínica (`referencia_cliente/RELATORIO_FINAL_ARTHUR_DANIEL__assinado.pdf`,
  com anamnese, histórico de desenvolvimento, hipóteses diagnósticas com
  CID, plano de intervenção, fotos e assinatura com registro profissional).
  Combinado com o usuário um primeiro pacote realista: seções de texto/
  checklist + fotos + hipóteses com CID + assinatura — ficando de fora
  desta rodada o quadro de funções executivas/habilidades acadêmicas por
  ano e o gráfico de "probabilidade estimada por hipótese diagnóstica"
  (dado estruturado extenso e heurística nova, respectivamente — candidatos
  a uma rodada futura se a psicóloga quiser).
- **O que foi feito:**
  - **Seções clínicas por laudo** (opcionais — um laudo sem nada
    preenchido continua gerando o PDF exatamente como antes): Anamnese
    Inicial, Histórico De Desenvolvimento, Encaminhamento/Histórico/
    Queixas, Metodologia, Estudo De Caso E Observações Clínicas, Plano De
    Intervenção, Encaminhamentos (checklist), Considerações Finais, e
    Hipóteses Diagnósticas com código CID (lista curta de hipóteses comuns
    — TEA, TDAH, DI, TOD, Transtorno de Aprendizagem, TPAC — mais opção de
    digitar qualquer outra hipótese como texto livre). Editável no
    Histórico do Paciente, num painel "Seções Clínicas" por linha, igual
    ao padrão já usado para "Editar"/"Ver Logs".
  - **Fotos do paciente**: upload/galeria/exclusão na tela de Histórico do
    Paciente (fotos são do paciente, não de um laudo específico), embutidas
    no PDF na seção de identificação.
  - **Assinatura profissional**: nova tela "Registro Profissional" em
    Configurações (ex.: número do CRP), que aparece no bloco de assinatura
    no fim do PDF junto com o nome da psicóloga e a data.
  - **Sexo e Escola do paciente**: campos opcionais novos no cadastro do
    paciente (Dashboard), aparecem na seção de identificação do PDF quando
    preenchidos.
  - **Bug real encontrado e corrigido durante o teste manual de ponta a
    ponta** (feito via API real, não só nos testes automatizados): o PDF
    de um laudo Portage estava saindo com a tabela de resultados vazia e
    sem gráfico, porque o gerador de PDF só sabia ler o formato de
    resultado do `sum_threshold`/`count_threshold` (`scores`), não o do
    `age_equivalent_percentage` (`areas`, com idade de desenvolvimento e
    percentual). Corrigido: a tabela agora mostra "Idade De
    Desenvolvimento" + percentual da idade cronológica por área, e o
    gráfico passa a ser gerado a partir desses percentuais.
- **Arquivos criados/alterados:**
  - `backend/app/models/patient.py` (`sex`, `school_info`, relação com
    `photos`), `backend/app/models/patient_photo.py` (novo),
    `backend/app/models/psychologist.py` (`professional_registration`),
    `backend/app/models/report.py` (`clinical_sections_json`) +
    migration `069c31366544_adiciona_secoes_clinicas_fotos_e_.py`
  - `backend/app/schemas/patient.py` (campos novos, `PatientPhotoOut`),
    `backend/app/schemas/report.py` (`ClinicalSections`,
    `DiagnosticHypothesis`), `backend/app/schemas/auth.py`
    (`PsychologistProfileUpdate`)
  - `backend/app/core/cid_codes.py` (novo, lista curta de CID-11)
  - `backend/app/api/patients.py` (`POST`/`GET`/`DELETE`
    `/api/patients/{id}/photos...`), `backend/app/api/reports.py`
    (`GET /api/cid-codes`, `PATCH /api/reports/{id}/clinical-sections`),
    `backend/app/api/auth.py` (`PUT /api/auth/me`)
  - `backend/app/services/pdf.py` (seções, fotos embutidas em base64 e
    assinatura renderizadas no PDF individual quando presentes)
  - `backend/tests/test_patient_photos.py` (4 testes), `test_clinical_sections.py`
    (6 testes), `test_reports_pdf.py` (1 teste novo confirmando que o PDF
    continua gerando corretamente com tudo preenchido junto),
    `test_pdf_age_equivalent.py` (4 testes cobrindo a correção do PDF do
    Portage)
  - `frontend/src/api/patients.ts` (fotos, `sex`/`school_info`),
    `frontend/src/api/reports.ts` (`updateClinicalSections`,
    `listCidCodes`), `frontend/src/api/auth.ts` (`updateProfile`)
  - `frontend/src/pages/HistoricoPaciente.tsx` (galeria de fotos + painel
    "Seções Clínicas" por laudo), `frontend/src/pages/Dashboard.tsx`
    (campos sexo/escola no cadastro), `frontend/src/pages/Configuracoes.tsx`
    (seção "Registro Profissional")
- **Como testar/ver funcionando:**
  1. `cd backend && source .venv/bin/activate && alembic upgrade head &&
     python -m pytest tests/ -v` — devem passar 119 de 119 testes.
  2. Pela tela: em "Configurações", preencher o registro profissional; no
     Dashboard, cadastrar um paciente com sexo/escola; no Histórico do
     Paciente, subir uma foto e abrir "Seções Clínicas" de um laudo,
     preencher anamnese/hipóteses/plano de intervenção/encaminhamentos e
     salvar; "Baixar PDF" deve trazer tudo isso junto com o que já existia
     (pontuação, gráfico, texto por IA).
- **Pendências/observações:**
  - O PDF **consolidado** (síntese de vários laudos) não foi alterado
    nesta rodada — continua no formato anterior (parecer integrado +
    resumo por avaliação), sem as seções clínicas/fotos/assinatura, que
    são conceitos por laudo individual/paciente. Se fizer sentido incluir
    fotos/assinatura no consolidado também, é um ajuste pequeno a partir
    daqui.
  - Ficaram fora desta rodada (candidatos a uma próxima, se a psicóloga
    quiser): quadro de funções executivas/habilidades acadêmicas por ano
    escolar (dado estruturado grande, não modelado ainda) e o gráfico de
    "probabilidade estimada por hipótese diagnóstica" (heurística nova,
    não pedida explicitamente).
  - A lista de CID-11 é curta e cobre só as hipóteses mais comuns vistas no
    laudo de referência da clínica — não é uma tabela oficial completa do
    CID-11; a psicóloga pode sempre digitar outra hipótese como texto
    livre.

## Redesenho do frontend com o design system da marca (Neuropp Mayra Vanessa)

- **Status:** ✅ Pronto (build e checagem de tipos limpos; ver observação
  sobre verificação visual)
- **Data:** 2026-09-13
- **Origem:** Pedido direto no chat — usar a pasta `desgin systema/` (fora
  do projeto, ao lado dele) como base para refazer a aparência do
  frontend. Essa pasta tinha dois materiais sem relação entre si: o
  design system real da cliente (extraído do Instagram
  @neuroppmayravanessa — cores roxo/rosa, tipografia Baloo 2/Nunito,
  biblioteca de componentes prontos) e um template genérico de landing
  page médica ("white-medical/VITALIS", Tailwind, sem relação com a
  marca). Perguntado ao usuário, a decisão foi **combinar os dois**: marca
  da Neuropp para cores/tipografia/componentes, com inspiração de layout
  do white-medical só para o "cartão de gráfico" e blocos de estatística
  (número grande + legenda).
- **O que foi feito:** Todo o frontend foi reconstruído visualmente em
  cima do design system da própria cliente, sem mudar nenhuma regra de
  negócio, chamada de API ou comportamento:
  - **Tokens de design** copiados da pasta de origem (cores, tipografia,
    espaçamento, sombras, fontes Baloo 2/Nunito via Google Fonts) e
    aplicados como variáveis CSS globais.
  - **Biblioteca de componentes compartilhados** nova
    (`frontend/src/components/ds/`): Button, IconButton, Card, Badge,
    Input, Select, Textarea, Checkbox, Alert, EmptyState, ProgressBar,
    PageHeader, Tabs, SidebarNav (integrado ao roteamento real via
    `react-router-dom`), PatientAvatar — portados dos componentes React
    da Neuropp, com tipos TypeScript.
  - **Layout novo**: menu lateral fixo (sidebar) com o logo real da
    cliente, no lugar do menu de topo antigo; colapsa para um menu
    hambúrguer em telas estreitas.
  - **Todas as telas reescritas** com os componentes novos: Login,
    Dashboard (com bloco de estatística "Pacientes cadastrados"), Novo
    Atendimento (formulário dinâmico, cartão de resultado, cartão de
    gráfico no estilo "chart card"), Histórico do Paciente (fotos, tabela,
    painéis de edição/logs/seções clínicas), Configurações, Modelos De
    Laudo.
  - **Ícones**: adicionado `lucide-react` (biblioteca leve recomendada
    pelo próprio guideline da marca), usado na sidebar e em botões de
    ação.
  - **Gráficos**: paleta do Chart.js (`ScoreChart`) trocada para as cores
    da marca; a biblioteca de gráficos em si não mudou.
- **Arquivos criados/alterados:** só em `frontend/` — nenhum arquivo do
  `backend/` foi tocado.
  - Novos: `frontend/src/styles/tokens/*.css`, `frontend/src/components/ds/*.tsx`,
    `frontend/public/logo-neuropp.png`
  - Reescritos: `frontend/src/index.css`, `frontend/src/components/Layout.tsx`
    + `Layout.module.css`, `frontend/src/components/DynamicField.tsx`,
    `frontend/src/components/ScoreChart.tsx` (só a paleta),
    `frontend/src/pages/{Login,Dashboard,NovoAtendimento,HistoricoPaciente,Configuracoes,ModelosDeLaudo}.tsx`
    + `Login.module.css`, `Page.module.css` (simplificado — só o que
    ainda é usado)
  - `frontend/package.json` (+ `lucide-react`)
- **Como testar/ver funcionando:**
  1. `cd frontend && npx tsc --noEmit && npm run build` — sem erros de
     tipo/build.
  2. `cd backend && source .venv/bin/activate && python -m pytest tests/ -v`
     — devem continuar passando 119 de 119 (nada de backend foi tocado).
  3. Pela tela: `cd frontend && npm run build`, depois
     `cd ../backend && uvicorn app.main:app --port 8000` e navegar por
     todas as telas logadas — sidebar com o logo, cores roxo/rosa da
     marca, formulários e tabelas com a nova aparência.
- **Pendências/observações:**
  - **Este ambiente de desenvolvimento não tem navegador disponível para
    tirar screenshot** — a verificação foi feita por checagem de tipos,
    build de produção limpo, teste de fumaça servindo o build real pelo
    backend (todos os assets carregando com sucesso) e conferência de que
    toda variável de cor/espaçamento usada no código existe de fato nos
    tokens copiados (nenhuma variável inválida). **A conferência visual
    final (cores, alinhamento, responsividade) precisa ser feita pelo
    usuário rodando `npm run dev` e navegando pelo sistema.**
  - `Dialog`, `Tag` e `Switch` do design system de origem não foram
    portados — nenhuma tela usa modal, chip removível ou toggle hoje;
    ficam disponíveis para portar se uma tela futura precisar.
  - O PDF exportado (WeasyPrint/Matplotlib) não foi alterado — a paleta
    usada nos gráficos do PDF continua a antiga; alinhar também o PDF à
    nova marca é um refinamento possível para uma próxima rodada, mas não
    fazia parte do pedido (frontend).

## Ajustes de feedback: texto do parecer, tabela de classificação e gráficos ilegíveis

- **Status:** ✅ Pronto
- **Data:** 2026-09-13
- **Origem:** Feedback direto do usuário revendo o PDF consolidado e o
  gráfico da CARS: (1) o parecer consolidado trazia um rótulo "Gerado Por
  IA — Revisar Antes De Uso Clínico" bem visível no corpo do texto; (2) a
  coluna "Classificação Da Área" da tabela de pontuações da CARS aparecia
  sempre vazia; (3) o gráfico de barras (PDF e tela) ficava com os rótulos
  das 15 áreas da CARS sobrepostos uns nos outros, ilegível.
- **O que foi feito:**
  - **Título do parecer consolidado** simplificado para "Parecer
    Integrado" (sem a marcação de IA no corpo do texto). O aviso legal
    padrão (rodapé, letra pequena, "gerado automaticamente com apoio de
    inteligência artificial... responsabilidade final é do profissional")
    foi mantido — é uma proteção de responsabilidade, não o rótulo
    chamativo que incomodava.
  - **Texto da IA mais técnico e humanizado**: o prompt (`chains.py`)
    ganhou uma instrução explícita de estilo — escrever em prosa corrida
    como um parecer redigido à mão por um profissional, integrando os
    números na argumentação clínica em vez de listar "área X: valor Y"
    numa sequência mecânica, e nunca mencionar que o texto foi gerado por
    IA dentro do próprio texto.
  - **Coluna de classificação corrigida**: a tabela de pontuações agora só
    mostra a coluna "Classificação Da Área" quando ela existe de verdade
    (escalas `count_threshold`, como o SNAP-IV, ou `age_equivalent_percentage`,
    como o Portage). Escalas `sum_threshold` (CARS, ATA) não têm
    classificação por área — só geral — então a tabela agora mostra só
    "Área" e "Pontuação", e a classificação geral continua aparecendo
    logo abaixo, como já acontecia.
  - **Gráficos de barra tornados horizontais** (backend, Matplotlib, e
    frontend, Chart.js) com altura proporcional ao número de áreas — com
    15 áreas como a CARS, os rótulos agora ficam um embaixo do outro, sem
    rotação e sem sobreposição, em vez de espremidos e girados no eixo X.
- **Arquivos alterados:**
  - `backend/app/services/ai/chains.py` (`ESTILO_DE_ESCRITA`, aplicado a
    `SYSTEM_PROMPT` e `CONSOLIDATED_SYSTEM_PROMPT`)
  - `backend/app/services/pdf.py` (`_cabecalho_tabela_pontuacao`/
    `_linhas_pontuacao` condicionais, `_grafico_barra_horizontal` novo,
    reaproveitado por `_gerar_grafico` e `_gerar_grafico_idade_equivalente`,
    título do parecer consolidado, paleta de cores alinhada à marca)
  - `frontend/src/components/ScoreChart.tsx` (gráfico de barra passa a ser
    horizontal com altura dinâmica, `indexAxis: 'y'`)
- **Como testar/ver funcionando:**
  1. `cd backend && source .venv/bin/activate && python -m pytest tests/ -v`
     — devem continuar passando 119 de 119.
  2. Gerar um laudo com a escala CARS completa (15 áreas) e baixar o PDF —
     a tabela mostra só "Área"/"Pontuação" (sem coluna vazia) e o gráfico
     aparece com barras horizontais, uma por área, totalmente legível.
     Testado de ponta a ponta via API real nesta máquina (extraindo a
     imagem do PDF gerado para conferência visual).
  3. Gerar um PDF consolidado (precisa de chave de IA configurada) — o
     título aparece como "Parecer Integrado", sem menção a IA no corpo.
- **Pendências/observações:**
  - Não foi possível testar a qualidade do texto humanizado com uma
    chamada real de IA nesta máquina (mesma limitação de sempre — falta
    uma chave de API válida no ambiente de desenvolvimento); só o prompt
    foi ajustado e revisado.

## Ajustes de feedback: aviso de geração mais visível, fluxo de salvar e estabilidade do PDF consolidado

- **Status:** ✅ Pronto
- **Data:** 2026-09-13
- **Origem:** Feedback direto do usuário: (1) a mensagem de "gerando texto
  com IA" passava despercebida; (2) depois de salvar o texto revisado, a
  psicóloga queria já ser levada de volta ao histórico do paciente, sem
  precisar navegar manualmente; (3) selecionar mais de um laudo para o PDF
  consolidado às vezes retornava erro.
- **O que foi feito:**
  - **Aviso de geração mais visível** ("Novo Atendimento"): enquanto o
    texto está sendo gerado, aparece um aviso destacado (tom rosa da
    marca, ícone girando) com "Gerando texto com IA..." em negrito — antes
    era uma caixa azul-clara discreta, fácil de não notar. O botão "Gerar
    Texto Com IA" também ganhou o mesmo ícone girando enquanto processa.
  - **"Salvar Texto Revisado" agora leva direto ao Histórico do Paciente**
    daquele atendimento, em vez de deixar a psicóloga na mesma tela sem
    indicação do que fazer a seguir.
  - **PDF consolidado mais resistente a falhas intermitentes da IA**:
    - As três chamadas de IA do sistema (texto individual, parecer
      consolidado, importação de modelo) agora tentam de novo
      automaticamente (até 3 tentativas, com pequena espera entre elas)
      antes de desistir — cobre falhas transitórias comuns de provedores
      de IA (limite de taxa, instabilidade momentânea de rede), que são a
      causa mais provável de "às vezes dá erro" ao combinar vários laudos
      num prompt maior.
    - O texto já redigido de cada laudo de origem é truncado a um tamanho
      razoável ao montar o resumo para a IA — evita que selecionar vários
      laudos com textos longos gere um prompt grande demais para o
      provedor de IA processar de uma vez.
    - Corrigida também uma falha não tratada (erro genérico, não uma
      mensagem clara) que ocorreria se um dos laudos selecionados
      referenciasse um modelo de laudo que não existe mais — agora vira
      um erro claro em vez de travar.
- **Arquivos alterados:**
  - `backend/app/services/ai/chains.py` (`_invocar_com_retentativas`,
    `_truncar`, aplicados às 3 chamadas de IA)
  - `backend/app/api/reports.py` (proteção contra modelo de laudo ausente
    no PDF consolidado)
  - `backend/tests/test_ai_chains_retry.py` (4 testes novos: recuperação
    após falha transitória, erro repassado após esgotar tentativas,
    truncamento)
  - `frontend/src/index.css` (`@keyframes np-spin`, reaproveitável em
    qualquer ícone de carregamento)
  - `frontend/src/pages/NovoAtendimento.tsx` (aviso de geração destacado,
    navegação para o histórico após salvar o texto revisado)
- **Como testar/ver funcionando:**
  1. `cd backend && source .venv/bin/activate && python -m pytest tests/ -v`
     — devem passar 123 de 123 testes.
  2. Pela tela: gerar um laudo em "Novo Atendimento" — o aviso rosa com
     ícone girando aparece durante a geração do texto. Editar o texto e
     clicar em "Salvar Texto Revisado" — deve levar direto para o
     Histórico do Paciente.
- **Pendências/observações:**
  - As retentativas reduzem bastante os erros intermitentes, mas não
    eliminam 100% das falhas possíveis de um provedor de IA externo (ex.:
    chave inválida, provedor fora do ar por muito tempo) — esses casos
    continuam mostrando a mensagem de erro clara já existente, como
    esperado.
  - Não foi possível reproduzir o erro relatado do PDF consolidado com uma
    chamada de IA real nesta máquina (falta chave de API válida) — a
    correção foi feita por análise de código (causas mais prováveis:
    falha transitória do provedor e prompt grande demais ao combinar
    vários laudos), não por reprodução direta do sintoma.

## Bloco de segurança: chave de IA criptografada e limite de tentativas de login

- **Status:** ✅ Pronto
- **Data:** 2026-09-13
- **Origem:** Pedido direto do usuário depois de eu listar pontos de
  melhoria antes de um uso real com pacientes — este é o primeiro dos 3
  blocos combinados (segurança → infraestrutura → produto).
- **O que foi feito:**
  - **Chave de IA criptografada em repouso**: a chave de API que cada
    psicóloga cadastra em "Configurações" agora é criptografada antes de
    salvar no banco (`cryptography.fernet`, chave derivada do
    `JWT_SECRET` do servidor) — antes ficava em texto puro na tabela
    `ai_settings`. Chaves já salvas antes desta mudança continuam
    funcionando normalmente (o sistema reconhece que não estão
    criptografadas e as recriptografa na próxima vez que forem salvas).
  - **Limite de tentativas de login**: depois de 5 tentativas erradas com
    o mesmo e-mail em 15 minutos, o login fica temporariamente bloqueado
    (erro claro, "muitas tentativas..."), mesmo que a senha certa seja
    digitada depois. Um login correto zera o contador. É um contador em
    memória do próprio processo (coerente com a arquitetura de serviço
    único do projeto) — reseta se o servidor reiniciar.
- **Arquivos criados/alterados:**
  - `backend/app/core/security.py` (`encrypt_secret`, `decrypt_secret`)
  - `backend/app/core/rate_limit.py` (novo)
  - `backend/app/api/ai_settings.py`, `backend/app/services/ai/resolver.py`
    (criptografar/descriptografar a chave), `backend/app/api/auth.py`
    (checagem de bloqueio no login)
  - `backend/app/models/ai_settings.py` (coluna `api_key` virou `Text` —
    o valor criptografado é maior que a chave original) + migration
    `ccbad30d88c7_amplia_coluna_api_key_para_texto_chave_.py`
  - `backend/requirements.txt` (`cryptography`, já era dependência
    transitiva, agora declarada explicitamente)
  - `backend/tests/test_encryption.py` (novo, 3 testes),
    `backend/tests/test_ai_settings.py` (+1 teste: chave nunca aparece em
    texto puro no banco), `backend/tests/test_auth.py` (+2 testes de
    bloqueio/desbloqueio), `backend/tests/conftest.py` (fixture para
    isolar o contador de tentativas entre testes + acesso ao banco de
    teste para inspeção direta)
- **Como testar/ver funcionando:**
  1. `cd backend && source .venv/bin/activate && alembic upgrade head &&
     python -m pytest tests/ -v` — devem passar 129 de 129 testes.
  2. Pela tela: errar a senha 5 vezes seguidas com o mesmo e-mail — a 6ª
     tentativa (mesmo com a senha certa) mostra "muitas tentativas,
     aguarde alguns minutos".
- **Pendências/observações:**
  - **Recuperação de senha por e-mail não entra nesta rodada** — decisão
    combinada com o usuário: precisa de um serviço de e-mail que ainda
    não existe no projeto. Continua documentada como pendência.
  - **HTTPS automático também não entra nesta rodada** — já é resolvido
    por Render/Fly (recomendados em `APRESENTACAO.md`); forçar
    redirecionamento no próprio código arriscaria quebrar quem já está
    atrás de um proxy que termina o TLS.
  - O bloqueio de login é por e-mail, não por IP — é a proteção mais
    relevante para este sistema (evita adivinhar a senha de uma conta
    específica), mas não impede um único atacante de tentar e-mails
    diferentes rapidamente. Suficiente para o risco atual (poucas
    contas, uso interno de clínica), não para um sistema exposto a
    milhares de usuários.

## Bloco de infraestrutura: storage configurável (S3) e backup do banco

- **Status:** ✅ Pronto
- **Data:** 2026-09-13
- **Origem:** Segundo dos 3 blocos combinados com o usuário (segurança →
  infraestrutura → produto), depois da lista de pontos de melhoria.
- **O que foi feito:**
  - **Fotos e PDFs deixam de depender só de disco local**: criada uma
    camada de armazenamento (`services/storage.py`) que hoje continua
    salvando tudo em disco (`backend/storage/...`, comportamento de
    sempre) mas passa a aceitar um bucket compatível com S3 (AWS,
    Cloudflare R2, Backblaze B2...) via variáveis de ambiente opcionais
    (`S3_BUCKET` e companhia — ver `.env.example`). Sem configurar nada,
    nada muda; configurando, os arquivos passam a ir para o bucket sem
    precisar tocar em mais nada do sistema.
  - **PDF consolidado agora fica salvo** (era gerado e baixado na hora,
    sem ficar guardado em lugar nenhum — pendência antiga, ver entrega
    "Adição: edição do histórico..."). Cada parecer consolidado vira um
    registro (`ConsolidatedReport`) com o texto e o PDF salvos; dá para
    listar os pareceres já gerados de um paciente e rebaixar o PDF depois
    **sem chamar a IA de novo**.
  - **Script de backup do banco** (`backend/scripts/backup_db.sh`) — roda
    um `pg_dump` compactado; documentado em `DEPLOY.md` com exemplo de
    agendamento via cron.
- **Arquivos criados/alterados:**
  - `backend/app/services/storage.py` (novo — `LocalDiskStorage`,
    `S3Storage`, `get_photos_storage`, `get_reports_storage`)
  - `backend/app/core/config.py` (variáveis `s3_*`, todas opcionais)
  - `backend/app/api/patients.py` (fotos), `backend/app/services/pdf.py`
    (PDFs) — passam a usar a camada de storage em vez de escrever direto
    em disco; `file_path`/`pdf_path` agora guardam uma chave lógica, não
    um caminho absoluto
  - `backend/app/models/consolidated_report.py` (novo) + migration
    `d11dc0afd0e2_adiciona_consolidated_reports.py`
  - `backend/app/schemas/report.py` (`ConsolidatedReportOut`)
  - `backend/app/api/reports.py` (`POST .../consolidated-pdf` agora
    persiste; `GET /api/patients/{id}/consolidated-reports` e
    `GET /api/consolidated-reports/{id}/pdf` novos)
  - `backend/app/models/ai_settings.py` + migration
    `ccbad30d88c7_...` (já registrada no bloco de segurança)
  - `backend/requirements.txt` (`boto3`)
  - `backend/scripts/backup_db.sh` (novo)
  - `.env.example`, `DEPLOY.md` (variáveis novas + checklist de backup)
  - Testes: `backend/tests/test_storage.py` (novo, 4 testes),
    `backend/tests/test_consolidated_pdf.py` (+3 testes: persistência,
    listagem, redownload sem nova chamada de IA, isolamento por dono),
    `test_patient_photos.py`/`test_reports_pdf.py` (ajustados para o novo
    ponto de mock do storage)
- **Como testar/ver funcionando:**
  1. `cd backend && source .venv/bin/activate && alembic upgrade head &&
     python -m pytest tests/ -v` — devem passar 136 de 136 testes.
  2. Pela tela: gerar um PDF consolidado no Histórico do Paciente — ele
     continua baixando na hora como antes, mas agora existe um registro
     dele guardado (checar via `GET /api/patients/{id}/consolidated-reports`
     pela documentação `/docs`, já que a lista ainda não apareceu na tela
     — isso é o próximo bloco, produto/UX).
- **Pendências/observações:**
  - O `S3Storage` foi testado com o cliente `boto3` simulado (sem
    depender de credenciais reais/rede) — não foi testado contra um
    bucket de verdade nesta máquina.
  - A lista de pareceres consolidados salvos ainda não tem uma tela — só
    a API. A tela entra no próximo bloco (produto/UX).
  - Backup automático de verdade (rodando sozinho, sem alguém disparar)
    depende de onde o sistema for hospedado — o script cobre a parte que
    dá para deixar pronta agora; agendar (cron, ou o backup gerenciado da
    plataforma escolhida) é passo de implantação, não de código.

## Bloco de produto/UX: editor visual de modelos, formulário mais fácil, painel de uso, testes de frontend

- **Status:** ✅ Pronto
- **Data:** 2026-09-13
- **Origem:** Terceiro e último dos 3 blocos combinados com o usuário
  (segurança → infraestrutura → produto), fechando a lista de pontos de
  melhoria levantada antes de um uso real com pacientes.
- **O que foi feito:**
  - **Editor visual de modelos de laudo**: a tela "Modelos De Laudo" não
    depende mais só de editar JSON cru. Agora tem um formulário de
    verdade — adicionar/remover área, campo, faixa etária (Portage),
    faixa de classificação, tudo com campos e seletores, sem precisar
    entender a sintaxe do JSON. Continua existindo um "Modo Avançado
    (JSON)" para quem preferir editar o texto direto (ex.: ajustes finos
    depois de importar um documento com a IA) — os dois modos ficam
    sincronizados.
  - **Formulário de atendimento mais fácil de preencher**: barra de
    progresso mostrando "X de Y perguntas respondidas", e atalhos de
    navegação por área quando o modelo tem muitas (ex.: CARS, 15 áreas) —
    facilita não se perder em formulários longos.
  - **Painel de uso no Dashboard**: além de "Pacientes Cadastrados", agora
    mostra "Laudos Gerados", "Laudos Nos Últimos 30 Dias" e um resumo de
    quantos laudos foram feitos por escala — dá pra acompanhar o uso do
    sistema sem abrir a documentação da API.
  - **Testes automatizados de frontend**: configurado Vitest + Testing
    Library (não existia nenhum teste de frontend antes). 14 testes novos
    cobrindo componentes com lógica de verdade: botão (clique/desabilitado),
    campo dinâmico do formulário (cada tipo de campo chama `onChange` com
    o valor certo), tela de login (mostra erro de credencial), e o editor
    visual de modelos (adicionar área/campo/faixa reflete na tela).
- **Arquivos criados/alterados:**
  - `frontend/src/components/TemplateBuilder.tsx` (novo — editor visual)
  - `frontend/src/pages/ModelosDeLaudo.tsx` (usa o editor visual +
    alternância para modo JSON avançado)
  - `frontend/src/pages/NovoAtendimento.tsx` (barra de progresso, atalhos
    de navegação por área), `frontend/src/components/ds/Card.tsx` (+ prop
    `id`, usado para as âncoras)
  - `backend/app/api/stats.py`, `backend/app/schemas/stats.py` (novos —
    `GET /api/stats/summary`), `backend/app/main.py` (router registrado)
  - `frontend/src/api/stats.ts` (novo), `frontend/src/pages/Dashboard.tsx`
    (blocos de estatística novos)
  - `frontend/src/api/types.ts` (`ClassificationRange`/`item_scoring`
    tipados corretamente — antes eram `Record<string, unknown>`;
    `StatsSummary`, `ConsolidatedReport`)
  - `frontend/vite.config.ts`, `frontend/src/test/setup.ts` (novo),
    `frontend/package.json` (`vitest`, `@testing-library/*`, `jsdom`,
    script `test`)
  - Testes novos: `frontend/src/components/ds/Button.test.tsx`,
    `frontend/src/components/DynamicField.test.tsx`,
    `frontend/src/components/TemplateBuilder.test.tsx`,
    `frontend/src/pages/Login.test.tsx` — 14 testes
  - `backend/tests/test_stats.py` (novo, 4 testes)
- **Como testar/ver funcionando:**
  1. `cd backend && source .venv/bin/activate && python -m pytest tests/ -v`
     — devem passar 140 de 140 testes.
  2. `cd frontend && npx tsc --noEmit && npm run build && npm run test` —
     typecheck, build e os 14 testes novos de frontend, todos limpos.
  3. Pela tela: em "Modelos De Laudo", clicar em "Ou Montar Um Modelo Do
     Zero" e montar uma escala simples só clicando em "Adicionar
     Área"/"Adicionar Campo" — sem escrever nenhum JSON à mão; em "Novo
     Atendimento", escolher a escala CARS e ver a barra de progresso subir
     conforme preenche; no Dashboard, ver os novos blocos de estatística.
  4. Testado de ponta a ponta via API real nesta máquina: build de
     produção do frontend + backend real (banco do zero, todas as
     migrations), registro, bloqueio de login após 5 tentativas erradas,
     chave de IA salva e confirmada criptografada direto no arquivo do
     banco, cadastro de template/paciente/laudo, estatísticas corretas, e
     download de PDF confirmando que o `pdf_path` salvo é uma chave
     lógica (não mais um caminho absoluto de disco).
- **Pendências/observações:**
  - Isso fecha os 3 blocos de melhoria combinados nesta sessão
    (segurança → infraestrutura → produto). Pendências que ficaram de
    fora por decisão explícita do usuário: recuperação de senha por
    e-mail (falta um serviço de e-mail) e contas multi-profissional
    (mantido 1 conta = 1 profissional) — ambas documentadas, não
    esquecidas.
  - Os testes de frontend cobrem componentes com lógica própria, não a
    aplicação inteira — não havia nenhum teste de frontend antes desta
    entrega, então qualquer cobertura é um ganho líquido; expandir para
    mais páginas é um próximo passo natural, não uma urgência.
  - O bundle de produção do frontend passou de ~150KB para ~163KB
    (gzip) com todas essas adições — o Vite avisa que o chunk principal
    já passa de 500KB (antes da compressão); não é um problema para o
    tamanho atual do sistema, mas code-splitting é uma otimização válida
    se o app continuar crescendo.

## Mudança de arquitetura: protocolo fixo substitui o motor de templates configuráveis

- **Status:** ✅ Pronto
- **Data:** 2026-09-20
- **Origem:** Decisão explícita do usuário — o motor de templates
  configuráveis (`schema_json` por escala, cadastrados pela psicóloga) foi
  considerado um erro de concepção desde o início do projeto. O usuário já
  tinha um protótipo HTML standalone completo, testado e validado na
  prática pela psicóloga (`formulario_prototipo_cliente.html`,
  originalmente em `referencia_cliente/`), e pediu para esse arquivo virar
  "o coração do sistema", exatamente como está, em vez de recriar a lógica
  clínica em React/JSON.
- **O que foi feito:**
  - **`frontend/public/formulario-novo-paciente.html`** (novo): cópia
    byte-a-byte do protótipo original, sem nenhuma linha da lógica clínica
    alterada. Um segundo `<script>` foi acrescentado no fim do arquivo
    fazendo a ponte com o backend: cria paciente/template/laudo no
    primeiro "Salvar No Sistema", depois sincroniza **cada campo alterado
    automaticamente com o banco** (`PUT /api/reports/{id}/answers`,
    debounce ~1,2s) — autosave real, não só `localStorage`. Botão
    "Concluir E Ver Histórico" separado, navegando a janela pai (por causa
    do iframe) para o Histórico do Paciente.
  - **Novo `rule_type` "custom_form"** (`backend/app/schemas/
    report_template.py`, `rules_engine/engine.py`): não calcula nada — o
    HTML já pontuou tudo sozinho. `POST /api/templates/
    custom-form-avaliacao` (novo endpoint, idempotente por psicóloga)
    garante o `ReportTemplate` interno fixo, sem precisar de tela de
    cadastro.
  - **PDF direto do HTML já pronto** (`backend/app/services/pdf.py`): para
    `rule_type="custom_form"`, `render_report_pdf` pega
    `report.generated_text` (HTML completo, com `<style>` embutido,
    montado pelo bootstrap a partir do laudo já gerado pelo formulário) e
    manda direto pro WeasyPrint, sem passar pelas tabelas de
    pontuação/gráfico Matplotlib do motor antigo. O gráfico de
    probabilidades (Chart.js/canvas) é congelado como `<img>` antes de
    enviar, porque o WeasyPrint não executa JavaScript.
  - **Novo endpoint de autosave**: `PUT /api/reports/{id}/answers`
    (`backend/app/schemas/report.py::ReportAnswersUpdate`,
    `backend/app/api/reports.py::update_answers`) — substitui
    `answers_json` inteiro, sem tocar no resto do laudo.
  - **"Novo Atendimento" embutido no sistema**: a rota `/atendimento/novo`
    (`frontend/src/pages/NovoAtendimento.tsx`, reescrita do zero) agora só
    embute o HTML standalone num `<iframe>` dentro do layout do app
    (sidebar/cabeçalho continuam visíveis) — nada abre mais em nova aba. O
    item de menu "Novo Atendimento" e os botões "Novo Atendimento"/"+ Novo
    Laudo Para Este Paciente" (Dashboard, Histórico do Paciente) foram
    atualizados para essa rota, passando `?paciente=<id>` quando aplicável
    (o bootstrap do HTML pré-carrega a identificação).
  - **Removido da navegação e do código**: páginas `pages/
    ModelosDeLaudo.tsx`, `pages/NovoAtendimento.tsx` antigo (formulário
    dinâmico via `schema_json`) e `components/DynamicField.tsx` (+ teste)
    foram **apagadas**, não só desligadas. Item de menu "Modelos De
    Laudo" removido. Formulário rápido de cadastro de paciente inline no
    Dashboard removido (paciente agora só é criado pelo fluxo do
    formulário standalone).
  - **Cache do `index.html`**: `backend/app/main.py` passou a responder o
    fallback de SPA com `Cache-Control: no-cache`, para o navegador sempre
    revalidar e pegar o bundle JS mais recente depois de um novo build —
    sem isso, uma aba já aberta antes de um deploy continuava rodando o JS
    antigo indefinidamente (bug real observado nesta sessão).
  - **Banco de dados zerado a pedido do usuário**: todos os laudos, logs
    de edição, PDFs consolidados e `ReportTemplate` antigos (CARS/ATA/
    SNAP-IV/Portage de exemplo) foram apagados do banco de desenvolvimento
    — pacientes cadastrados foram preservados. PDFs órfãos removidos do
    storage local.
  - **`referencia_cliente/` apagada**: continha o protótipo original (já
    copiado para o novo local) e PDFs de exemplo com dados reais de
    pacientes (nome completo, laudo assinado) — não deveriam continuar no
    repositório sem necessidade depois que a integração real foi feita.
    Backup intocado do HTML original mantido fora do repositório, em
    `/home/samu/formpsico/.claude/formulario_prototipo_cliente.html`.
  - **Documentação atualizada**: `CLAUDE.md` (seções 1, 2, 3, 6 e 9
    reescritas), `SPEC.md` (aviso no topo + nova seção 7 descrevendo a
    arquitetura atual), `APRESENTACAO.md` (seções 1-4 e 6 reescritas para
    o público não técnico), `README.md` e `DEPLOY.md` (referências a
    `seed_templates`/modelos corrigidas).
- **Arquivos criados/alterados:**
  - `frontend/public/formulario-novo-paciente.html` (novo)
  - `backend/app/schemas/report_template.py`, `rules_engine/engine.py`,
    `services/pdf.py`, `api/templates.py`, `schemas/report.py`,
    `api/reports.py`, `main.py`
  - `frontend/src/App.tsx`, `components/Layout.tsx`, `components/ds/
    SidebarNav.tsx`, `pages/Dashboard.tsx`, `pages/HistoricoPaciente.tsx`,
    `pages/NovoAtendimento.tsx` (reescrita)
  - Apagados: `frontend/src/pages/ModelosDeLaudo.tsx`,
    `frontend/src/components/DynamicField.tsx` (+ `.test.tsx`),
    `referencia_cliente/` (pasta inteira)
  - `CLAUDE.md`, `SPEC.md`, `APRESENTACAO.md`, `README.md`, `DEPLOY.md`
- **Como testar/ver funcionando:**
  1. `cd backend && ./.venv/bin/python3 -m pytest tests/ -v` — 140 de 140
     testes passando (nada quebrou no motor de regras legado).
  2. `cd frontend && npx tsc --noEmit && npm run build && npm run test` —
     typecheck, build e 10 testes de frontend, todos limpos.
  3. Pela tela: login → "Novo Atendimento" (menu ou Dashboard) → formulário
     completo aparece embutido no sistema → preencher nome/data de
     nascimento e ver a linha de status confirmando o autosave conforme
     digita → "Salvar No Sistema" → "Concluir E Ver Histórico" → laudo
     aparece no Histórico do Paciente → baixar PDF.
  4. Testado de ponta a ponta via API real nesta máquina: criar paciente,
     garantir template idempotente (chamado duas vezes, mesmo id), criar
     laudo, autosave de resposta via `PUT /answers`, salvar texto, baixar
     PDF (`HTTP 200`, `PDF document, version 1.7` confirmado via `file`).
- **Pendências/observações:**
  - Fotos do paciente continuam só embutidas em base64 no laudo (não
    entram na galeria oficial `/api/patients/{id}/photos`) — documentado
    como próximo passo, não bloqueia o uso atual.
  - Motor de regras dinâmico, geração de texto por IA e CRUD/import de
    templates **continuam no backend**, só não são mais chamados por
    nenhuma tela — decisão deliberada de não remover código que pode
    voltar a ser útil, documentada em `CLAUDE.md` seção 9 para não
    confundir uma sessão futura.
  - `.venv` do backend tem um `shebang` quebrado (caminho antigo da
    máquina) — usar `./.venv/bin/python3 -m uvicorn ...` em vez do script
    `uvicorn` direto; documentado em `CLAUDE.md` seção 9.

## Fotos do paciente passam a sincronizar com a galeria oficial

- **Status:** ✅ Pronto
- **Data:** 2026-09-20
- **Origem:** Pendência conhecida, documentada desde a entrega da mudança
  de arquitetura (protocolo fixo): o formulário standalone embutia fotos
  só como base64 no laudo/PDF, sem usar a galeria oficial de fotos do
  paciente já existente no backend (`/api/patients/{id}/photos`, com tela
  própria em "Fotos Do Paciente" no Histórico do Paciente).
- **O que foi feito:** `frontend/public/formulario-novo-paciente.html` —
  só no segundo `<script>` (bootstrap de integração); nenhuma linha da
  lógica clínica original (~897 linhas) foi tocada:
  - `enviarFotosNovasParaGaleria()`: depois que o paciente existe no banco
    (dentro de `salvarNoSistema()`, logo após `garantirRegistroCriado()`),
    converte cada foto ainda não enviada (sem `_photoId`) de volta para
    `File` (`dataUrlParaArquivo()`) e faz `POST
    /api/patients/{id}/photos` (multipart, função nova `apiFetchArquivo`).
    A foto guarda o `_photoId` devolvido para não ser reenviada de novo.
  - `carregarFotosDaGaleria()`: quando o formulário abre para um paciente
    já existente (`?paciente=<id>`) e ainda não tem nenhuma foto
    carregada, busca as fotos já salvas na galeria
    (`GET /api/patients/{id}/photos`), baixa cada uma como blob
    autenticado e converte para dataURL (`baixarFotoComoDataUrl`), para
    que continuem aparecendo e sendo embutidas no laudo normalmente.
  - `interceptarRemocaoDeFoto()`: envolve (sem editar) a função original
    `removerFotoPaciente` — se a foto removida já tinha `_photoId`,
    também apaga da galeria (`DELETE
    /api/patients/{id}/photos/{photoId}`).
  - Upload é best-effort: se o arquivo não for de um formato aceito pela
    galeria (`.jpg/.jpeg/.png/.webp`) ou a chamada falhar, a foto continua
    funcionando no laudo/PDF (base64 embutido, inalterado) — só não
    aparece na galeria oficial.
  - Nenhuma mudança no backend — os endpoints de fotos já existiam,
    prontos e testados (`backend/tests/test_patient_photos.py`).
- **Arquivos alterados:** `frontend/public/formulario-novo-paciente.html`,
  `CLAUDE.md` (seção 9), `SPEC.md` (seção 7).
- **Como testar/ver funcionando:**
  1. `cd backend && ./.venv/bin/python3 -m pytest tests/ -v` — 140 de 140
     continuam passando (nenhum endpoint de backend foi alterado).
  2. `cd frontend && npx tsc --noEmit && npm run build` — typecheck e
     build de produção limpos.
  3. Pela tela: "Novo Atendimento" → adicionar uma ou mais fotos na seção
     de identificação → "Salvar No Sistema" → abrir o Histórico do
     Paciente → card "Fotos Do Paciente" deve mostrar as mesmas fotos.
     Remover uma foto no formulário e salvar de novo deve tirá-la também
     do card. Reabrir "+ Novo Laudo Para Este Paciente" para o mesmo
     paciente deve pré-carregar as fotos já enviadas antes.
- **Pendências/observações:**
  - Formatos fora de `.jpg/.jpeg/.png/.webp` (ex.: HEIC de iPhone) não
    entram na galeria oficial (a rota de upload já rejeitava esses
    formatos antes desta entrega) — continuam funcionando no laudo/PDF.

## Relatório: CARS item a item (Fase 1 de aproximação ao layout de referência)

- **Status:** 🟡 Parcial (fase 1 de um trabalho maior, em andamento)
- **Data:** 2026-09-20
- **Origem:** Usuário pediu que o PDF/Word/formulário gerados pelo sistema
  fiquem estruturalmente idênticos a um relatório real de referência
  (`RELATÓRIO FINAL GUSTAVO HENRIQUE`). Esse relatório usa a CARS, a ATA e
  três checklists de "Habilidades" item a item, com gráficos próprios —
  nada disso existia no formulário (só uma nota total por escala). Os
  itens exatos da CARS vieram de uma planilha real da psicóloga
  (`CARS_Gustavo Henrique Amancio Lopes(2).xlsx`, aba "CARS"), sem nenhum
  texto inventado.
- **O que foi feito** (só em `frontend/public/formulario-novo-paciente.html`):
  - Novo array `carsItens`: as 15 áreas oficiais da CARS, cada uma com os
    4 textos de gravidade (Normal/Leve/Moderado/Severo) extraídos da
    planilha da psicóloga.
  - `montarFormulario()` agora renderiza um `<select>` por área (15 ao
    todo, id `cars_0` a `cars_14`), com os 4 graus e os 3 valores
    intermediários (1,5 / 2,5 / 3,5) que a psicóloga usa na prática.
  - `calcularCARS()`: soma as 15 áreas e preenche o campo `Pontuação CARS`
    automaticamente (só quando todas as 15 estiverem preenchidas) — o
    campo antes era digitado manualmente, agora é sempre calculado a
    partir dos itens, exatamente como a planilha original faz. A
    classificação (Normal/Leve-Moderado/Grave) que já existia
    (`atualizarInterpretacoes()`) não foi alterada — só passou a receber
    o total calculado em vez do total digitado.
  - `gerarTabelaCARS()` e um gráfico de linha (`graficoCARS`, Chart.js)
    foram adicionados à seção "10. ATA E CARS" do relatório gerado,
    mostrando pontuação por área — igual ao gráfico da página 11 do
    relatório de referência.
  - `congelarGraficoComoImagem()` (bootstrap de integração) foi
    generalizada para congelar **todos** os gráficos do relatório como
    imagem (antes só congelava o gráfico de probabilidades) — necessário
    para o gráfico novo da CARS também aparecer no PDF gerado pelo
    backend (WeasyPrint não executa JavaScript/Canvas).
- **O que NÃO foi alterado:** nenhuma lógica clínica pré-existente (ATA,
  SNAP-IV, Portage, M-CHAT, quadro DSM-5-TR, funções executivas atuais,
  cálculo de probabilidades) — só a CARS, que antes era só um número
  digitado, virou um cálculo a partir dos itens reais.
- **Como testar:** "Novo Atendimento" → seção "11. Pontuações ATA E CARS"
  → selecionar o grau das 15 áreas da CARS → conferir que o campo
  "Pontuação CARS" preenche sozinho e a interpretação muda de faixa
  corretamente → "Gerar Relatório" → conferir a tabela e o gráfico de
  linha da CARS no relatório em tela.
- **Pendências (próximas fases, aguardando confirmação da psicóloga a
  cada etapa):**
  - ATA item a item (22 categorias, cada uma com pontuação máxima
    própria) — dados já levantados da planilha `PROTOCOLO ATA(1).xlsx`,
    implementação ainda não feita.
  - 3 checklists de "Habilidades" (Cognitivas/Metacognitivas,
    Socioemocionais/Comunicativas, Motoras/Sociomotoras, ~31 itens) com
    gráficos de barra — dados já levantados do próprio PDF de referência,
    implementação ainda não feita.
  - Gráficos extras do SNAP-IV (pontos por categoria + % por categoria) e
    do Portage por área (hoje é só um percentual agregado).
  - Reagrupamento do quadro de observações em 4 áreas fixas
    (Comunicação/Interação, Padrões Comportamentais, Sensorial/Emocional,
    Aprendizagem) como no relatório de referência.
  - Layout de cabeçalho (foto do paciente + caixa de identificação) e
    rodapé de contato repetidos por página no PDF/impressão.
  - Quadro de Funções Executivas por faixa etária do relatório de
    referência: por decisão do usuário, **não será copiado** — o bloco
    atual de Funções Executivas do sistema permanece como está.

## Formulário "gamificado": wizard com progresso, etapas e feedback de conclusão

- **Status:** ✅ Pronto
- **Data:** 2026-09-20
- **Origem:** Pedido do usuário para melhorar a UX do preenchimento de um
  formulário longo (20 seções), tornando o progresso visível e o
  preenchimento menos cansativo.
- **O que foi feito:** um **terceiro `<script>`**, independente da lógica
  clínica original (primeiro script) e do bootstrap de integração com o
  backend (segundo script), adicionado só em
  `frontend/public/formulario-novo-paciente.html`:
  - As 20 seções (`<h2>1...` a `<h2>20...`) são divididas em
    "etapas" (`.etapa-form`) automaticamente via JavaScript, sem duplicar
    HTML — os elementos originais são só movidos para dentro de um
    `<section>` por etapa, nada foi reescrito manualmente.
  - Barra de progresso geral fixa no topo (`% Do Formulário Preenchido`,
    contando campos de texto/número/seleção não somente-leitura e
    ignorando campos condicionalmente ocultos como os "Descreva..." que só
    aparecem quando a resposta é "Sim").
  - Barra de etapas (stepper) clicável, com círculo numerado por etapa;
    vira verde com "✓" quando todos os campos daquela etapa estão
    preenchidos.
  - Botões "Etapa Anterior"/"Próxima Etapa" ao final de cada seção; a
    última etapa tem "Ir Para Ações Finais" que rola até os botões de
    salvar/gerar relatório (que continuam sempre visíveis, fora do fluxo
    de etapas).
  - Ao completar uma etapa pela primeira vez, aparece um toast
    ("✓ Seção Concluída: ...") no canto da tela por ~2,6s.
  - Ao abrir o formulário (inclusive com dados de um paciente já
    existente, carregados de forma assíncrona pelo bootstrap), o wizard
    pula automaticamente para a primeira etapa ainda incompleta.
  - **Impressão preservada:** ao imprimir o formulário em branco
    (`imprimirFormularioPDF()`), uma regra CSS (`.print-form
    .etapa-form{display:block!important}`) faz todas as etapas
    aparecerem de novo, junto com `@media print` — a função de imprimir
    não foi alterada e continua imprimindo o formulário inteiro, não só a
    etapa atual.
  - A "cópia editável" salva (`salvarCopiaEditavelPaciente()`) também
    funciona normalmente: como o wizard reconstrói a barra de progresso e
    religa os cliques toda vez que a página carrega (em vez de confiar em
    manipuladores de evento que não sobrevivem ao salvar o HTML), o
    arquivo salvo abre com o wizard funcionando igual.
- **O que NÃO foi alterado:** nenhuma função de lógica clínica, nenhuma
  função do bootstrap de integração com o backend — é uma camada de UX
  por cima, adicionada como um script novo e separado.
- **Como testar:** abrir "Novo Atendimento" → conferir a barra de
  progresso e o stepper no topo → preencher uma seção inteira e ver o
  círculo virar verde com o toast de confirmação → clicar em etapas
  diferentes do stepper para navegar → testar "Imprimir Formulário Em
  PDF" e confirmar que todas as 20 seções aparecem na impressão, não só a
  etapa ativa na tela.
- **Verificação feita nesta sessão:** simulação completa em ambiente
  isolado (jsdom) confirmando 20 etapas criadas corretamente, navegação
  por clique funcionando, cálculo de progresso e detecção de etapa
  completa corretos, e que `#statusSalvamento`/os botões de ação
  permanecem fora do fluxo de etapas (sempre visíveis). Testes de backend
  (140/140) e build/typecheck do frontend seguem limpos.
- **Bug real encontrado e corrigido após o usuário reportar "os campos
  sumiram"**: o jsdom (usado na verificação acima) só confere estrutura e
  lógica, não faz renderização visual — por isso não pegou este bug.
  Instalei um Chromium headless (Playwright) só para diagnosticar e
  confirmei visualmente: `dividirFormularioEmEtapas()` reanexava as 20
  etapas com `form.appendChild(etapa)`, que sempre adiciona ao final da
  lista atual de filhos — como `#statusSalvamento`/`.acoes` já eram os
  únicos filhos restantes do `<form>` naquele momento, as etapas acabavam
  entrando DEPOIS deles, invertendo a ordem original. Isso fazia a função
  que esconde os botões de ação até a última etapa
  (`montarBlocoAcoesFinais`) varrer "tudo depois de `#statusSalvamento`" e
  engolir as 20 etapas inteiras dentro do bloco escondido — resultando em
  formulário com progresso/stepper visíveis, mas nenhum campo aparecendo.
  Corrigido trocando `form.appendChild(etapa)` por
  `form.insertBefore(etapa, referenciaFixaAoStatusSalvamento)`, que
  preserva a ordem correta (etapas primeiro, ações por último). Reconferido
  com o Chromium headless: 20 etapas como filhas diretas do formulário,
  altura do formulário voltando ao normal, campos visíveis. Também ajustei
  o toast de "seção concluída" para não disparar na carga inicial (seções
  com texto padrão pré-preenchido, como "Considerações Finais", apareciam
  como "recém-concluídas" assim que a página abria). 
## Relatório idêntico ao modelo oficial (Parecer Neuropsicopedagógico) em PDF e Word

**Status:** ✅ Concluído (2026-09-23)

**O que mudou:** o relatório gerado pelo formulário agora segue a estrutura
do modelo oficial da psicóloga (relatório "Parecer Neuropsicopedagógico /
Análise Comportamental"), página a página: moldura em todas as páginas, logo
no topo e contatos no rodapé; cabeçalho com foto + caixa de identificação;
faixa "PARECER NEUROPSICOPEDAGÓGICO / ANÁLISE COMPORTAMENTAL"; metodologia;
anamnese e histórico em tópicos; quadro comparativo; texto + gráfico da CARS;
texto + gráfico + tabela da ATA; fotos; tabelas e gráficos de habilidades
(Sim/Às vezes/Não); perfil das funções executivas; gráfico de idade de
desenvolvimento (Portage); análise por área em faixas cinza; SNAP-IV com os
dois gráficos; síntese clínica; gráfico de déficits das funções executivas;
pizza por domínio; encaminhamento, hipóteses com CID, observação e assinatura.

- **Um único documento para tudo:** `gerarDocumentoLaudoHTML()` (novo bloco
  `<script>` no formulário) monta o HTML usado na pré-visualização, salvo
  no laudo e convertido pelo backend.
- **Botões do formulário:** "Pré-Visualizar Relatório", "Gerar Word (DOCX)"
  e "Gerar PDF". PDF e Word vêm do backend: `POST /api/documents/pdf`
  (WeasyPrint) e `POST /api/documents/docx` (python-docx, Word editável de
  verdade, com moldura, cabeçalho/rodapé, tabelas e destaques).
- **Histórico:** novo "Baixar Word" (`GET /api/reports/{id}/docx`) ao lado
  de "Baixar PDF".
- **Campos novos no formulário:** idade cognitiva/marco do cabeçalho
  (preenchidos sozinhos), ATA por área (pontos + %), percentuais CARS/ATA do
  relatório, títulos das colunas do quadro, hipóteses em texto livre, perfil
  das 6 funções executivas (substitui a lista antiga de 7 funções),
  habilidades Sim/Às vezes/Não, domínios da pizza e a seção "Textos Do
  Parecer" com o texto-padrão do modelo (ajustado para o/a paciente
  conforme o sexo; marcação `**negrito**`, `==cinza==`, `!!amarelo!!`).
- **Fora do relatório (uso interno, avisado no formulário):** habilidades
  acadêmicas, TOD, M-CHAT, plano de intervenção e checklist de
  encaminhamentos — não existem no modelo oficial.
- **Correções encontradas na revisão:** respostas do Portage/M-CHAT não eram
  salvas (selects sem id); habilidades acadêmicas e linhas extras do quadro
  se perdiam ao reabrir; nome de paciente com acento quebrava o download do
  PDF; o PDF não busca mais nenhuma URL externa (só imagens embutidas).
- **SNAP-IV:** o texto usa o corte padrão de 6 itens "bastante/demais" por
  bloco (o modelo dizia 4 na metodologia; o texto-padrão foi ajustado para 6).

**Arquivos:** `frontend/public/formulario-novo-paciente.html`,
`backend/app/services/laudo_documento.py` (novo), `backend/app/api/documents.py`
(novo), `backend/app/api/reports.py`, `backend/app/services/pdf.py`,
`backend/app/main.py`, `backend/tests/test_documents_export.py` (novo),
`frontend/src/api/reports.ts`, `frontend/src/pages/HistoricoPaciente.tsx`,
`Dockerfile` (fonte Liberation, métrica do Arial).

**Como testar:** `npm run build` no frontend, subir o backend, abrir "Novo
Atendimento", preencher e clicar em "Gerar PDF" / "Gerar Word (DOCX)". Testes:
`cd backend && ./.venv/bin/python3 -m pytest` (150 passando).

### Ajuste (2026-09-23): Quadro Comparativo igual ao modelo (página 4)

O quadro da seção "Quadro De Observações Comportamentais" vinha do protótipo
original com 5 linhas sobre TEA/DSM-5-TR, por isso a página 4 não batia com
o modelo. Agora ele já vem com as **16 linhas do modelo (TDAH × TPAC)** e
colunas "Relação com TDAH" / "Relação com TPAC"; ganhou "+ Adicionar Linha",
"Remover Esta Linha" e "Restaurar Quadro Do Modelo". O botão "Gerar Quadro
Interpretativo Pelo Estudo De Caso" continua existindo (substitui o quadro e
troca os títulos das colunas para o formato DSM-5-TR). Tabela compactada
para caber numa página, como no modelo. Atendimentos já salvos mantêm o
quadro que tinham.

## Usabilidade do protocolo (heurísticas de Nielsen), fases e mensagens de erro

**Status:** ✅ Concluído (2026-09-23)

- **Nome correto: "protocolo".** Botões, fases, avisos, Histórico ("Protocolos
  Do Paciente", "+ Novo Protocolo…"), Painel e mensagens do backend deixaram de
  chamar o registro de "laudo" (o termo continua só onde é conteúdo clínico, ex.
  "Possui Laudo Anterior?", "não configura laudo médico").
- **Fases verdes de verdade.** Cada fase tem campos essenciais (marcados com *);
  o número fica verde ✓ quando eles estão completos, amarelo quando a fase está
  pela metade. Antes, a fase só ficava verde com *todos* os campos (inclusive
  opcionais) e 4 fases nunca podiam ficar verdes. Fases com texto-padrão
  (Metodologia, Quadro, Textos do Parecer, Plano, Considerações) só ficam verdes
  depois de abertas/revisadas. "Se sim, descreva" passa a ser exigido. M-CHAT
  conclui sozinho acima de 30 meses ("não se aplica"). No fim de cada fase:
  "Falta preencher nesta fase" com botões que levam direto ao campo.
- **Mensagens de erro:** validação do backend em português claro (antes:
  JSON técnico em inglês), falta de conexão, servidor fora do ar, sessão
  expirada (com "Entrar Novamente" e aviso na tela de login), fotos grandes
  demais — sempre dizendo o que fazer. `alert()` substituídos por avisos que não
  travam a tela, com "Tentar Novamente" quando faz sentido.
- **Heurísticas de Nielsen aplicadas:** status de salvamento sempre visível no
  topo (salvando / salvo / erro); barra fixa com Salvar Protocolo, Pré-Visualizar,
  Gerar PDF e Gerar Word em qualquer fase (antes só na última); botões mostram
  "Gerando…"; validação na hora (data de nascimento, valores 0–100, soma da
  pizza); salvar sem nome/data leva ao campo com o erro; autosave tenta de novo
  sozinho após falha de rede e antes de ir ao Histórico garante o último
  salvamento; atalhos Ctrl+S e Alt+←/→; ações raras e destrutivas em "Mais Opções".
- **Bug corrigido:** "Gerar Novo Formulário" dentro do sistema continuava
  gravando por cima do protocolo anterior; agora "Novo Protocolo" recomeça do zero.

**Arquivos:** `frontend/public/formulario-novo-paciente.html`,
`frontend/src/api/client.ts`, `frontend/src/pages/{Login,Dashboard,HistoricoPaciente,NovoAtendimento,Configuracoes}.tsx`,
`backend/app/core/errors.py` (novo), `backend/app/main.py`, `backend/app/api/{deps,reports,patients}.py`,
`backend/tests/test_error_messages.py` (novo).

## Stepper das fases, campos condicionais, UX do formulário e capa dos relatórios

**Status:** 🟡 Parcial (2026-09-30) — tudo implementado e testado; falta só
trocar a arte **provisória** da capa (`frontend/public/capa-relatorio.png`,
recortada de um print, baixa resolução) pela arte oficial em alta resolução.

- **Stepper das 23 fases:** trilho com rolagem suave, setas ‹ › e sombra nas
  bordas indicando que há mais fases; a fase ativa é centralizada
  automaticamente; itens do mesmo tamanho, rótulos em no máximo 2 linhas (nome
  completo no tooltip); legenda (Atual / Concluída / Com pendências / Não
  iniciada); cabeçalho fixo e mais baixo. Contador ("Fase X de 23 · N de 23
  concluídas"), barra e ✓ agora vêm do mesmo cálculo (a barra só chega a 100%
  com as 23 fases concluídas). No celular vira um seletor "Fase 4 de 23 · …".
- **Campos condicionais:** "Desde qual idade possui laudo?" só aparece com
  "Possui laudo anterior?" = Sim (transição suave), é essencial só quando
  visível e é apagado — inclusive no banco — ao voltar para Não. O mesmo para
  "Idade do desfralde" (só com Controle Total, Controle Diurno ou Escapes). Os
  demais pares Sim/Não ("Tem familiares laudados?", "Há histórico de transtorno
  na família?", terapias etc.) já escondiam, limpavam e só exigiam a descrição
  com Sim — conferidos, sem mudança. O relatório continua sem esses dados
  (decisão: ficam só na Fase 4).
- **Bug corrigido:** clicar em Sim/Não não disparava o salvamento automático no
  banco (só era salvo na próxima digitação).
- **UX:** espaçamento uniforme; rótulos ligados aos campos (clique e leitores
  de tela); Sim/Não com estado acessível; foco visível; "Próxima fase" marca
  junto de cada campo essencial vazio o que falta (sem bloquear); "Fase X de
  23" entre Anterior/Próxima; a barra de ações nunca cobre o formulário (altura
  medida); aviso ao sair do Novo Atendimento (menu, Sair, fechar/recarregar a
  aba) enquanto houver alterações não salvas no sistema; animações desligadas
  para quem prefere menos movimento; layout ajustado para celular.
- **Capa obrigatória:** pré-visualização, PDF (botão e Histórico) e Word
  começam com a capa em página inteira, sem cabeçalho/rodapé/moldura, e o
  conteúdo começa na página 2. O nome do paciente sai em maiúsculas na faixa
  roxa (fonte reduzida ou 2 linhas para nomes longos), numa imagem A4 de 300
  dpi montada num único ponto (`gerarCapaRelatorio()` no formulário). Laudos
  antigos ganham capa ao serem salvos de novo.

**Arquivos:** `frontend/public/formulario-novo-paciente.html`,
`frontend/public/capa-relatorio.png` (provisória), `frontend/public/fonts/`
(Fredoka, licença OFL), `frontend/src/pages/NovoAtendimento.tsx`,
`frontend/src/components/Layout.tsx`, `backend/app/services/laudo_documento.py`,
`backend/tests/test_documents_export.py`.

**Como testar:** Novo Atendimento → navegar pelas fases (setas, Alt+←/→,
celular); Fase 4: Sim → escolher idade → Não (campo some e é limpo);
Pré-Visualizar / Gerar PDF / Gerar Word → 1ª página é a capa com o nome.
Para trocar a arte: substituir `frontend/public/capa-relatorio.png` (A4 em pé,
2480×3508, sem o nome), ajustar `CAPA_FAIXA` no formulário se a faixa mudar de
lugar e rodar `npm run build`.

## Capa do relatório personalizável (capa padrão + capa por relatório)

**Status:** ✅ Pronto (2026-10-05)

- **O que mudou para a psicóloga:** a capa dos relatórios não é mais fixa.
  - **Capa padrão (Configurações → "Capa Do Relatório"):** enviar a imagem da
    capa (JPG, PNG ou WEBP, até 10 MB, A4 em pé — no Canva, exportar como PNG
    tamanho A4). Ela passa a valer para todos os relatórios.
  - **Nome do paciente opcional:** marcar "Escrever o nome do paciente na
    capa", arrastar sobre a prévia para marcar onde o nome fica e escolher a
    cor. Desmarcado, a capa sai exatamente como a imagem enviada.
  - **Capa só de um relatório:** no formulário, fase "Inserção De Fotos",
    bloco "Capa Deste Relatório (Opcional)" — a imagem enviada ali vale só
    para aquele relatório (com as mesmas opções de nome/cor) e fica salva
    junto com ele. "Usar A Capa Padrão" desfaz.
  - "Voltar À Capa Padrão" (Configurações) volta para a arte do sistema.
  - Imagem fora do formato A4 em pé é recortada ao centro (com aviso), nunca
    esticada.
- **Como funciona por dentro:** a capa continua sendo montada num único lugar
  (`gerarCapaRelatorio()` no formulário), agora escolhendo a arte nesta ordem:
  capa do relatório → capa padrão da psicóloga → `capa-relatorio.png`. PDF e
  Word não mudaram (já recebiam a capa pronta). A capa padrão fica no storage
  (`covers/`, local ou S3) e a posição/cor do nome em `psychologists.capa_config`;
  a capa de um relatório fica nas respostas do laudo (`__capaRelatorio`), como
  as fotos.
- **Arquivos:** `backend/app/api/auth.py` (`PUT/DELETE /api/auth/me/capa`,
  `GET /api/auth/me/capa/arquivo`, `PUT /api/auth/me/capa/config`),
  `backend/app/models/psychologist.py`, `backend/app/schemas/auth.py`,
  `backend/app/services/storage.py`, migration `b7c3e1f2a9d4`,
  `backend/tests/test_capa_personalizada.py`,
  `frontend/src/components/EditorCapa.tsx` (+ teste),
  `frontend/src/pages/Configuracoes.tsx`, `frontend/src/api/{auth,client,types}.ts`,
  `frontend/public/formulario-novo-paciente.html`.
- **Como testar:** `alembic upgrade head`; Configurações → enviar capa, marcar
  nome, desenhar a área, Salvar Capa; Novo Atendimento → Pré-Visualizar /
  Gerar PDF / Gerar Word: 1ª página é a capa nova com o nome na área marcada.
  Na fase de fotos, enviar outra capa só para esse relatório e recarregar a
  página: a capa continua lá.
- **Pendências/observações:** a arte provisória `capa-relatorio.png` só é
  usada por quem não enviou capa própria — trocá-la deixou de ser obrigatório.
  PDF como capa não é aceito (exportar a capa como imagem).

## Modelos de protocolo próprios (Configurações) e escolha do protocolo em Novo Atendimento

**Status:** ✅ Pronto (2026-10-05)

- **O que mudou para a psicóloga:**
  - **Configurações → "Modelos De Protocolo":** botão "Novo Modelo" abre um
    editor onde ela monta o próprio formulário, por seções:
    - **Perguntas** (texto curto/longo, Sim/Não com "descreva", múltipla
      escolha, caixas de seleção, data, número), com opção de marcar como
      essencial;
    - **Escala pontuada** (itens, respostas com pontos, faixas de
      classificação pelo total e gráfico de barras);
    - **Fotos** e **Texto livre**.
  - Cada seção tem o bloco **"No Relatório"**: mostrar ou não, como mostrar as
    respostas (lista, tabela ou só texto) e o **texto padrão** — com botões
    que inserem o nome, a idade, o/a, a resposta de uma pergunta, a pontuação
    e a classificação. Cada opção de resposta e cada faixa da escala pode ter
    um trecho que entra no relatório quando é escolhida.
  - "Pré-Visualizar Relatório" no editor mostra o relatório com respostas de
    exemplo. Modelos podem ser editados, duplicados e arquivados (arquivar
    não apaga nada: os relatórios já feitos continuam no histórico).
  - **Novo Atendimento:** havendo modelos próprios, a primeira tela pergunta
    qual protocolo usar. O protocolo padrão continua exatamente igual (o
    arquivo do formulário não foi alterado); sem modelos próprios, nada muda.
  - **Atendimento com um modelo próprio** funciona como o padrão: fases com
    progresso, identificação, "Texto Do Relatório" já preenchido em cada
    seção e atualizado pelas respostas até ela editar (depois disso não é
    mais sobrescrito; "Voltar Ao Texto Automático" desfaz), salvamento
    automático no sistema, capa só deste relatório, Pré-Visualizar, Gerar
    PDF, Gerar Word e "Concluir E Ver Histórico".
  - **Relatório no mesmo padrão visual:** capa (personalizável), cabeçalho
    com logo, moldura, rodapé, faixa do título, seções em faixas cinza,
    tabelas, gráfico, "Sobre a profissional" e assinatura.
  - **Histórico:** "Abrir Protocolo" reabre o atendimento. Editar o modelo
    depois não altera atendimentos já feitos (cada um guarda a versão do
    modelo da época).
- **Arquivos:** backend — `app/schemas/protocolo.py`, `app/api/protocolos.py`,
  `app/rules_engine/engine.py`, `app/services/pdf.py`, `app/api/reports.py`,
  `app/models/report_template.py`, migration `c4e8a2d6f1b3`,
  `tests/test_protocolos.py`; frontend — `src/laudo/` (gerador do relatório:
  `texto.ts`, `documento.ts`, `imagens.ts`, `grafico.ts`, `css.ts`,
  `modelo.ts`, `tipos.ts`), `src/pages/EditorProtocolo.tsx`,
  `src/pages/AtendimentoProtocolo.tsx`, `src/pages/NovoAtendimento.tsx`,
  `src/components/ModelosDeProtocolo.tsx`, `src/pages/HistoricoPaciente.tsx`,
  `public/laudo/{cabecalho,rodape}.jpg` + testes.
- **Como testar:** Configurações → Modelos De Protocolo → abrir "Exemplo —
  Anamnese E Atenção" (deixado no banco de dev) ou criar um novo → Novo
  Atendimento → escolher o modelo → preencher → Salvar No Sistema →
  Pré-Visualizar / Gerar PDF / Gerar Word → Concluir E Ver Histórico.
- **Pendências/observações:**
  - Fora desta entrega (dá para fazer depois): "Gerar com IA" por seção,
    perguntas condicionais (mostrar B só se A = Sim) e importar modelo a
    partir de um documento.
  - O visual do relatório existe em duas cópias (protocolo padrão e
    `src/laudo/`): mudou um, replicar no outro.
  - Ficou no banco de dev um paciente "Paciente Teste E2E" com um
    atendimento de exemplo (o sistema não deixa excluir paciente com laudo).

## Configurações com submenu e páginas próprias

**Status:** ✅ Pronto (2026-10-05)

- Configurações no menu lateral agora expande/recolhe quatro subopções:
  Registro Profissional, Capa Dos Relatórios, Modelos De Protocolo e
  Inteligência Artificial. Cada opção abre uma página própria, carregando
  apenas a configuração correspondente.
- A opção atual fica destacada; abrir uma página de configuração diretamente
  também abre o submenu. No celular, expandir Configurações mantém o menu
  aberto, e selecionar uma opção fecha o menu lateral.
- O endereço anterior `/configuracoes` redireciona para Registro Profissional.
  O botão de voltar do editor de protocolos retorna à lista de modelos.
- Arquivos: `frontend/src/App.tsx`, `components/Layout.tsx`,
  `components/ds/SidebarNav.tsx`, `components/ds/SidebarNav.module.css`,
  `pages/Configuracoes{Registro,Capa,Protocolos,IA}.tsx` e
  `pages/EditorProtocolo.tsx`. A antiga página única foi substituída.
- Validação: build de produção e 28 testes existentes do frontend aprovados.
- Como conferir: clicar em Configurações, navegar pelas quatro opções e abrir
  um modelo de protocolo; usar Voltar para retornar à lista. Repetir com o
  menu móvel, verificando que expandir o grupo não fecha a navegação.

## Relatório por IA a partir de PDFs dos formulários (substitui o PDF consolidado)

**Status:** ✅ Pronto (2026-10-05)

- **O que mudou para a psicóloga:**
  - No **Histórico do paciente**, o antigo "PDF consolidado" (marcar
    protocolos e a IA juntar) saiu. No lugar, o botão **"Relatório Por IA
    (PDFs)"**: anexar (ou arrastar) de **1 a 6 PDFs** com as respostas dos
    formulários — no Google Forms: aba Respostas → Individual → impressora →
    Salvar como PDF — e, se quiser, escrever observações para a IA.
  - A IA lê cada pergunta e a **opção marcada** (inclusive quando a marcação
    é só um círculo preenchido no PDF) e monta o relatório **por área/tema**,
    cruzando os formulários (ex.: o que a mãe e a professora dizem sobre
    atenção), com **gráficos** quando há respostas em escala — sempre
    dizendo como os valores foram contados — e as fontes de cada área.
  - Abre uma **tela de revisão** onde tudo é editável: metodologia, cada área
    (título, texto, gráfico com os valores), considerações finais, sugestões
    de intervenção, cidade/data, capa. Salva sozinho. Dá para
    Pré-Visualizar, **Gerar PDF**, **Gerar Word** e "Salvar E Voltar Ao
    Histórico". O relatório fica no histórico ("Abrir Relatório"), com PDF e
    Word, e os PDFs originais continuam disponíveis para baixar.
  - Mesmo visual dos demais relatórios (capa, cabeçalho, moldura, rodapé,
    faixas, "Sobre a profissional", assinatura).
- **Testado com IA de verdade** (Gemini configurado na conta de
  demonstração), com dois PDFs fictícios no estilo do Google Forms: leu as
  opções marcadas corretamente (somas 9 e 8 conferidas à mão) e levou cerca
  de 1 minuto e meio.
- **Arquivos:** backend — `app/api/relatorios_pdf.py`,
  `app/services/ai/{chains,schemas,__init__}.py`, `app/services/storage.py`
  (`form_pdfs`), `app/services/document_text.py`, `app/services/pdf.py`,
  `app/api/reports.py` (consolidado removido), `tests/test_relatorios_pdf.py`
  (e `tests/test_consolidated_pdf.py` removido); frontend —
  `src/components/EnvioDePdfsParaIA.tsx`, `src/pages/RelatorioPorPdfs.tsx`,
  `src/laudo/relatorioIA.ts`, `src/laudo/documento.ts` (partes comuns),
  `src/laudo/grafico.ts` (gráfico genérico), `src/api/relatoriosPdf.ts`,
  `src/pages/HistoricoPaciente.tsx` + testes.
- **Como testar:** Pacientes → Histórico → "Relatório Por IA (PDFs)" →
  anexar PDFs → Gerar Relatório → revisar → Gerar PDF/Word → Salvar E
  Voltar Ao Histórico.
- **Pendências/observações:**
  - O modelo de IA configurado em Configurações → Inteligência Artificial
    precisa aceitar PDF (Claude, GPT-5 e Gemini aceitam).
  - Os PDFs vão ao provedor de IA (dados sensíveis — LGPD), como já
    acontecia com o consolidado.
  - Os pareceres consolidados antigos não aparecem mais na tela; os dados
    continuam no banco (tabela `consolidated_reports`).
  - No banco de dev ficou um relatório de teste no "Paciente Teste E2E".

## Menu Pacientes, página Todos Os Pacientes e Ver Logs

**Status:** ✅ Pronto (2026-10-05)

- **Menu lateral:** "Pacientes" agora mostra sempre as subopções **Todos Os
  Pacientes**, **Novo Atendimento** e **Relatório Por IA A Partir De
  Formulários Google**. Abaixo de Configurações entrou **Ver Logs**.
- **Todos Os Pacientes:** cada paciente tem **Histórico**, **Novo
  Atendimento**, **Formulário Dos Responsáveis**, **Seções Clínicas** e
  **PDF / Word** — que abre a lista de relatórios do paciente (o mais recente
  destacado) para escolher qual baixar e em qual formato.
- **Formulário Dos Responsáveis** e **Seções Clínicas** ganharam página
  própria por paciente. As seções clínicas continuam sendo de cada relatório:
  a página mostra um seletor de relatório (começa no mais recente).
- **Relatório Por IA** pelo menu: escolher o paciente e anexar os PDFs (o
  mesmo envio do Histórico).
- **Ver Logs:** todas as edições feitas nos relatórios (data, paciente,
  relatório, o que mudou e quem alterou), com filtro por paciente. O botão
  "Ver Logs" de dentro do Histórico saiu.
- O endereço antigo `/dashboard` redireciona para Todos Os Pacientes.
- **Arquivos:** `components/Layout.tsx`, `components/ds/SidebarNav.tsx` (+css,
  teste), `pages/Dashboard.tsx` (+teste), `pages/{FormulariosResponsaveisPaciente,
  SecoesClinicasPaciente,RelatorioIA,Logs}.tsx`,
  `components/pacientes/{BaixarRelatorioDialog,CabecalhoDoPaciente,
  FormulariosDeResponsaveis,SecoesClinicasForm}.tsx` (os dois últimos saíram de
  dentro do Histórico, sem mudança de comportamento), `pages/HistoricoPaciente.tsx`,
  `App.tsx`, `pages/Login.tsx`, `api/reports.ts`; backend `GET /api/logs` em
  `app/api/reports.py` (+ testes em `tests/test_reports_edit_log.py`).

## Pesquisa de pacientes, opções em botões e cadastro no Relatório Por IA

**Status:** ✅ Pronto (2026-10-05)

- **Todos Os Pacientes:** campo de **pesquisa** (por nome — sem diferenciar
  acentos e maiúsculas — ou data de nascimento, ex.: "15/03"), com contador
  "X de Y pacientes". As opções de cada paciente viraram **botões** com ícone
  (Novo Atendimento em destaque; Histórico, Formulário Dos Responsáveis,
  Seções Clínicas e PDF / Word). O quadro "Protocolos Por Modelo" foi
  removido.
- **Relatório Por IA:** botão **Novo Paciente** ao lado da escolha do
  paciente; sem nenhum paciente cadastrado, o cadastro (nome, nascimento,
  sexo) já aparece direto. Ao cadastrar, o paciente fica selecionado e o
  envio dos PDFs abre em seguida.
- **Correção no celular:** a barra superior (logo e botão do menu) aparecia
  como uma faixa branca ao lado do conteúdo, em vez de em cima. Corrigido
  (`components/Layout.module.css`).
- **Arquivos:** `pages/Dashboard.tsx` (+teste), `pages/RelatorioIA.tsx`
  (+teste), `components/pacientes/NovoPacienteForm.tsx`,
  `components/Layout.module.css`.

## IA: todos os principais provedores do mercado

**Status:** ✅ Pronto (2026-10-05)

- **Configurações → Inteligência Artificial** agora aceita: **Anthropic
  (Claude)**, **OpenAI (ChatGPT/GPT)**, **Google (Gemini)**, **OpenRouter**
  (uma chave só para modelos de quase todas as empresas), **xAI (Grok)**,
  **Mistral AI**, **Meta Llama (via Groq)**, **Alibaba (Qwen)**, **DeepSeek**
  e **Cohere**. Cada um traz modelos sugeridos (pode digitar outro) e o link
  de onde gerar a chave.
- A tela mostra **como cada IA lê os PDFs** do Relatório Por IA:
  - por inteiro (Claude, GPT, Gemini, OpenRouter) — o ideal;
  - como imagens das páginas (Grok, Mistral, Llama, Qwen) — ainda enxerga a
    opção marcada; se o modelo escolhido não aceitar imagens, o sistema tenta
    de novo só com o texto;
  - só o texto (DeepSeek, Cohere) — aviso em destaque: pode não identificar a
    opção marcada no Google Forms; a IA é instruída a dizer isso em vez de
    supor.
- **O relatório continua saindo no padrão do sistema com qualquer IA:** a IA
  só devolve o conteúdo (textos, valores dos gráficos, etc.) em campos fixos;
  capa, cabeçalho, layout, gráficos, PDF e Word são sempre montados pelo
  próprio sistema.
- **Implantação:** dependência nova `pypdfium2` (em `requirements.txt`) —
  precisa reconstruir a imagem Docker.
- **Testado** com a IA real só no Gemini (a única chave disponível aqui); os
  demais provedores foram testados com a IA simulada (endereço, formato de
  envio dos PDFs, volta para só texto).
- **Arquivos:** `backend/app/services/ai/{provedores,provider,chains}.py`,
  `app/services/document_text.py` (`paginas_em_png`),
  `app/schemas/ai_settings.py`, `app/api/ai_settings.py`
  (`GET /api/settings/ai/provedores`), `requirements.txt`, testes;
  frontend `pages/ConfiguracoesIA.tsx` (+teste), `api/aiSettings.ts`.

## Auditoria de segurança e preparação para o deploy na VPS

**Status:** ✅ Pronto (2026-10-05)

- **Falha crítica corrigida — leitura de arquivos do servidor sem login:**
  um endereço como `/..%2f..%2fbackend%2f.env` devolvia o `.env` (com o
  segredo dos logins) e até o banco de desenvolvimento inteiro. Agora a rota
  só entrega arquivos do próprio site. Testado contra o servidor real e com
  testes automáticos.
- **Imagem Docker sem segredos nem dados:** o `.dockerignore` deixava entrar
  o `backend/.env` e um backup do banco com dados de pacientes na imagem
  publicada no GitHub. Corrigido e conferido dentro da imagem.
- **Produção mais fechada:** o sistema se recusa a subir com `JWT_SECRET`
  fraco/de exemplo; cadastro público desligado (a conta vem do ADMIN_*);
  documentação da API escondida.
- **Login:** bloqueio também por IP (20 erros em 15 min, além dos 5 por
  e-mail) e tempo de resposta igual para e-mail existente ou não.
- **PDF:** nenhum PDF busca arquivos do servidor ou da internet (havia um
  caminho antigo que permitia).
- **Uploads limitados** (fotos, formulários dos responsáveis, importação de
  modelos: 15 MB; 100 MB por envio no Caddy).
- **Cabeçalhos de segurança** em todas as respostas (CSP, nosniff,
  SAMEORIGIN, Referrer/Permissions-Policy, sem cache na API). Corrigido
  também o `X-Frame-Options: DENY` do Caddy, que **quebraria o Novo
  Atendimento em produção** (o protocolo abre num iframe).
- **Sem recursos de terceiros:** Chart.js (antes vinha de um CDN sem versão
  fixa — 1 linha alterada no protocolo padrão) e as fontes da marca (antes
  Google Fonts) agora são servidos pelo próprio sistema.
- **Dependências:** FastAPI/Starlette, python-multipart, cryptography,
  uvicorn, pypdf e python-dotenv atualizados; `python-jose` (sem manutenção)
  trocado por `PyJWT`. `pip-audit` e `npm audit`: 0 vulnerabilidades.
- **Container sem root**; pré-visualizações em iframe com `sandbox`.
- **Deploy:** `DEPLOY.md` reescrito como passo a passo para a VPS;
  scripts `scripts/gerar-env.sh` (gera o `.env` com segredos fortes),
  `scripts/backup.sh` (banco + arquivos, com rotação) e
  `scripts/atualizar.sh` (backup → atualização → conferência).
- **Testado:** imagem de produção construída e executada com Postgres em
  modo produção — migrations, conta admin, login pela tela, protocolo padrão
  no iframe, Chart.js, fontes, PDF, cadastro bloqueado, ataques de leitura
  de arquivo bloqueados, nenhum erro de política de segurança no navegador.
- **Pendências/observações:** se já havia versão no ar, seguir a seção 7 do
  `DEPLOY.md` (trocar `JWT_SECRET`, senhas e chaves; revisar a imagem no
  GHCR). O token de login continua no `localStorage` do navegador (risco
  residual baixo com a CSP atual).

## Correções da daily com a cliente e Laudo Por IA (protocolo padrão)

**Status:** 🟡 Parcial (2026-10-13) — itens a confirmar com a cliente no fim.

- **Formulário (protocolo padrão):**
  - Nova pergunta "Houve Complicação No Parto?" (Sim/Não + descrição), que sai na Anamnese do relatório.
  - Idade da mãe e idade gestacional viraram listas: é só clicar no número.
  - "Metodologia" virou "Protocolo Utilizado"; o botão "Salvar Protocolo" virou "Salvar Laudo".
  - Saíram as seções 17 (habilidades cognitivas, já cobertas pela 8), 20 (Sugestões de Intervenção) e 22 (Considerações Finais, agora com texto-padrão fixo no relatório). A seção 8 (habilidades acadêmicas) passou a sair no relatório com tabela e gráfico.
  - A Análise por Área (faixas cinza) só aparece quando o TDAH está entre as hipóteses.
  - Encaminhamentos ganhou "Acompanhamento Multidisciplinar" (Terapia, Fisioterapia, Nutrição, Psicologia Infantil).
  - Hipóteses viraram a seção 9 e os Quadros a 10: cada hipótese marcada gera o seu quadro, todos no mesmo padrão, numa seção própria do relatório.
  - As seções foram renumeradas (agora vão de 1 a 20).
  - Seção 11: botão "Importar Escalas Com IA" — anexar os PDFs das escalas pontuadas preenche CARS, ATA, SNAP-IV, TOD e Portage, e os gráficos saem sozinhos.
- **Correção de falha antiga:** as hipóteses e os encaminhamentos marcados não eram salvos (sumiam ao reabrir o laudo).
- **Cores:** formulário, gráficos, PDF e Word seguem a paleta da marca. No gráfico do Portage, Socialização e Cognição tinham a mesma cor; agora são diferentes.
- **Laudo Por IA (menu Pacientes):** envia de 1 a 10 PDFs (Google Forms e escalas). A IA faz o estudo de caso e preenche o protocolo padrão, o sistema gera o laudo oficial com os gráficos, e a psicóloga baixa o Word para editar ou abre "Ajustar No Formulário". O que os PDFs não trouxeram aparece numa lista. No Histórico, "Abrir Protocolo" reabre qualquer laudo do protocolo padrão.
- **Arquivos principais:** `frontend/public/formulario-novo-paciente.html`, `frontend/src/pages/LaudoPorIA.tsx`, `frontend/src/components/SeletorDePdfs.tsx`, `frontend/src/components/pacientes/EscolhaDePaciente.tsx`, `backend/app/api/laudo_ia.py`, `backend/app/services/laudo_ia.py`.
- **Como testar:** Pacientes → Novo Atendimento (correções) e Pacientes → Laudo Por IA (PDFs de teste).
- **Considerações finais — TEA em meninas:** incluído o texto fornecido pela cliente em 13/10 sobre diagnóstico e mascaramento autista, preservando a redação. Aparece para sexo Feminino e hipótese diagnóstica selecionada de TEA, antes do aviso de fechamento, no HTML compartilhado pela prévia, PDF e Word (também no Laudo Por IA). Laudos já gerados precisam ser regenerados pelo formulário para incorporar o texto.
- **Pendências — confirmar com a cliente:** o que é "colocar entendas"; quais campos são "observações gerais 4 e 5" (copiar/colar/anexar); o que é a "ficha do grupo" (10 anos ou mais); se o "problema na página 8" era a cor do Portage; o texto geral das Considerações Finais; se o acompanhamento multidisciplinar sai no relatório; se as faixas cinza continuam cinza.

## Sistema mais rápido e IA dividida em agentes

**Status:** ✅ Pronto (2026-10-13)

- **Navegação mais leve:**
  - A lista de laudos do Histórico trazia o relatório inteiro de cada laudo (fotos, capa e gráficos — cerca de 2 MB por laudo). Agora traz só o resumo: **de 2,1 MB para 651 bytes**. O laudo completo só é baixado quando é aberto.
  - O salvamento automático do formulário reenviava todas as fotos a cada alteração e recebia de volta o relatório inteiro. Agora as fotos só sobem quando mudam (uma edição de texto: ~35 KB em vez de centenas de KB ou mais) e a resposta é mínima.
  - As telas do sistema carregam sob demanda: o primeiro acesso baixa 303 KB em vez de 556 KB.
  - O navegador guarda os arquivos do sistema: os que têm versão no nome ficam guardados por 1 ano; o formulário (540 KB) só é baixado de novo quando muda (senão, resposta vazia).
- **IA mais rápida, em agentes:**
  1. Cada PDF é transcrito para JSON (perguntas e respostas marcadas) por um agente próprio, todos ao mesmo tempo. O resultado fica guardado: enviar o mesmo PDF de novo não chama a IA.
  2. Sobre esse JSON, sem reler os PDFs, trabalham ao mesmo tempo quatro agentes: anamnese/histórico, escalas, desenvolvimento (Portage, habilidades, funções executivas, domínios) e o redator do estudo de caso.
  - O tempo total passa a ser o da chamada mais lenta de cada etapa, não a soma de todas. No teste com tempo de IA simulado (1,5 s por chamada): 2 PDFs transcritos em 1,5 s e os 4 agentes em 1,5 s.
  - O Relatório Por IA antigo também usa a transcrição em JSON. Cada Laudo Por IA guarda o JSON lido e o tempo de cada etapa.
- **Arquivos principais:** `backend/app/services/ai/agentes/` (extração, especialistas, execução em paralelo), `backend/app/services/laudo_ia.py`, `backend/app/api/reports.py` (resumo leve), `backend/app/main.py` (cache), `frontend/src/App.tsx` (carregamento sob demanda), `frontend/public/formulario-novo-paciente.html` (salvamento automático).
- **Como testar:** abrir o Histórico de um paciente com vários laudos; preencher o formulário com fotos e conferir que continua fluido; gerar um Laudo Por IA com mais de um PDF.
- **Pendências/observações:** a velocidade real da IA depende do provedor e do modelo configurados. O ganho vem de dividir e paralelizar; ainda não foi medido com o provedor real. Enquanto um PDF é gerado no servidor, as outras requisições ficam mais lentas (há um único processo, porque o limite de tentativas de login vive na memória dele); se isso pesar, o próximo passo é gerar os PDFs num processo separado.

## Laudo Por IA como único fluxo de criação por PDFs

**Status:** ✅ Pronto (2026-10-14)

- Menu Pacientes mantém apenas **Laudo Por IA**; removida a opção antiga de Relatório Por IA.
- O Histórico oferece o novo Laudo Por IA com o paciente já selecionado.
- Links antigos para `/relatorio-ia` redirecionam para `/laudo-ia`, preservando os parâmetros. Relatórios antigos continuam acessíveis para revisão e exportação pelo Histórico.
- Cota diária da IA esgotada agora tem mensagem específica; o sistema não repete a chamada automaticamente nesse caso.

## Nova identidade visual "Caderno Lilás" em todo o sistema

**Status:** ✅ Pronto (2026-10-14)

- **O que mudou na aparência (sem mudar dados, rotas nem regras):**
  - Novas cores (violeta principal, céu secundária, amarelo só para pendências e avisos), fundo lilás-claro com o conteúdo em cartões brancos, e novas fontes: Bricolage Grotesque nos títulos e números, Figtree no resto, JetBrains Mono nos atalhos de teclado.
  - Botões com um só tipo de destaque por tela (primário violeta), secundário branco com borda, tonal lilás para PDF/Word e fantasma para Voltar/Cancelar. Todos têm estado de foco visível, desabilitado e carregando (com spinner).
  - Campos com rótulo acima, asterisco nos obrigatórios, halo violeta no foco, erro em vermelho com ícone, e calculados com borda tracejada.
  - Menu lateral com grupos "Clínica" e "Sistema", sua foto/iniciais no rodapé e botão de sair. "Ver Logs" passou a se chamar **Registro de atividades**. No celular o menu abre empilhado acima da tela.
  - **Todos os pacientes:** cartões de números, tabela com iniciais coloridas e idade, e ações "Atendimento", "Histórico" e "Responsáveis". "Seções clínicas" e "PDF / Word" ficam no botão ⋯.
  - **Novo atendimento:** etiqueta "Ainda não salvo" / "Salvo às HH:MM" no topo, fases com círculos (atual violeta, concluída verde ✓, pendente amarela com !), faixa de título da fase sem degradê, ajuda em aviso azul e barra de ações embaixo ("← Fase anterior", "Mais opções", "Pré-visualizar", "PDF", "Word" e **"Salvar laudo" em violeta, não mais amarelo**).
  - Títulos, menus e botões só com a primeira letra maiúscula. Nomes de pacientes salvos em CAIXA ALTA aparecem como nome (o dado salvo não muda).
- **Não mudou:** o PDF e o Word dos relatórios, os textos e as regras do protocolo, nem os nomes dos campos do formulário.
- **Arquivos principais:** `frontend/public/identidade/tokens.css` (cores e fontes), `frontend/src/styles/base.css`, `frontend/src/components/ds/`, `frontend/src/components/Layout.tsx`, todas as páginas em `frontend/src/pages/`, `frontend/public/formulario-novo-paciente.html` (só aparência e textos de botões). Referência de design: `docs/identidade/`.
- **Como testar:** entrar no sistema e percorrer Todos os pacientes, Novo atendimento, Histórico, Laudo por IA, Configurações e Registro de atividades, no computador e no celular.
- **Pendências/observações:**
  - A etiqueta de status do último laudo na tabela de pacientes não foi incluída: a lista de pacientes não traz essa informação, e incluí-la exigiria mudar a API (fora do escopo de "só aparência").
  - No formulário do protocolo padrão, os rótulos dos campos e os títulos das seções continuam com Iniciais Maiúsculas no código, porque as regras das fases e a IA leem esses textos. Os nomes das fases e os títulos mostrados na tela já aparecem só com a primeira letra maiúscula.

## Varredura de desempenho (banco, servidor, capa e processos)

**Status:** ✅ Pronto (2026-10-14) — branch `otimizacao-desempenho`

- **Sem mudança de comportamento:** pontuação, classificação, textos do laudo e layout do PDF/Word continuam iguais; isolamento entre psicólogas inalterado.
- **Registro de atividades** (`/api/logs`): 243 consultas ao banco viraram 2 (349 ms → ~50 ms no teste com 200 registros). Antes, cada linha carregava o laudo inteiro (fotos e HTML).
- **Salvamento automático e "Salvar laudo":** cada salvamento lia o laudo inteiro do banco duas vezes (~3,5 MB); agora lê só o necessário (~0,8 MB no autosave, quase nada ao salvar o texto).
- **Painel de números** (`/api/stats/summary`): 5 consultas → 3, sem ler as colunas pesadas (100 ms → ~45 ms).
- **Compressão gzip no próprio servidor:** a stack do Portainer não comprimia nada; o formulário padrão cai de 570 KB para 267 KB na rede, o registro de atividades de 79 KB para 14 KB.
- **S3:** a conexão com o bucket é reaproveitada (antes era criada a cada foto/arquivo). O PDF baixado do Histórico não é mais relido do storage logo depois de gerado.
- **Índices novos no banco** (migração `e5f1a7c3b9d2`, aplicada sozinha ao subir o container): laudos por paciente e data; registro de atividades por data.
- **Capa padrão** `capa-relatorio.png` (3,4 MB) → `capa-relatorio.jpg` (829 KB), diferença imperceptível (a capa final já era gravada em JPEG).
- **2 processos do servidor** (`WEB_CONCURRENCY=2`): gerar um PDF pesado não trava as outras telas. RAM em repouso 142 → 300 MB. O limite de tentativas de login passa a contar por processo (até 10 em vez de 5 no pior caso).
- **Como testar:** abrir Registro de atividades, Todos os pacientes e o Histórico; preencher um atendimento (autosave) e baixar PDF/Word; conferir a capa padrão no PDF.
- **Ficou de fora (baixo impacto):** remover o pacote `langchain` não usado e o pytest da imagem, `.dockerignore` mais completo, apagar `ScoreChart.tsx`/`react-chartjs-2` órfãos.

## Laudo por IA: não trava mais com 3 ou mais PDFs

**Status:** ✅ Pronto (2026-10-14) — branch `laudo-ia-estavel`

- **Causa:** todos os PDFs eram lidos pela IA ao mesmo tempo. Com 3 ou mais, a conta do provedor batia no limite de uso por minuto, e o sistema tentava de novo cedo demais. Além disso, as chamadas não tinham tempo-limite (podiam esperar até ~90 min) e tudo acontecia numa única conexão aberta por 4 a 7 minutos, que a rede ou o proxy podiam cortar, deixando a tela sem resposta.
- **O que mudou:**
  - A geração agora roda em segundo plano. A tela mostra o andamento ("Lendo documento 2 de 4…", "Preenchendo o protocolo…", "Redigindo o estudo de caso…") e a situação de cada PDF.
  - No máximo 3 PDFs lidos ao mesmo tempo. Quando o provedor pede para esperar, o sistema espera o tempo pedido.
  - Toda chamada à IA tem tempo-limite e tamanho máximo de resposta. Erro de chave ou de modelo aparece na hora, sem novas tentativas.
  - Se um PDF falhar, a mensagem diz qual foi e por quê. Os PDFs já lidos ficam guardados: tentar de novo só relê o que falhou.
  - Com GPT-5, a leitura dos PDFs usa raciocínio curto (é só transcrição), o que deixa essa etapa mais rápida.
- **Não mudou:** regras de pontuação, o laudo gerado e o Word/PDF.
- **Como testar:** Laudo por IA com 4 ou 5 PDFs; acompanhar as mensagens de andamento; gerar de novo com os mesmos PDFs (fica mais rápido).
- **Arquivos principais:** `backend/app/services/laudo_ia_jobs.py`, `backend/app/api/laudo_ia.py`, `backend/app/services/ai/provider.py`, `backend/app/services/ai/chains.py`, `backend/app/services/ai/agentes/`, `frontend/src/pages/LaudoPorIA.tsx`, `frontend/src/api/laudoIA.ts`.

## Laudo por IA: completar os dados que faltaram (digitando ou por foto)

**Status:** ✅ Pronto (2026-10-15)

- **Antes:** depois do Laudo por IA aparecia "Os PDFs não trouxeram:", uma lista em texto com nomes internos (ata_item_0…), itens fora do caso e sem como resolver ali.
- **Agora, no cartão "Laudo gerado" (e pelo Histórico, ⋯ → "Completar dados"):**
  - "Dados que faltaram", por seção com nome amigável (Identificação e escola, Gestação e parto, Desenvolvimento, Histórico clínico e queixas, Habilidades do ano escolar, cada escala). O essencial vem primeiro; o opcional fica recolhido.
  - Os essenciais são os mesmos marcados como obrigatórios no formulário. As escalas só aparecem se foram aplicadas, ou em "Também apliquei: TOD…". Os itens de cada escala viram uma pendência só ("Pontuações da ATA — 22 itens"), com o botão "Preencher".
  - Cada pendência tem o campo do tipo certo (lista, Sim/Não, número, data, texto). No menu ⋯ há "Não se aplica" e "Não informado pela família", que não aparecem no laudo.
  - Barra "8 de 12 essenciais preenchidos" e salvamento automático ("Salvo às…"). Fechar a página não perde nada.
  - "Anexar foto ou documento", geral e em cada seção. No celular, "Tirar foto" abre a câmera; também aceita PDF. A IA lê a foto (reduzida e sem localização/metadados) e sugere valores só para o que falta. A sugestão aparece destacada com o nome da foto e só entra no laudo depois de "Confirmar" ou "Corrigir".
  - "Atualizar laudo": aplica os dados confirmados. Se mudaram identificação, gestação, desenvolvimento ou queixas, a IA reescreve só o estudo de caso, sem reler os PDFs (se você já tinha editado o estudo, ele é mantido, salvo se marcar "Reescrever"). Depois gera o documento de novo, com gráficos e pontuações recalculados.
  - Os dados confirmados ficam no cadastro do paciente e preenchem o que a IA deixar vazio nos próximos laudos, sem sobrescrever o que vier dos PDFs.
- **Banco:** migração `f2b8d4e6a1c7` (aplicada sozinha ao subir o container): coluna `patients.dados_complementares` e tabela `patient_attachments`. As fotos ficam no storage existente (pasta `anexos`), e cada psicóloga só vê as dos seus pacientes.
- **Não mudou:** regras de pontuação, textos do laudo e o modelo do Word/PDF.
- **Como testar:** gerar um Laudo por IA; preencher 2 ou 3 pendências; dispensar uma; anexar a foto de uma ficha; confirmar a sugestão; "Atualizar laudo" e conferir o documento.

### Ajuste (2026-10-15): resumo com modal

- No lugar da lista de campos aberta na página, o laudo mostra um quadro nas cores do sistema: **"Há alguns campos que podem ser preenchidos:"**, com **tudo** o que falta, por seção (essenciais e opcionais, sem nomes internos) e a contagem dos essenciais.
- Clicar numa seção (ou em "Preencher campos") abre um **modal** com os campos, o anexar foto e as sugestões. Embaixo ficam **"Salvar"** (salva e fecha) e **"Salvar e gerar o protocolo"** (salva, aplica no laudo e gera o documento de novo).
- **Para voltar a essa tela:** o quadro continua no laudo depois de fechar o modal, e no Histórico do paciente cada laudo por IA tem o botão **"Campos que faltam"**.
