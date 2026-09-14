# Material de referência enviado pela psicóloga (cliente)

Estes arquivos **não fazem parte do sistema novo** — são o protótipo/material
atual da cliente, usados só como insumo para desenhar os `schema_json` reais
dos templates de laudo (SPEC.md seção 3) e o formato de saída da IA
(seção 5). Não editar nem referenciar a partir do código do backend/frontend.

- `formulario_prototipo_cliente.html` — protótipo atual da psicóloga: um
  único HTML client-side (sem backend), com formulário dinâmico, autosave em
  `localStorage`, exportação para PDF/Word via impressão do navegador, e uma
  "IA" caseira baseada em casamento de palavras-chave (funções
  `regrasInterpretativasTEA` / `regrasInterpretativasOutrosTranstornos`) que
  gera os quadros interpretativos a partir do texto livre do Estudo de Caso.
  Contém a implementação de referência das escalas ATA, CARS, SNAP-IV, TOD,
  Portage (idade cognitiva por área) e M-CHAT, além da estrutura completa do
  laudo final (identificação, anamnese, desenvolvimento, metodologia,
  quadros, hipóteses diagnósticas com CID, gráficos Chart.js, plano de
  intervenção, encaminhamentos, considerações finais, assinatura).
- `RELATORIO_FINAL_ARTHUR_DANIEL__assinado.pdf` — exemplo de laudo final
  gerado pelo protótipo acima, já assinado. Mostra o produto esperado
  (gráficos por área do CARS/ATA, distribuição de déficits em funções
  executivas, hipóteses diagnósticas e CID de fechamento).
- `ESTUDO DE CASO - SAFIRA KEROLAINY.pdf` — exemplo de estudo de caso bruto
  (texto livre + tabela comportamento → critério DSM-5-TR) que alimenta o
  campo "Estudo de Caso" do formulário e deveria alimentar o prompt da IA
  real (LangChain) no lugar do casamento de palavras-chave atual.
- `AVALIAÇÃO COGNITIVA.pdf` e `AVALIAÇÃO DA EQUIPE.pdf` — checklists
  adicionais (habilidades cognitivas/metacognitivas, socioemocionais,
  motoras, e avaliação de funções executivas) usados pela clínica em papel;
  ainda não estão representados no `schema_json` do protótipo HTML e são
  candidatos a virar novos `ReportTemplate`/seções do laudo.
