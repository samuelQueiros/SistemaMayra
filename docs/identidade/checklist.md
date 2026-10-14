# Caderno Lilás — checklist de aplicação (2026-10-14)

## Fundamentos
- [x] Tokens únicos em `frontend/public/identidade/tokens.css` (app + protocolo padrão); sistema antigo `--np-*` removido
- [x] Fontes self-hosted (Bricolage Grotesque, Figtree, JetBrains Mono) em `public/fonts/` com licenças OFL; Baloo 2/Nunito removidas
- [x] Classes base (`.btn-*`, `.input`, `.select`, `.card`, `.badge`, `.alert`, `.menu`…) em `src/styles/base.css`
- [x] Ícones lucide com traço 1.75; 20px em botões, 18px em tabelas
- [x] Foco visível (anel violeta-300) em tudo que é clicável

## Componentes (`src/components/ds/`)
- [x] Button (primário, secundário, tonal, fantasma, perigo; 36/44/52; carregando com spinner)
- [x] IconButton (44×44, aria-label obrigatório)
- [x] Input / Select / Textarea / Checkbox (foco, erro com ícone, desabilitado tracejado, busca com lupa)
- [x] Card, Badge (pílulas), Alert (info/sucesso/atenção/erro com ícone), EmptyState, ProgressBar, Tabs
- [x] PageHeader (sobrelinha violeta, título 40px Bricolage)
- [x] PatientAvatar (iniciais, cor fixa por nome: violeta/céu/sol)
- [x] Menu ⋯ (teclado: setas, Esc, Home/End)
- [x] SidebarNav (grupos Clínica/Sistema, ativo violeta-50, subitem com barrinha de 2px)
- [x] PhaseStepper, SectionBand, SaveStatus

## Telas
- [x] Layout (menu lateral, rodapé com avatar e sair, menu empilhado no celular)
- [x] Login
- [x] Todos os pacientes
- [x] Novo atendimento (escolha do protocolo + iframe com etiqueta de salvamento)
- [x] Protocolo padrão — `formulario-novo-paciente.html` (fases, faixa de título, aviso azul, campos, barra de ações, "Salvar laudo" violeta)
- [x] Atendimento com modelo próprio (fases, faixa, grade de 2 colunas, barra de ações)
- [x] Histórico do paciente (fotos, responsáveis, laudo por IA, protocolos)
- [x] Formulário dos responsáveis
- [x] Seções clínicas
- [x] Laudo por IA
- [x] Relatório por IA (revisão)
- [x] Diálogo PDF / Word
- [x] Configurações: registro profissional, capa, modelos de protocolo, editor de modelo, inteligência artificial
- [x] Registro de atividades (antigo "Ver Logs")

## Textos e acessibilidade
- [x] Só a primeira letra maiúscula em títulos, menus, botões e nomes de fases
- [x] Nomes de pacientes exibidos como nome (dado salvo intacto)
- [x] aria-label em botões só com ícone; estado nunca só por cor (texto/ícone)
- [x] Alvos ≥ 44px (exceto botões 36px de tabela, conforme a especificação)

## Verificação final
- [x] `npm run build`, `npm run lint`, `npm test` (50 testes)
- [x] Busca por cores fixas, fontes antigas e amarelo em botões (restam só no PDF/Word e na cor do nome da capa, que é dado)
