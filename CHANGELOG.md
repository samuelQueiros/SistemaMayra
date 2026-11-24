# Histórico de mudanças

Resumo por data, em linguagem simples, montado a partir do git. Os detalhes estão em
[ENTREGAS.md](ENTREGAS.md) e o panorama em [docs/ESCOPO.md](docs/ESCOPO.md).

## 2026-11-24

### Corrigido
* Texto de TEA aparecendo em relatório de TDAH: a conclusão (após o gráfico de domínios), o 1º parágrafo das Considerações Finais e a frase "Partindo de uma hipótese diagnóstica de…" da metodologia agora seguem a hipótese principal. Para outras hipóteses (ex.: TPAC) o texto é neutro e usa o nome da hipótese. Os textos de TDAH e o neutro são adaptações e aguardam revisão da Mayra.
* Cabeçalho do paciente no Word (foto + identificação) saía com bordas em todas as células e o texto sem negrito, num parágrafo só.
* XML do Word fora da ordem do schema (elementos repetidos e fora de ordem), que o Word do Windows perdoa mas Word para Mac, Pages e Google Docs não.
* Título e cabeçalho das tabelas de quadros ficam presos à primeira linha no Word.
* Gráfico do Portage: legenda movida para baixo, sem encostar nos números.

### Alterado
* Gráficos CARS e ATA menores (110 mm de largura em vez de 170 e 165 mm).

## 2026-10-30

### Alterado
* Fechamento do relatório no padrão da Mayra: texto novo "A análise dos comportamentos…" antes do "Vale ressaltar", "Desde já…" junto da assinatura, sem caixa azul.
* Documentação, organização e nomes mais claros (sem mudar o funcionamento): README, `docs/`, comentários no código, `pdf.py` virou `pdf_do_laudo.py`.

### Corrigido
* Removida a frase "OBSERVAÇÃO: este relatório não configura um laudo médico".
* Removido o bloco "Sobre a profissional" que repetia um parágrafo.

## 2026-10-27

### Adicionado
* Testes com gráficos reais no relatório, no PDF e no Word.

## 2026-10-23

### Corrigido
* Considerações Finais duplicadas e texto de TDAH aparecendo com hipótese de TEA.

## 2026-10-21

### Alterado
* Paleta, ordem das seções e aviso legal conforme o relatório-modelo; assinatura em caligrafia com credencial e registro.

### Corrigido
* Assinatura sempre com o nome completo da profissional.

## 2026-10-18 e 2026-10-19

### Adicionado
* Pontuação da ATA feita pelo sistema; hipóteses CID-11 com subtipos e encaminhamentos escolhidos antes de gerar; desfralde, ano escolar e habilidades escolhidos pela psicóloga.
* Barra de progresso na geração do Laudo por IA.

### Alterado
* Documento e estética iguais ao relatório-modelo de referência; Laudo por IA mais rápido.

### Corrigido
* O documento não trava mais em silêncio; gráficos com nomes completos; observação do Portage fora de laudos já gerados.

## 2026-10-14 e 2026-10-15

### Adicionado
* Laudo por IA como único fluxo por PDFs, em segundo plano, com agentes e cache.
* Pendências: completar dados digitando ou por foto/documento, e "Atualizar relatório".
* Identidade visual "Lavanda Premium"; ícone do aplicativo.
* Exclusão definitiva de paciente com confirmação.

### Alterado
* Várias otimizações de velocidade (listas leves, índices, compressão, capa menor, 2 processos).

### Corrigido
* A geração não trava mais com 3 ou mais PDFs; erros de IA com mensagens claras.

## 2026-10-05

### Adicionado
* Modelos de protocolo próprios; capa personalizável; Relatório por IA a partir de PDFs; todos os principais provedores de IA; menu Pacientes e Registro de atividades; configurações em submenu.
* Imagem Docker sem segredos, container sem root e roteiro de deploy.

### Alterado
* Auditoria de segurança (cabeçalhos, limites de upload).

## 2026-09-28

### Adicionado
* Formulários dos responsáveis; considerações finais e sugestões por IA; deploy com docker-compose e Caddy; stack para Portainer com imagem no GHCR; ícones de escala na metodologia.

### Corrigido
* Nota sobre os percentuais, termo "percentil" retirado, só a hipótese selecionada, ressalva da faixa do Portage, aviso de divergência nas funções executivas.

## 2026-09-20 a 2026-09-23

### Alterado
* O sistema passou a girar em torno do protocolo fixo da Mayra, com autosave no banco.

### Adicionado
* Relatório idêntico ao modelo oficial em PDF e Word; formulário em etapas; fotos sincronizadas com a galeria.

## 2026-09-12 a 2026-09-14

### Adicionado
* Primeira versão completa: login, pacientes, motor de regras, histórico, gráficos, PDF, IA no texto do parecer, segurança básica e preparação para implantação.
