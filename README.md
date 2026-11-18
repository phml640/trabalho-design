# Gestão de filas e atendimento presencial

Protótipo acadêmico de Design de Software para organizar filas, emitir senhas,
aplicar prioridade e conduzir o atendimento presencial. A demonstração inclui o
ciclo completo, histórico persistente e uma integração de notificação substituível,
inicialmente simulada.

## Executar a aplicação completa

Requer apenas Docker Engine/Desktop funcionando e Docker Compose v2.20 ou superior.
Não é necessário instalar Python, Node.js ou PostgreSQL no computador.

```bash
git clone https://github.com/phml640/trabalho-design.git
cd trabalho-design
docker compose up --build
```

Se o repositório já estiver clonado, execute somente o último comando na raiz.
A primeira execução precisa de internet para baixar imagens e dependências.
Aguarde os serviços ficarem saudáveis. Para executar em segundo plano e esperar
os healthchecks:

```bash
docker compose up --build -d --wait
docker compose ps
```

| Acesso | Endereço padrão |
| --- | --- |
| Página inicial | <http://localhost:8080> |
| Usuário | <http://localhost:8080/usuario> |
| Administrador/atendente | <http://localhost:8080/admin> |
| Swagger | <http://localhost:8000/docs> |
| OpenAPI | <http://localhost:8000/openapi.json> |
| Saúde da API pelo proxy | <http://localhost:8080/api/health> |

O Compose inicia PostgreSQL, espera seu healthcheck, inicia a API e aplica
`alembic upgrade head` antes do Uvicorn. O Nginx só inicia após a API saudável.
Ele serve o build React e encaminha `/api/` à API, preservando filtros e erros
HTTP. O navegador usa a mesma origem, sem configuração manual de CORS.
Os healthchecks conferem banco, processo HTTP e o proxy do frontend.

### Configuração demonstrativa

O comando funciona sem criar `.env`. Os padrões públicos são banco `gestao_filas`,
usuário `gestao` e senha **exclusivamente demonstrativa** `gestao_demo_local`.
Para personalizar portas ou credenciais locais:

```bash
cp .env.example .env
# Edite os valores desejados e execute novamente o Compose.
```

| Variável | Padrão no Compose |
| --- | --- |
| `FRONTEND_PORT` | `8080` |
| `API_PORT` | `8000` |
| `POSTGRES_PORT` | `5432`, publicada somente no endereço local |
| `POSTGRES_DB` | `gestao_filas` |
| `POSTGRES_USER` | `gestao` |
| `POSTGRES_PASSWORD` | `gestao_demo_local` |

A API usa o host interno `postgres:5432`; o Nginx usa `api:8000`. As portas
publicadas ficam em `127.0.0.1`. Variáveis do host como `DATABASE_URL` não
substituem essa composição. Alterar usuário/senha/banco no `.env` não modifica
um volume PostgreSQL que já foi inicializado: conserve a configuração anterior
ou limpe explicitamente o volume descartável antes de começar outra demonstração.

### Parar, reiniciar e limpar

```bash
# Logs dos três serviços
docker compose logs -f

# Reiniciar, conservando os dados
docker compose restart
docker compose up -d --wait

# Parar e remover containers/rede, mantendo o banco
docker compose down

# Iniciar novamente com os mesmos dados
docker compose up --build -d --wait

# Apagar o volume PostgreSQL e todos os dados da demonstração
docker compose down -v
```

O volume nomeado `postgres_data` sobrevive a reinícios e a `down`. Somente a
limpeza com `-v` remove seus dados. Migrações são reaplicadas de forma idempotente
na inicialização da API. Uma falha de migração impede a API de servir um esquema
incompatível; consulte `docker compose logs api` para diagnosticar.

## Stack e arquitetura

| Parte | Tecnologias |
| --- | --- |
| Backend | Python 3.11+, FastAPI, Uvicorn; imagem Python 3.12 |
| Persistência | PostgreSQL 17, SQLAlchemy 2.0, psycopg 3, Alembic |
| Frontend | React, TypeScript, Vite, CSS próprio; build com Node 24 |
| Servidor web | Nginx 1.30, SPA e proxy `/api` |
| Testes | unittest, PostgreSQL real, cliente HTTP da biblioteca padrão e Playwright |

O backend é um **monólito modular com características de Arquitetura Hexagonal**.
`gestao_filas` coordena filas; `gestao_senhas` contém senha, seleção e atendimento;
`gestao_compartilhada` concentra contratos transacionais, virada, histórico e
notificações. Casos de uso dependem de portas e do domínio. API e adaptadores
fazem a tradução para HTTP, PostgreSQL e notificação simulada. Há uma única
transação local de negócio, sem microsserviços, Redis ou mensageria externa.

A composição em `criar_app()` seleciona a unidade de trabalho e o notificador.
A seleção, o contador da fila, o estado, o histórico e a Outbox confirmam ou
revertem juntos. PostgreSQL bloqueia a linha da fila; o adaptador em memória
permanece para testes rápidos em um processo. A entrega da notificação ocorre
após o commit, sem transação aberta durante o envio.

Responsabilidades, GRASP/SOLID, coesão, acoplamento, trade-offs e evolução dos
adaptadores estão em [docs/componentes.md](docs/componentes.md). A API externa
de horários citada no levantamento inicial **não foi implementada e está fora
do escopo do protótipo**. Não é uma dependência necessária à execução.

## Roteiro de demonstração em duas janelas

1. Abra `/admin`, clique em **Nova fila** e crie uma fila. Informe o identificador
   do atendente e o guichê, sem usar dados pessoais reais.
2. Em outra janela, abra `/usuario`, escolha a fila e emita uma senha normal.
   O número e o estado retornados pela API aparecem em destaque.
3. Para demonstrar prioridade, emita senhas prioritárias em janelas/perfis de
   usuário independentes. Havendo ambas as classes, o backend chama até duas
   prioritárias consecutivas antes de uma normal, mantendo FIFO dentro da classe.
4. No administrador, consulte as senhas e clique em **Chamar próxima senha**.
   A visão do usuário mostra a chamada e o guichê nas consultas periódicas,
   normalmente a cada três segundos, sem recarregar a página.
5. Clique em **Iniciar atendimento** e **Finalizar atendimento**. Consulte as
   transições na aba **Histórico**, incluindo o filtro `Finalizada` e a paginação.
6. Na aba **Notificações**, clique em **Simular falha no envio**. A chamada não é
   desfeita. Clique em **Processar notificações** para tentar novamente e consulte
   a mensagem simulada e as tentativas. O lote atua sobre todas as filas.
7. Emita outra senha, encerre a fila e confirme o cancelamento das pendências.
   Verifique o motivo na visão do usuário. Emissão, chamada e início em fila
   encerrada são bloqueados; um atendimento já iniciado pode ser finalizado.
8. Reabra a fila para novas emissões. Senhas canceladas não são reativadas.
9. Reinicie os serviços com os comandos acima e recarregue as páginas. Senhas,
   contador, histórico, mensagens e tentativas continuam no banco.

O navegador salva apenas o id da senha em `localStorage`; o estado vem da API.
Uma visão de usuário acompanha uma senha por vez. As visões **não constituem
uma fronteira de segurança**: não há login, autenticação, autorização ou gestão
de usuários. A prioridade é demonstrativa, sem verificação real de elegibilidade.

## Testes sem Python ou Node no host

### Regressões do backend

Com os serviços iniciados, crie o banco separado uma vez:

```bash
docker compose exec postgres sh -c 'createdb -U "$POSTGRES_USER" gestao_filas_teste'
docker compose run --rm --no-deps api python scripts/testar_backend.py
```

Se o banco já existir, não repita `createdb`. O runner configura a conexão com
esse banco sem imprimir credenciais. Cada classe PostgreSQL usa um schema
exclusivo e descartável. A suíte cobre concorrência entre chamadas/pools, FIFO,
prioridade, contadores, virada, rollback, falha de envio, idempotência, migrações
e reinício real do processo Uvicorn. Nenhum teste existente foi removido.

Para executar somente as regressões rápidas sem banco:

```bash
docker compose run --rm --no-deps -e PERSISTENCIA=memoria api python -m unittest discover -s tests -v
```

Nesse comando, os cenários PostgreSQL são marcados como ignorados.

### Teste ponta a ponta da entrega e persistência

O teste cria dados fictícios e processa notificações; use a instância acadêmica.
Ele verifica o frontend compilado, as rotas React, o proxy e o fluxo REST completo:

```bash
docker compose exec api python scripts/verificar_api.py --registrar /tmp/verificacao-entrega.json
```

Para conferir os dados após remover e recriar os containers, preservando o volume:

```bash
docker compose cp api:/tmp/verificacao-entrega.json ./verificacao-entrega.json
docker compose down
docker compose up --build -d --wait
docker compose cp ./verificacao-entrega.json api:/tmp/verificacao-entrega.json
docker compose exec api python scripts/verificar_api.py --conferir /tmp/verificacao-entrega.json
```

A comparação inclui senhas, números, contador da fila, histórico, eventos,
tentativas e mensagens simuladas. O JSON é somente um registro esperado do teste;
a aplicação continua usando PostgreSQL como fonte oficial.

### Navegador e ASR02

Os sete testes Playwright podem apontar ao Nginx existente com `E2E_BASE_URL`.
São opcionais para executar a aplicação e exigem Node/Chromium apenas no ambiente
de desenvolvimento/testes. Instruções em [frontend/README.md](frontend/README.md).

Resultados, condições, medição básica com 50 clientes/10 mil senhas e comandos
para reprodução estão em [docs/validacao.md](docs/validacao.md). A medição é
exploratória; **a meta do ASR02 não foi atingida no cenário medido**, pois consulta
e chamada ultrapassaram o p95 de 500 ms. Os resultados não são uma certificação
de capacidade do ambiente Docker ou do hardware da apresentação.

## Desenvolvimento local opcional

O caminho de entrega é o Compose completo. Para alterar a interface com hot reload,
use a API do Compose e as instruções do [frontend](frontend/README.md). Seu proxy
Vite também usa `/api`, com destino configurável em `frontend/.env`.

Para trabalhar somente com o backend, instale Python 3.11+ em um ambiente virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
PERSISTENCIA=memoria uvicorn gestao_filas.api:app --reload
```

A execução em memória perde os dados ao reiniciar. Para PostgreSQL local, exporte
`PERSISTENCIA=postgres` e `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`,
`POSTGRES_USER`, `POSTGRES_PASSWORD` conforme `.env.example`; alternativamente,
`DATABASE_URL` tem precedência no modo local. Execute `alembic upgrade head` antes
do Uvicorn. O shell deve exportar essas variáveis; o Python não carrega `.env`
automaticamente. No Compose, essa configuração já está pronta.

## Simplificações e limites acadêmicos

- Notificações são simuladas e processadas manualmente, sem serviço pago,
  agendamento automático ou política de backoff. Uma reserva interrompida pode
  ser retomada após 30 segundos; não se promete entrega exatamente uma vez.
- A fila ativa mantém um array e carrega as senhas da fila. Histórico e
  notificações têm paginação. O bloqueio por fila limita a concorrência dessa fila;
  consulte a medição antes de afirmar atendimento à meta de desempenho.
- Dados de atendimento ficam associados à senha; não há CRUD de guichês,
  cadastro de usuários, autenticação, validação real de prioridade ou totem físico.
- Não há integração com API de horários, frontend em nuvem, HTTPS, backups
  automatizados, múltiplas réplicas da API ou migrações concorrentes entre réplicas.
- O frontend usa polling, que pode ser adiado quando o navegador suspende a aba.
  As credenciais incluídas são públicas e servem apenas à demonstração local.
- O build usa `package-lock.json`; as imagens e faixas das dependências Python
  ainda podem receber atualizações. A auditoria transitiva das ferramentas do
  frontend e a limitação de validação Docker deste ambiente estão registradas
  na documentação de validação.

## Documentação

- [Requisitos e ASRs](docs/requisites.md)
- [Componentes implementados, princípios e trade-offs](docs/componentes.md)
- [Endpoints e contratos HTTP](docs/api.md)
- [Validação e desempenho](docs/validacao.md)
- [Frontend e testes de navegador](frontend/README.md)
- [ADR-001 — Stack](docs/adr/ADR-001-escolha-da-stack-do-backend.md)
- [ADR-002 — Monólito modular e características hexagonais](docs/adr/ADR-002-monolito-modular-hexagonal-eventos.md)
- [ADR-003 — PostgreSQL e persistência](docs/adr/ADR-003-postgresql-persistencia.md)
- [ADR-004 — Notificações](docs/adr/ADR-004-notificacoes.md)
