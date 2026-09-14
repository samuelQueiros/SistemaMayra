# Sistema de Relatório Automático — Apresentação

> Documento pensado para apresentar o sistema a alguém que não vai ler
> código (ex.: sócio, investidor) — o que é, o que já funciona, o que
> falta, e quanto custa manter no ar. Para o histórico técnico detalhado
> de cada entrega, ver `ENTREGAS.md`.

## 1. O que é

Uma plataforma web para a clínica da Mayra Vanessa (neuropsicopedagoga)
substituir o processo manual de aplicar escalas de avaliação (CARS, ATA,
SNAP-IV, Portage/IPO...) e escrever o laudo em um editor de texto comum.

Hoje, com o sistema:

1. A psicóloga faz login com sua própria conta.
2. Cadastra o paciente (ou já tem cadastrado).
3. Escolhe a escala e preenche um formulário guiado — o sistema já sabe
   quais perguntas fazer, porque cada escala foi cadastrada como um
   "modelo" configurável (não é código fixo; ver seção 3).
4. O sistema **calcula a pontuação e a classificação automaticamente**,
   monta o gráfico, e **gera um rascunho do texto do laudo com IA** —
   sempre revisável antes de qualquer exportação.
5. A psicóloga revisa/edita o texto, completa seções clínicas extras se
   quiser (anamnese, hipóteses diagnósticas com CID, plano de
   intervenção...), e baixa o **PDF pronto**, com gráfico, tabela e
   assinatura.
6. Tudo fica salvo no histórico do paciente — dá para ver, editar
   (com log de auditoria de qualquer correção) e gerar um PDF
   **consolidado** juntando vários atendimentos num só parecer.

Não existe mais planilha solta, Word avulso ou cálculo manual de
pontuação — e cada psicóloga só acessa os próprios pacientes (dado de
saúde é sensível, isolado por conta).

## 2. O que já está pronto (visão geral)

| Área | Status |
|---|---|
| Login e conta por psicóloga (dados isolados entre contas) | ✅ Pronto |
| Cadastro de pacientes | ✅ Pronto |
| Motor de cálculo das escalas (3 formatos diferentes de pontuação) | ✅ Pronto |
| Formulário que se monta sozinho a partir da escala escolhida | ✅ Pronto |
| Gráfico automático do resultado | ✅ Pronto |
| Texto do laudo redigido por IA (sempre revisável) | ✅ Pronto |
| Exportação em PDF (individual e consolidado de vários atendimentos) | ✅ Pronto |
| Seções clínicas extras (anamnese, hipóteses com CID, plano de intervenção, fotos, assinatura) | ✅ Pronto |
| Cadastro de novas escalas subindo o documento — a IA monta o modelo | ✅ Pronto |
| Histórico do paciente com edição e log de quem mudou o quê | ✅ Pronto |
| Tela de configuração da chave de IA (cada psicóloga usa a própria) | ✅ Pronto |
| Aparência com a identidade visual da marca (cores, logo, tipografia) | ✅ Pronto |
| Preparado para produção (Docker, checklist de segurança) | ✅ Pronto |

**123 testes automatizados** cobrindo login, isolamento entre contas,
cálculo de cada escala e geração de PDF — todos passando.

## 3. Decisão de design mais importante: escalas configuráveis

As escalas (CARS, ATA, SNAP-IV, Portage...) **não estão fixas no código**.
Elas são cadastradas como um "modelo" — um formato de dados que descreve
as perguntas, os pesos e como calcular a pontuação. Isso significa que
**uma escala nova não exige programação**: a psicóloga sobe o documento
da escala (PDF/DOCX/TXT) e a IA já extrai um rascunho do modelo para ela
revisar e salvar. Isso é o que torna o sistema reutilizável no longo
prazo, em vez de um software que só funciona para as 3-4 escalas
pensadas hoje.

## 4. O que ainda está pendente (transparência)

- **Escala ATA incompleta**: só 3 dos 22 itens oficiais foram fornecidos
  até agora. O caminho para completar já existe (subir o documento
  oficial pela tela "Modelos De Laudo").
- **Portage/IPO**: o cálculo funciona, mas só tem um exemplo pequeno
  cadastrado — falta a psicóloga alimentar os itens reais por área.
- **Nenhuma chamada de IA foi testada com uma chave paga de verdade**
  nesta máquina de desenvolvimento — toda a integração foi validada com
  simulações; falta só configurar uma chave real (Anthropic, OpenAI ou
  Google) para começar a usar de fato.
- **Sem teste automatizado de frontend** (a validação da tela foi manual)
  — não é um requisito de segurança, é só uma cobertura extra possível.
- **Sem limite de tentativas de login** (proteção contra força bruta) —
  recomendável antes de expor publicamente numa clínica com muitos
  acessos externos.

Nada disso impede uma demonstração ou um primeiro uso real controlado —
são pontos para amadurecer com o uso.

## 5. Onde hospedar gratuitamente para uma demonstração

O sistema já está pronto para subir com um único comando de Docker,
então qualquer serviço que aceite "suba este Dockerfile" funciona. Para
mostrar ao sócio sem gastar nada, a combinação mais simples é:

### Backend/aplicação: [Render.com](https://render.com) (grátis)
- Cria uma "Web Service" direto a partir do repositório no GitHub — o
  Render lê o `Dockerfile` que já existe no projeto e builda sozinho.
- HTTPS automático, URL pública (algo como `https://seusistema.onrender.com`).
- **Limitação do plano grátis**: o serviço "dorme" depois de ~15 minutos
  sem uso, e demora uns 30-60 segundos para acordar na primeira visita
  depois disso. Para a demonstração, vale abrir o link uns 2 minutos
  antes da reunião para ele já estar "acordado".

### Banco de dados: [Neon.tech](https://neon.tech) (grátis)
- Postgres gratuito que **não expira** (diferente do Postgres grátis do
  próprio Render, que é apagado depois de 90 dias) — mais adequado para
  uma demo que vai ficar no ar por um tempo.
- Cria o projeto, copia a "Connection String" e usa como `DATABASE_URL`.

### Passo a passo resumido
1. Subir o código para um repositório no GitHub.
2. Criar o banco grátis no Neon e copiar a connection string.
3. Criar a Web Service no Render, conectar o repositório (Render detecta
   o Dockerfile sozinho).
4. Configurar as variáveis de ambiente no painel do Render:
   `DATABASE_URL` (do Neon), `JWT_SECRET` (qualquer texto aleatório longo),
   `ENV=production`. As chaves de IA **não precisam** ser configuradas
   aqui — cada psicóloga configura a própria na tela "Configurações"
   depois de logar.
5. Deploy. Depois do primeiro deploy, registrar a primeira conta pela
   própria tela do sistema (`/` → criar conta).

*(Ver `DEPLOY.md` no projeto para o checklist completo, incluindo o que
trocar antes de um uso real com pacientes de verdade — principalmente o
`JWT_SECRET` de exemplo.)*

### Alternativa sem "soneca"
Se a demonstração for ao vivo e o delay de acordar incomodar, o
[Fly.io](https://fly.io) tem uma cota gratuita que roda o container
sempre ligado (sem dormir), também lendo o `Dockerfile` direto — um
pouco mais técnico de configurar (usa uma ferramenta de linha de
comando), mas resolve esse problema específico.

## 6. Custo estimado para manter no ar de verdade

Hospedagem gratuita é ótima para demonstrar, mas tem limites (dorme,
banco pequeno, sem backup garantido) — não é recomendada para uso real
com dados de pacientes. Estimativas de custo mensal, dependendo do
tamanho:

| Cenário | O que inclui | Custo aproximado/mês |
|---|---|---|
| **Demonstração** (o que foi descrito acima) | Render grátis + Neon grátis | **R$ 0** |
| **Produção enxuta** (uma clínica pequena/média) | Um servidor pequeno (VPS) rodando tudo junto — app + banco no mesmo lugar (ex.: Hetzner, DigitalOcean) | **R$ 25 – 60** |
| **Produção com serviços gerenciados** (mais robusto, sem administrar servidor) | Web service pago (sem dormir) + banco Postgres gerenciado com backup automático, ambos no Render/Railway ou similar | **R$ 80 – 190** |
| **Domínio próprio** (opcional, ex. `sistema.neuropp.com.br`) | Registro do domínio | **R$ 40 – 80/ano** |

**Custo da IA (texto do laudo) é separado da hospedagem** — é cobrado
diretamente pelo provedor escolhido (Anthropic, OpenAI ou Google), por
uso, na chave que cada psicóloga configura. Cada geração de texto usa
poucos milhares de "tokens" (uma fração de centavo a poucos centavos de
dólar por laudo, dependendo do modelo escolhido). Para o volume de uma
clínica pequena/média, isso costuma ficar na casa de **US$ 2 – 10/mês**
(≈ R$ 10 – 55/mês) mesmo com uso frequente — não é um custo que escala
junto com o número de psicólogas cadastradas, só com quantos laudos são
gerados por IA.

**Resumo prático**: dá para mostrar o sistema ao sócio hoje sem gastar
nada, e colocar em uso real por uma clínica pequena por algo entre
R$ 25 e R$ 90 por mês (hospedagem) + um valor pequeno e variável de IA,
sem precisar de investimento inicial em infraestrutura.
