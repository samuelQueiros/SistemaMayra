# Regras do relatório

Todas as regras clínicas e de montagem num só lugar. "Onde está" aponta o arquivo de origem. Quase tudo
vive em `frontend/public/formulario-novo-paciente.html` (chamado abaixo de **HTML**), na função
`gerarDocumentoLaudoHTML()`. Quem mudar uma regra deve conferir também as cópias indicadas.

## Sumário

* [Ordem das seções](#ordem-das-seções)
* [Regras de idade](#regras-de-idade)
* [Escalas e cálculos](#escalas-e-cálculos)
* [Textos obrigatórios e termos proibidos](#textos-obrigatórios-e-termos-proibidos)
* [Fechamento do relatório](#fechamento-do-relatório)
* [Tabelas, gráficos e Word](#tabelas-gráficos-e-word)
* [O que a IA pode e não pode fazer](#o-que-a-ia-pode-e-não-pode-fazer)
* [Divergências com o pedido de documentação](#divergências-com-o-pedido-de-documentação)

## Ordem das seções

Do início ao fim do documento (HTML, `gerarDocumentoLaudoHTML()`):

1. Capa (arte padrão, capa da psicóloga ou capa só do relatório; nome do paciente opcional).
2. Identificação (foto no cabeçalho, caixa com os dados).
3. Faixa "PARECER NEUROPSICOPEDAGÓGICO ANÁLISE COMPORTAMENTAL" e metodologia ("METODOLOGIA E PROTOCOLOS UTILIZADOS").
4. Anamnese inicial e histórico de desenvolvimento; aspectos comportamentais.
5. Quadros por hipótese e por área do desenvolvimento (a análise por área só aparece com TDAH entre as hipóteses).
6. Habilidades acadêmicas do ano escolar (tabela e gráfico) e quadros das funções executivas.
7. Portage (texto, interpretação e gráfico de idade de desenvolvimento).
8. CARS e ATA (texto e gráfico).
9. SNAP-IV **ou** M-CHAT (ver idade); TOD só se algum item foi respondido.
10. Corroboração, hipóteses e/ou confirmações diagnósticas (todas as marcadas, com CID), síntese clínica.
11. Encaminhamentos.
12. Considerações Finais (três textos, abaixo).
13. Nota sobre os resultados, "Desde já…", local e data, "Atenciosamente", assinatura.
14. Galeria "REGISTROS DOS ATENDIMENTOS" numa página própria (fotos só no cabeçalho e aqui, nunca no meio do texto).

Nenhuma quebra de página é forçada no meio do texto, exceto antes da galeria.

## Regras de idade

| Regra | Valor | Onde está |
|---|---|---|
| M-CHAT entra no relatório | De **16 a 30 meses**, no lugar do SNAP-IV | HTML, `idadeDoMCHAT()` e `metodoNoRelatorio()` |
| SNAP-IV entra no relatório | Em **todas as outras idades** (fora de 16 a 30 meses) | HTML, `metodoNoRelatorio("snap")` |
| Lista de itens do M-CHAT na tela | Só até 30 meses | HTML, `carregarMCHAT()` |
| Faixa do Portage | 0 a 72 meses, em faixas de 12 meses (0-12, 13-24, 25-36, 37-48, 49-60, 61-72) | HTML, `faixaPortage()`, `PORTAGE_IDADE_MAX_MESES` |
| Portage acima de 72 meses | Resultado é só referência de repertório, não comparação normativa; entra uma ressalva automática | HTML, `idadeForaDaFaixaPortage()` |

## Escalas e cálculos

| Escala | Regra | Onde está |
|---|---|---|
| CARS | Soma dos itens, só quando todos estão respondidos. "Percentual de falhas" = (total − 15) ÷ 45, de 0 a 100% | HTML, `calcularCARS()`, `atualizarPercentualCARS()` |
| ATA | 22 itens, nota 0, 1 ou 2 (total 0 a 44). Item: nenhuma caixa marcada = 0, uma = 1, duas ou mais = 2. % do item = marcadas ÷ caixas do item. % total = pontos ÷ 44 | HTML `calcularATA()`; backend `services/ata.py` (Laudo por IA) |
| SNAP-IV | 18 itens (0-8 desatenção, 9-17 hiperatividade). Nota 2 ou 3 conta como sintoma. Limiar do relatório: 6 sintomas por bloco | HTML, `analisarSNAP()` e `LIMIAR` |
| TOD | Cada resposta "1" (Sim) é um sintoma; % = sintomas ÷ itens, só com todos respondidos | HTML, `analisarTOD()` |
| M-CHAT | Ver regra de idade | HTML, `carregarMCHAT()` |
| Portage | % = pontos ÷ itens. Idade cognitiva estimada = idade em meses × %. Leitura com tolerância de 2 meses | HTML, `calcularPortage()` |
| Probabilidade por hipótese | Estimativa descritiva. TEA é a média do ATA e do CARS (aqui o ATA usa 50 como máximo, ver divergências) | HTML, `probabilidades()` |

Escalas podem ser tiradas do relatório pela psicóloga (`__metodosExcluidos`): os dados continuam salvos e só
os blocos somem. Backend: `api/pendencias.py`.

## Textos obrigatórios e termos proibidos

| Regra | Onde está |
|---|---|
| **Nota sobre os resultados** sempre presente, perto da assinatura: percentuais são descritivos e clínico-observacionais, **não** são percentis normativos | HTML, `notaSobreOsResultados`; Word/PDF de laudos antigos: `no_modelo_atual()` em `services/laudo_documento.py` |
| Proibido o termo **"percentil"** em qualquer outro ponto (relatório e prompts da IA) | HTML; `LIMITES_DA_IA` em `services/ai/chains.py` |
| Proibido o título **"Analista Comportamental"**; a credencial é "Especialista em Análise do Comportamento Aplicada - ABA" | `_TROCAS` em `services/laudo_documento.py`; credencial da assinatura no HTML |
| Relatório mostra **só a hipótese selecionada**/marcadas, nunca todas as possíveis | HTML, `hipotesesParaRelatorio()` |
| Ressalva automática quando a idade excede a faixa do Portage | HTML, `avisoFaixaEtariaPortage()` |
| Aviso sobre divergência entre gráfico e texto das funções executivas | HTML |

## Fechamento do relatório

Ordem desde 30/10 (OBS-01 a OBS-04), em "Considerações Finais":

1. Texto "**A ANÁLISE DOS COMPORTAMENTOS**…" (igual para todos os relatórios; **a confirmar** com a Mayra, ver `ESCOPO.md` P1/P2), com negritos.
2. Texto sobre TEA em meninas, quando o sexo é Feminino e a hipótese é TEA (`consideracoesFinaisTEAMeninas()`).
3. "Vale ressaltar que não se deve rejeitar nenhuma mudança…" (`avisoLegalFechamento()`).
4. Nota sobre os resultados, sem caixa azul (classe `fechamento-texto`).
5. "Desde já, coloco-me à disposição…" junto de local, data e "Atenciosamente".

A frase "OBSERVAÇÃO: este relatório não configura um laudo médico" **saiu**. O bloco "Sobre a profissional" também
saiu do protocolo padrão (repetia um parágrafo). Modelos próprios e o relatório por PDFs ainda o imprimem.

## Tabelas, gráficos e Word

* Cada bloco gráfico segue o formato título → tabela → gráfico (ATA: gráfico → tabela; SNAP-IV: dois gráficos lado a lado).
* Tabelas **inteiras** no Word: linhas não se quebram entre páginas e o cabeçalho repete; a tabela fica presa ao gráfico que vem depois (`_prender_ao_proximo` em `services/laudo_documento.py`).
* Rótulos dos gráficos por extenso (`quebrarRotulo()`), nunca abreviados.
* O Word só entende as classes CSS que o formulário gera (`cab-paciente`, `faixa`, `faixa-topico`, `caixa-cinza`, `tabela`, `grafico`, `fotos`, `quebra`…). Mudou o gerador, confira `_ConversorDocx`.
* Teste que garante os gráficos no relatório, no PDF e no Word: `backend/tests/test_graficos_exportacao.py`, `frontend/src/laudo/graficosDoLaudo.test.js`.
* Cópia do visual para modelos próprios e relatório por PDFs: `frontend/src/laudo/css.ts`, `documento.ts`.

## O que a IA pode e não pode fazer

| Pode | Não pode |
|---|---|
| Transcrever PDFs para JSON (pergunta + opção marcada) | Interpretar, resumir ou concluir na etapa de transcrição; inventar resposta |
| Preencher campos do catálogo (anamnese, escalas, desenvolvimento) com valores válidos | Preencher campo fora do catálogo ou com opção inexistente (descartado) |
| Estimar `fe_perc_N` (funções executivas) com 2 a 4 frases de manifestação | Inventar sintomas, diagnósticos, escalas ou dados que não estejam nos documentos |
| Redigir o estudo de caso e integrar dados novos confirmados | Fechar diagnóstico, usar "percentil", dizer que o texto foi gerado por IA |
| Sugerir valores lendo anexos (com o trecho que os sustenta) | Aplicar sugestão sem a psicóloga confirmar |
| Escrever `hab_obs_N` coerente com o desempenho escolhido | Escolher hipóteses, encaminhamentos, desfralde, ano escolar ou desempenho nas habilidades (isso é da psicóloga) |
| — | Pontuar a ATA (é do sistema) |

Prompts e limites: `backend/app/services/ai/chains.py` (`PERSONA`, `LIMITES_DA_IA`, `ESTILO_DE_ESCRITA`) e
`services/ai/agentes/`. Quem altera um prompt de extração deve subir `VERSAO_DA_EXTRACAO`.

## Divergências com o pedido de documentação

* O pedido citava "SNAP-IV a partir de 6 anos". **O código não tem essa regra de idade**: o SNAP-IV aparece em todas as idades fora de 16 a 30 meses. O número 6 é o limiar de sintomas por bloco. Se a regra de 6 anos é desejada, é uma mudança de comportamento a combinar com a Mayra.
* "M-CHAT só até 30 meses; acima disso some" está correto; falta dizer que **abaixo de 16 meses também não entra**.
* ATA: o percentual do relatório divide por 44, mas a estimativa de probabilidade de TEA divide por 50 (herança do protótipo). Não alterado.
