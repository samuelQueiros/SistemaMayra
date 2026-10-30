# Manutenção da VPS

Rotinas do dia a dia. Os valores entre `<...>` são seus; nunca grave senha, chave ou IP neste arquivo.
Complementa o [DEPLOY.md](../DEPLOY.md) (instalação inicial).

## Sumário

* [O que nunca rodar](#o-que-nunca-rodar)
* [Atualizar](#atualizar)
* [Voltar para a versão anterior](#voltar-para-a-versão-anterior)
* [Backup e restauração](#backup-e-restauração)
* [Logs e saúde](#logs-e-saúde)
* [Limpar o Docker sem perder dados](#limpar-o-docker-sem-perder-dados)
* [Dados de pacientes e o histórico do git](#dados-de-pacientes-e-o-histórico-do-git)

## O que nunca rodar

Os volumes guardam **todos os dados dos pacientes** (banco e arquivos).

| Comando | Por quê |
|---|---|
| `docker volume prune` | Apaga volumes que "não estão em uso" no momento, inclusive o do banco se o container estiver parado |
| `docker system prune --volumes` | Idem, junto com o resto |
| `docker compose down -v` | O `-v` apaga os volumes da stack |
| `rm -rf` em `/var/lib/docker/volumes` | Apaga banco e arquivos |
| Trocar o nome do volume (`db_data`, `app_storage`) | Cria volume vazio; os dados antigos ficam órfãos |

## Atualizar

Com `docker-compose.yml` (build na VPS):

```bash
cd <PASTA_DO_PROJETO>
./scripts/atualizar.sh   # backup, git pull, rebuild, confere /api/health
```

Com Portainer (imagem do GHCR): fluxo `push na master` → GitHub Actions publica `ghcr.io/<dono>/<repo>:latest`
→ na stack, "Pull and redeploy". As migrations rodam sozinhas no start.

Se na VPS existir um `atualizar-mayra.sh` próprio, ele não está neste repositório; confirme o que ele faz.

## Voltar para a versão anterior

A imagem publicada também recebe a etiqueta `sha-<commit>` de cada versão.

* **Portainer:** defina `APP_IMAGE=ghcr.io/<dono>/<repo>:sha-<COMMIT_ANTERIOR>` nas variáveis da stack e faça redeploy.
* **docker-compose:** `git checkout <COMMIT_ANTERIOR>` e `docker compose up -d --build`.
* **Cuidado com migrations:** voltar o código não desfaz alterações do banco. Se a versão nova criou uma migration, volte também com `alembic downgrade <REVISÃO>` ou restaure o backup feito antes da atualização. Sem migration nova (caso desta branch de documentação), basta trocar a imagem.

## Backup e restauração

```bash
./scripts/backup.sh      # banco + arquivos em ./backups (mantém os 14 últimos)
```

Agende às 3h com `crontab -e` e **copie os backups para fora da VPS**. Restauração (substitui os dados atuais):

```bash
gunzip -c backups/banco_<DATA>.sql.gz | docker compose exec -T db psql -U formpsico formpsico
docker compose exec -T app sh -c 'rm -rf /app/backend/storage/*'
docker compose exec -T app tar -C /app/backend -xzf - < backups/arquivos_<DATA>.tar.gz
docker compose restart app
```

Teste a restauração pelo menos uma vez num ambiente de teste. Backups guardam dados de saúde: permissão 600,
nunca em pasta pública.

## Logs e saúde

```bash
docker compose ps
docker compose logs --tail=100 app
docker compose exec -T app python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health').read())"
```

Os logs não devem conter dados de pacientes. Se aparecer algum, trate como falha e corrija.

## Limpar o Docker sem perder dados

```bash
docker image prune -f          # só imagens sem uso
docker builder prune -f        # cache de build
```

Antes, confira `docker volume ls` e faça um backup.

## Dados de pacientes e o histórico do git

Nomes de pacientes que apareciam em testes e comentários foram retirados dos arquivos, mas **continuam nos
commits antigos**. Se o repositório (ou o pacote no GHCR) for público, é preciso reescrever o histórico ou
mantê-lo privado. Pastas de referência (`reclamacoes`, `referencias`, etc.) ficam fora do repositório.
