# Escopo do projeto: o que foi combinado, o que foi entregue e o que falta

Este documento conta a história do sistema em quatro partes: o que foi combinado no início, o que foi
entregue dentro disso, o que foi entregue além, e o que ainda está pendente. Tudo foi conferido no código e
no histórico do git. Datas são aproximadas (a data do commit).

> **Sobre a fonte do escopo original.** Não foi encontrado nenhum contrato ou proposta assinada no
> repositório nem nas pastas de apoio. O escopo original abaixo foi **deduzido** do roteiro de 4 semanas
> (`PROMPTS.md`, que se descreve como "o mesmo cronograma de 4 semanas da proposta"), do `CLAUDE.md`, do
> `SPEC.md` e do `APRESENTACAO.md`. Por isso toda a Parte 1 está marcada como **a confirmar** com quem
> fechou a proposta.

## Sumário

* [Parte 1. Escopo original (a confirmar)](#parte-1-escopo-original-a-confirmar)
* [Parte 2. Entregue dentro do escopo](#parte-2-entregue-dentro-do-escopo)
* [Parte 3. Entregue além do escopo](#parte-3-entregue-além-do-escopo)
* [Parte 4. Pendências](#parte-4-pendências)
* [Resumo em números](#resumo-em-números)

## Parte 1. Escopo original (a confirmar)

**Ideia central:** transformar o formulário HTML de avaliação da Mayra (neuropsicopedagoga) em um sistema
web com login, banco de dados e geração automática do relatório no padrão dela, em PDF, em 4 semanas.

| Semana | O que o roteiro previa |
|---|---|
| 1. Levantamento e design | Estrutura do projeto, modelagem do banco, protótipo de telas |
| 2. Backend | Login, cadastro de pacientes e modelos, motor de pontuação das escalas, endpoint do laudo |
| 3. Frontend | Formulário integrado à API, histórico e painel, gráficos, build único servido pelo backend |
| 4. Entrega | Texto do parecer com IA, exportação em PDF, testes e revisão de segurança, preparação para implantação |

Em 20/09/2026 houve uma **mudança de rumo decidida pelo usuário**: em vez de modelos de laudo configuráveis,
o sistema passou a girar em torno de um **protocolo fixo** (o formulário original da Mayra, embutido). Isso
está registrado em `ENTREGAS.md` (entrada "Mudança de arquitetura") e no `CLAUDE.md`. O escopo abaixo já
considera essa mudança.

## Parte 2. Entregue dentro do escopo

| # | Funcionalidade (em linguagem simples) | Quando | Onde está no código | Commits principais |
|---|---|---|---|---|
| 1 | A psicóloga entra com e-mail e senha; cada uma só vê os próprios pacientes | 14/09 | `backend/app/api/auth.py`, `api/deps.py`, `core/security.py` | `7196da1` |
| 2 | Cadastro e edição de pacientes | 14/09 | `backend/app/api/patients.py`, `frontend/src/pages/Dashboard.tsx` | `7196da1` |
| 3 | O protocolo completo da Mayra funciona dentro do sistema (identificação, gestação, escola, escalas) | 14/09 a 21/09 | `frontend/public/formulario-novo-paciente.html`, `frontend/src/pages/NovoAtendimento.tsx` | `7196da1`, `3b51266` |
| 4 | O sistema calcula a pontuação das escalas CARS, ATA, SNAP-IV, TOD, M-CHAT e Portage | 14/09 a 21/09 | HTML do protocolo (`calcularCARS`, `calcularATA`, `analisarSNAP`…) | `7196da1`, `3b51266` |
| 5 | Cada campo é salvo sozinho no banco (autosave) | 20/09 | Segundo `<script>` do HTML; `PUT /api/reports/{id}/answers` em `backend/app/api/reports.py` | `3b51266`, `0e105f6` |
| 6 | Interpretação por palavras-chave e probabilidade por hipótese diagnóstica | 14/09 a 21/09 | HTML do protocolo (`probabilidades()`) | `7196da1` |
| 7 | Relatório final no padrão da Mayra (capa, textos, tabelas, assinatura) | 23/09 | `gerarDocumentoLaudoHTML()` no HTML | `0e105f6` |
| 8 | Gráficos automáticos dentro do relatório | 14/09 a 23/09 | HTML do protocolo (`graficoCARS`, `graficoATA`, `graficosSNAP`…) | `7196da1`, `0e105f6` |
| 9 | Relatório em PDF | 14/09 a 23/09 | `backend/app/services/laudo_documento.py`, `services/pdf_do_laudo.py` | `7196da1`, `0e105f6` |
| 10 | Relatório em Word editável | 23/09 | `backend/app/services/laudo_documento.py` (`html_para_docx`) | `0e105f6` |
| 11 | Histórico do paciente com os relatórios já feitos | 14/09 | `frontend/src/pages/HistoricoPaciente.tsx`, `GET /api/patients/{id}/reports` | `7196da1` |
| 12 | Texto de fechamento (considerações finais e sugestões) escrito com apoio de IA | 28/09 | `backend/app/services/ai/chains.py` (`generate_conclusion_and_interventions`) | `2fc7edc` |
| 13 | Segurança básica e preparação para implantação (variáveis de ambiente, Docker, documento de deploy) | 14/09 a 05/10 | `Dockerfile`, `DEPLOY.md`, `backend/app/core/` | `7196da1`, `8931dc3` |

## Parte 3. Entregue além do escopo

Itens que não estavam no roteiro de 4 semanas e foram feitos por pedido da cliente, por necessidade técnica
ou por decisão do projeto. Todos foram confirmados no código e no git.

### Inteligência artificial

| # | Funcionalidade | Quando | Onde no código | Commits |
|---|---|---|---|---|
| 14 | **Laudo por IA** (antes "Relatório por IA"): a psicóloga envia os PDFs dos formulários e das escalas, a IA lê, preenche o protocolo e o sistema monta o relatório oficial | 05/10 a 14/10 | `backend/app/api/laudo_ia.py`, `services/laudo_ia.py`, `services/ai/`, `frontend/src/pages/LaudoPorIA.tsx` | `6c82a40`, `66f407c` |
| 15 | Geração em segundo plano com barra de progresso | 14/10 e 18/10 | `services/laudo_ia_jobs.py`, `frontend/src/components/ProgressoDaGeracao.tsx` | `5b024c5`, `f9fc638` |
| 16 | IA dividida em agentes que trabalham ao mesmo tempo, com cache da leitura dos PDFs | 13/10 e 14/10 | `services/ai/agentes/` | `66f407c`, `78d1a49` |
| 17 | Importar escalas pontuadas por PDF para o formulário | 13/10 | `POST /api/patients/{id}/escalas-de-pdf` em `api/laudo_ia.py` | `66f407c` |
| 18 | Pontuação da ATA feita pelo sistema (não pela IA) | 18/10 | `backend/app/services/ata.py` | `351cf9c` |
| 19 | Pendências do relatório: o que faltou preencher, completar digitando ou anexando foto/documento, e "Atualizar relatório" | 14/10 e 15/10 | `services/pendencias.py`, `api/pendencias.py`, `api/anexos.py`, `frontend/src/components/pendencias/` | `ae89469`, `b2414b1`, `dae5de9`, `c531f72`, `4f636de`, `1ee6036`, `a4b187d`, `0449d64` |
| 20 | A psicóloga escolhe hipóteses (CID-11 com subtipos), encaminhamentos, desfralde, ano escolar e habilidades | 18/10 e 19/10 | `frontend/src/laudo/hipotesesCid.ts`, `components/EscolhasDoLaudo.tsx`, `components/DadosDaProfissional.tsx` | `6458a59`, `e046305`, `ffb785e` |
| 21 | Vários provedores de IA (Claude, GPT, Gemini, e outros) e chave de IA guardada criptografada | 13/09 e 05/10 | `backend/app/services/ai/provedores.py`, `core/security.py` | `7196da1`, `6c82a40` |
| 22 | Importar modelos de escala a partir de um documento, com IA (fluxo do motor antigo, hoje sem tela) | 13/09 | `backend/app/api/templates.py` | `7196da1` |

### Produto e telas

| # | Funcionalidade | Quando | Onde no código | Commits |
|---|---|---|---|---|
| 23 | Modelos de protocolo próprios, cadastrados em Configurações, com escolha em Novo Atendimento | 05/10 | `backend/app/api/protocolos.py`, `frontend/src/pages/EditorProtocolo.tsx`, `AtendimentoProtocolo.tsx` | `9f59f5f` |
| 24 | Capa do relatório personalizável | 05/10 | `frontend/src/components/EditorCapa.tsx`, `backend/app/api/auth.py` | `c03abf7` |
| 25 | Formulários preenchidos pelos responsáveis (registro, validação e rejeição) | 28/09 | `backend/app/api/guardian_forms.py`, `frontend/src/components/pacientes/FormulariosDeResponsaveis.tsx` | `01efd8d` |
| 26 | Edição do histórico com registro de atividades (quem mudou o quê) | 13/09 e 05/10 | `backend/app/api/reports.py` (`/api/logs`), `frontend/src/pages/Logs.tsx` | `7196da1` |
| 27 | Menu Pacientes, busca, cadastro rápido e exclusão definitiva com confirmação | 05/10 e 15/10 | `frontend/src/pages/Dashboard.tsx`, `backend/app/api/patients.py` | `c03abf7`…`6c82a40`, `15a88d9` |
| 28 | Revisão de relatórios de 28/09: nota sobre os percentuais, só a hipótese selecionada, ressalva da faixa do Portage, ícones de escala na metodologia | 28/09 | HTML do protocolo | `9b65def`, `e9e213b`, `e26bd68`, `c475fe8`, `9ee8c86`, `40224d4`, `2be81ca` |
| 29 | Formulário em etapas (fases, progresso, campos condicionais) | 20/09 a 30/09 | HTML do protocolo | `3b51266`, `0e105f6`, `0d9d040` |
| 30 | Identidade visual nova ("Caderno Lilás", depois "Lavanda Premium") e ícone do aplicativo | 14/10 e 15/10 | `frontend/src/styles/`, `frontend/src/components/ds/`, `frontend/public/identidade/` | `b855d4b`, `015d256`, `669df2d` |

### Qualidade, desempenho e implantação

| # | Funcionalidade | Quando | Onde no código | Commits |
|---|---|---|---|---|
| 31 | Otimizações de desempenho (listas leves, índices, compressão, cache, arte da capa menor) | 14/10 e 18/10 | `backend/app/main.py`, `api/reports.py`, `alembic/versions/e5f1a7c3b9d2_*` | `a3215ff`, `2ea3246`, `1985c45`, `e09e94b`, `a6581c2` |
| 32 | Deploy: docker-compose com HTTPS automático (Caddy), stack para Portainer e imagem publicada no GHCR por GitHub Actions | 28/09 | `docker-compose.yml`, `docker-compose.portainer.yml`, `Caddyfile`, `.github/workflows/` | `2fe20df`, `f7ec094` |
| 33 | Auditoria de segurança (cabeçalhos, limites de upload, container sem root, imagem sem segredos) | 05/10 | `backend/app/core/cabecalhos.py`, `core/uploads.py`, `Dockerfile` | `8931dc3`, `6c82a40` |
| 34 | Backup do banco e dos arquivos, armazenamento opcional em S3 | 13/09 e 28/09 | `scripts/backup.sh`, `backend/app/services/storage.py` | `7196da1`, `2fe20df` |
| 35 | Testes automatizados (backend e frontend) e testes que conferem gráficos reais no PDF e no Word | 13/09 a 27/10 | `backend/tests/`, `frontend/src/**/*.test.*` | `7196da1`, `060a1ff` |

### Correções pedidas pela cliente

| # | Correção | Quando | Onde no código | Commits |
|---|---|---|---|---|
| 36 | Relatório no modelo de referência da cliente (cores, ordem, quadros por área, rodapé) após a videochamada | 16/10 a 19/10 | HTML do protocolo, `src/laudo/`, `laudo_documento.py` | `96015d1`, `4a23d1a`, `3a00022`, `e9d951e` |
| 37 | Paleta, ordem das seções, aviso legal e assinatura (credencial e caligrafia) | 21/10 | HTML do protocolo, `laudo_documento.py` | `7f6cba7`, `bceb696`, `c9b686f` |
| 38 | Correções de 23/10: texto de Considerações Finais duplicado e texto de TDAH aparecendo com hipótese de TEA | 23/10 | HTML do protocolo | `0fa4868` |
| 39 | Gráficos presentes no relatório, no PDF e no Word (teste com gráficos reais) | 27/10 | `backend/tests/test_graficos_exportacao.py`, `frontend/src/laudo/graficosDoLaudo.test.js` | `060a1ff` |
| 40 | Correções de 30/10 (OBS-01 a OBS-04): texto novo de fechamento, sem caixa azul, sem a "OBSERVAÇÃO", "Desde já…" junto da assinatura | 30/10 | HTML do protocolo, `src/laudo/`, `laudo_documento.py` | `446bc8e`, `878dab0` |

## Parte 4. Pendências

| # | O que falta | Depende de | Observação |
|---|---|---|---|
| P1 | Confirmar com a Mayra o **texto novo de fechamento** ("A análise dos comportamentos…"). Foi transcrito de um print de baixa resolução | Mayra | Está em `analiseDosComportamentosFechamento()` no HTML |
| P2 | O texto novo cita **TEA** e vale para **todas** as hipóteses (decisão registrada em 30/10). Relatórios de TDAH, TOD etc. também dirão TEA | Mayra e usuário | Conflita com a regra de mostrar só a hipótese selecionada |
| P3 | Perguntas da daily de 13/10 sem resposta da cliente: o que é "colocar entendas", quais são as "observações gerais 4 e 5", o que é a "ficha do grupo (10 anos ou mais)", se o "problema na página 8" era a cor do Portage | Mayra | Registrado em `ENTREGAS.md` |
| P4 | Relatórios já salvos antes de 30/10 só mudam ao clicar em **Atualizar Relatório** | Mayra (uso) | Comportamento por desenho |
| P5 | Modelos de protocolo próprios e o relatório por PDFs antigo ainda imprimem "Sobre a profissional" e não têm o texto novo de fechamento | Decisão | Só o protocolo padrão foi atualizado em 30/10 |
| P6 | Medir a velocidade real da IA com o provedor em produção | Equipe | Os ganhos do trabalho em agentes foram medidos só com IA simulada |
| P7 | Recuperação de senha por e-mail | Decisão (precisa de serviço de e-mail) | Adiada de propósito, não esquecida |
| P8 | Confirmar como a VPS está montada (proxy Caddy ou outro) e se existe um script `atualizar-mayra.sh` fora do repositório | Quem mantém a VPS | O repositório só tem `scripts/atualizar.sh` |

Fora de escopo por decisão registrada: assinatura digital de laudos, vários profissionais por conta,
aplicativo nativo para celular.

## Resumo em números

| Parte | Itens |
|---|---|
| 1. Escopo original (a confirmar) | 4 semanas de roteiro |
| 2. Entregue dentro do escopo | 13 |
| 3. Entregue além do escopo | 27 (itens 14 a 40) |
| 4. Pendências | 8 |
| Total de itens entregues | 40 |

Para o histórico por data, veja o [CHANGELOG](../CHANGELOG.md). Para as regras do relatório, veja
[REGRAS_DO_RELATORIO.md](REGRAS_DO_RELATORIO.md).
