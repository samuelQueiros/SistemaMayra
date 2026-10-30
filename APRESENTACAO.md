> **Aviso (30/10/2026):** este documento é de apresentação e está parcialmente desatualizado (por exemplo, o
> PDF consolidado foi removido em 05/10). O estado atual está no [README](README.md) e em [docs/ESCOPO.md](docs/ESCOPO.md).

# Sistema de Relatório Automático — Apresentação

> Documento pensado para apresentar o sistema a alguém que não vai ler
> código (ex.: sócio, investidor) — o que é, o que já funciona, o que
> falta, e quanto custa manter no ar. Para o histórico técnico detalhado
> de cada entrega, ver `ENTREGAS.md`.

## 1. O que é

Uma plataforma web para a clínica da Mayra Vanessa (neuropsicopedagoga)
substituir o processo manual de aplicar o protocolo de avaliação
neuropsicopedagógica e comportamental (CARS, ATA, SNAP-IV, TOD, M-CHAT,
Portage/IPO...) e escrever o laudo em um editor de texto comum.

Hoje, com o sistema:

1. A psicóloga faz login com sua própria conta.
2. Clica em "Novo Atendimento" — abre, dentro do próprio sistema, o
   protocolo completo de avaliação (o mesmo formulário que a psicóloga já
   usava e validou, agora integrado ao sistema — não precisou reaprender
   nada nem reescrever nenhuma escala do zero).
3. Preenche o formulário: identificação, histórico, escola, e os
   protocolos aplicados. **Cada campo preenchido é salvo automaticamente
   no banco de dados** assim que o atendimento é iniciado — não depende
   de lembrar de salvar.
4. O próprio formulário **calcula a pontuação de cada protocolo, monta o
   quadro de observações associando comportamentos a critérios
   diagnósticos, e estima probabilidades por hipótese diagnóstica** —
   tudo automático, sempre revisável antes de fechar o laudo.
5. Ao concluir, o laudo final (com gráfico, tabelas e assinatura) fica
   pronto para exportar em **PDF**.
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
| Protocolo completo de avaliação embutido no sistema (CARS, ATA, SNAP-IV, TOD, M-CHAT, Portage) | ✅ Pronto |
| Autosave de cada campo direto no banco de dados (não só no navegador) | ✅ Pronto |
| Cálculo automático de pontuação/classificação de cada protocolo | ✅ Pronto |
| Quadro de observações clínicas associado a critérios diagnósticos, gerado automaticamente | ✅ Pronto |
| Gráfico automático de probabilidades por hipótese diagnóstica | ✅ Pronto |
| Exportação em PDF (individual e consolidado de vários atendimentos) | ✅ Pronto |
| Seções clínicas extras (anamnese, hipóteses com CID, plano de intervenção, fotos, assinatura) | ✅ Pronto |
| Histórico do paciente com edição e log de quem mudou o quê | ✅ Pronto |
| Aparência com a identidade visual da marca (cores, logo, tipografia) | ✅ Pronto |
| Preparado para produção (Docker, checklist de segurança) | ✅ Pronto |

**140 testes automatizados** de backend cobrindo login, isolamento entre
contas e geração de PDF, todos passando.

## 3. Decisão de design mais importante: o protocolo é o próprio formulário validado pela psicóloga

Diferente de uma versão anterior deste sistema (que tentava deixar cada
escala "configurável" por dentro, como se fossem peças montáveis
genéricas), o sistema hoje usa **o formulário exato que a psicóloga já
desenvolveu e testa há tempo** — com toda a lógica de pontuação, o quadro
de observações e o cálculo de probabilidades exatamente como ela
projetou. Isso elimina o risco de a "tradução" para um formato genérico
perder nuances clínicas, e faz o sistema já nascer usando um protocolo
validado na prática, em vez de recriar do zero. O custo dessa escolha:
adicionar uma escala/protocolo novo hoje significa editar o formulário
diretamente (não existe mais uma tela de "montar modelo" sem programação)
— uma troca deliberada em favor de fidelidade ao que já funciona.

## 4. O que ainda está pendente (transparência)

- **Fotos do paciente**: hoje entram junto com o laudo/PDF do atendimento,
  mas ainda não aparecem na galeria separada "Fotos Do Paciente" do
  Histórico — funcional, só falta essa segunda vitrine.
- **Sem teste automatizado de frontend para a tela nova** de "Novo
  Atendimento" (a tela em si é só uma moldura — a lógica pesada está no
  formulário, testada manualmente).

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

**Não há custo de IA hoje**: o texto do laudo e o cálculo de cada
protocolo são gerados pelo próprio formulário (regras fixas, sem chamar
nenhum serviço de IA pago) — diferente de uma versão anterior do sistema,
que dependia de uma chave de API paga por geração de texto. A tela de
configuração de IA e o suporte a Anthropic/OpenAI/Google continuam
existindo no sistema para uso futuro, mas não são necessários para o
fluxo de hoje.

**Resumo prático**: dá para mostrar o sistema ao sócio hoje sem gastar
nada, e colocar em uso real por uma clínica pequena por algo entre
R$ 25 e R$ 90 por mês, só de hospedagem — sem custo variável de IA no
fluxo principal.
