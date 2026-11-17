# Gestão de filas e atendimento presencial

Trabalho da disciplina de Design de Software. Backend Python/FastAPI organizado
nos módulos `gestao_filas`, `gestao_senhas` e `gestao_compartilhada`.
O frontend React/Vite/TypeScript está em [`frontend/`](frontend/), com as visões
`/usuario` e `/admin` e o fluxo completo de atendimento integrado à API.

## Executar com Docker e PostgreSQL

Requer Docker Engine e Docker Compose v2.

```bash
cp .env.example .env
# Edite POSTGRES_PASSWORD em .env e escolha uma senha local.
docker compose up --build -d --wait
docker compose ps
```

A API usa PostgreSQL por padrão no Compose. O banco precisa estar saudável antes
de a API iniciar; o container da API executa `alembic upgrade head` antes do
Uvicorn. A primeira execução baixa as imagens e instala as dependências.

- API: <http://localhost:8000>
- Documentação interativa: <http://localhost:8000/docs>
- Verificação do processo HTTP: <http://localhost:8000/health>

```bash
docker compose logs -f api
docker compose restart api
docker compose down
```

O volume `postgres_data` mantém os dados após reinícios da API, do banco e após
`docker compose down`. `docker compose down -v` apaga esse volume e os dados.
As portas são publicadas apenas em `127.0.0.1`. `API_PORT` e `POSTGRES_PORT` em
`.env` permitem alterar as portas locais.

## Executar o frontend

Com a API e o PostgreSQL iniciados, abra outro terminal. Requer Node.js 24 LTS
(ou 22.12+ na linha 22) e npm:

```bash
cd frontend
npm ci
cp .env.example .env
npm run dev
```

Abra <http://localhost:5173>. A página inicial permite escolher a visão. Para
demonstrar em duas janelas, abra `/usuario` em uma e `/admin` na outra. O proxy do
Vite encaminha `/api` ao backend em `http://127.0.0.1:8000`; ajuste
`VITE_API_PROXY_TARGET` em `frontend/.env` se a API usar outra porta. Não é
necessário alterar CORS no backend para usar esse proxy.

O administrador cria a fila e informa atendente e guichê. O usuário seleciona
essa fila e emite uma senha. O administrador chama, inicia e finaliza o atendimento;
a janela do usuário acompanha as mudanças automaticamente a cada três segundos.
Histórico e notificações simuladas podem ser consultados no painel. No celular,
a senha emitida é trazida para a área visível automaticamente.

O navegador conserva somente o identificador da senha no `localStorage`. Número,
estado, fila e histórico são consultados na API; PostgreSQL continua sendo a
fonte oficial. Não há login ou controle de acesso entre as visões, e a prioridade
continua demonstrativa, sem validação de elegibilidade.

Para verificar o build ou visualizar a versão compilada:

```bash
npm run build
npm run preview
```

O preview fica em <http://localhost:4173> e também usa o proxy local. Instruções de
configuração, testes de navegador e roteiro de demonstração estão no
[README do frontend](frontend/README.md).

## Executar sem Docker

Requer Python 3.11 ou superior.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Para testes rápidos, o padrão fora do Docker continua sendo memória:

```bash
PERSISTENCIA=memoria uvicorn gestao_filas.api:app --reload
```

Esse adaptador funciona em um único processo e perde os dados ao reiniciar.
Para usar PostgreSQL, inicie um banco local ou apenas o serviço do Compose:

```bash
cp .env.example .env  # Se ainda não existir; edite a senha antes de continuar.
docker compose up -d --wait postgres
set -a
source .env
set +a
alembic upgrade head
uvicorn gestao_filas.api:app --reload --port "${API_PORT:-8000}"
```

O arquivo `.env` é carregado automaticamente pelo Compose. Na execução local,
o shell precisa exportar as variáveis como no exemplo acima.

| Variável | Uso |
| --- | --- |
| `PERSISTENCIA` | `memoria` ou `postgres`; padrão local `memoria`, Compose `postgres`. |
| `POSTGRES_HOST` | Host do banco; padrão local `localhost`, Compose `postgres`. |
| `POSTGRES_PORT` | Porta do banco; padrão `5432`. No Compose altera a porta publicada, mantendo `5432` entre os containers. |
| `POSTGRES_DB` | Nome do banco; padrão `gestao_filas`. |
| `POSTGRES_USER` | Usuário do banco; padrão `gestao`. |
| `POSTGRES_PASSWORD` | Senha local; obrigatória se não houver `DATABASE_URL`. |
| `DATABASE_URL` | Opcional na execução local; tem precedência sobre `POSTGRES_*`. Aceita `postgresql://` e `postgresql+psycopg://`. |
| `API_PORT` | Porta HTTP publicada pelo Compose; padrão `8000`. |
| `TEST_DATABASE_URL` | Banco separado para os testes PostgreSQL. |

Senhas com caracteres especiais não precisam de escape quando fornecidas por
`POSTGRES_PASSWORD`; em uma URL, devem ser codificadas conforme o formato de URL.
O Compose configura a conexão pelos campos `POSTGRES_*` de `.env`.

## Migrações

Com as variáveis de conexão exportadas e o banco disponível:

```bash
alembic upgrade head
alembic current
alembic check
```

A revisão inicial `0001` cria o esquema completo e pode ser aplicada a um banco
vazio. Repetir `upgrade head` não recria tabelas nem apaga dados. Para evoluir o
esquema, altere os modelos de infraestrutura, gere uma nova revisão com
`alembic revision --autogenerate -m "descricao"` e revise o SQL antes de aplicá-la.
Os testes verificam também o ciclo de downgrade/upgrade em esquema descartável.
A revisão incremental `0002` acrescenta tentativas, notificações simuladas e a
reserva temporária da Outbox. Execute `alembic upgrade head` também em bancos já
criados na etapa anterior. No Docker, reconstrua a API com o comando inicial.

## Integração e persistência

Os dois gerenciadores recebem a mesma porta `UnidadeDeTrabalho`, definida em
`gestao_compartilhada.application`. A API faz essa composição em `criar_app()`;
testes também podem injetar explicitamente qualquer adaptador.

O adaptador `gestao_compartilhada.postgres.UnidadeDeTrabalhoPostgres` usa uma
Session por transação, com isolamento `READ COMMITTED`. Toda operação de uma
fila bloqueia sua linha com `SELECT ... FOR UPDATE` antes de ler as entidades.
Isso serializa emissão, chamada, atendimento e virada da mesma fila, inclusive
entre processos da API. Filas diferentes têm bloqueios independentes. Operações
globais usam um advisory lock transacional para proteger a verificação e criação
de nomes, preservando a comparação `casefold()` existente.

Estado, contador de prioridade, numeração, histórico e evento são confirmados
juntos. Qualquer exceção reverte a transação; números de senha não são consumidos
em emissões revertidas. As entidades retornadas são objetos de domínio separados
do ORM. Os repositórios PostgreSQL só podem ser usados dentro de seu contexto
transacional; após a saída, a Session fica encerrada.

| Tabela | Conteúdo |
| --- | --- |
| `filas` | Estado, dia operacional, nome único normalizado e contador de chamadas prioritárias. |
| `senhas` | Emissão, usuário, classe, estado e dados de atendimento (atendente, guichê e horários), como no domínio atual. |
| `contadores_senhas` | Numeração transacional por fila, dia e classe. |
| `historico_transicoes` | Transições com identificador estável, estado anterior/novo, horário e motivo. |
| `outbox` | Eventos `SenhaChamada` com identificador estável e campos para tentativas, erro e processamento posterior. |
| `tentativas_notificacao` | Cada tentativa, com início, fim e erro quando houver. |
| `notificacoes_simuladas` | Mensagens registradas pelo `FakeNotificador`, únicas por evento. |

Chaves estrangeiras preservam a associação entre fila, senha, histórico e evento.
Uma restrição única protege a numeração por fila/dia/classe. Há índices para
seleção de senhas, histórico e eventos pendentes. Horários usam `timestamptz` e
conexões em UTC; o dia operacional continua calculado em `America/Sao_Paulo`.
Os dados de atendimento permanecem na senha para preservar o modelo existente.

## Contrato para o frontend

Todos os endpoints, corpos, respostas e filtros estão descritos em
[docs/api.md](docs/api.md) e no OpenAPI em `/docs`. O fluxo completo está disponível:
criar fila, emitir, consultar, chamar, iniciar e finalizar atendimento e consultar
histórico. Histórico e notificações usam `limite` (1–100, padrão 20), `offset` e
`tem_mais`. A lista de senhas ativas conserva o formato de lista já existente.

As visões de usuário e administrador/atendente são convenções de apresentação,
**não constituem uma fronteira de segurança**. Não há autenticação ou autorização;
qualquer cliente local pode chamar os endpoints administrativos. A emissão aceita
um identificador simbólico de usuário; as respostas públicas de senha não expõem
esse identificador nem o identificador do atendente. Não forneça dados pessoais
reais na demonstração. A classificação prioritária é escolhida para demonstrar
a política de chamada; **a elegibilidade real não é verificada pelo protótipo**.

## Demonstração pela API

Crie uma fila em `POST /filas`, copie seu `id` e use-o nas operações de senha:

```bash
curl -X POST http://localhost:8000/filas \
  -H 'Content-Type: application/json' -d '{"nome":"Caixa"}'

# Substitua pelo id devolvido na criação.
FILA_ID=COLE_O_ID_AQUI
curl -X POST "http://localhost:8000/filas/$FILA_ID/senhas" \
  -H 'Content-Type: application/json' -d '{"usuario_id":"usuario-demo","tipo":"normal","canal":"totem"}'
curl -X POST "http://localhost:8000/filas/$FILA_ID/senhas" \
  -H 'Content-Type: application/json' -d '{"usuario_id":"demo-p1","tipo":"prioritaria"}'
curl -X POST "http://localhost:8000/filas/$FILA_ID/senhas" \
  -H 'Content-Type: application/json' -d '{"usuario_id":"demo-p2","tipo":"prioritaria"}'
# As três chamadas devem retornar P001, P002 e N001, nessa ordem.
for CHAMADA in 1 2 3; do
  curl -X POST "http://localhost:8000/filas/$FILA_ID/senhas/chamada" \
    -H 'Content-Type: application/json' -d '{"atendente_id":"a1","guiche_id":"g1"}'
done

# Copie o id de uma senha chamada.
SENHA_ID=COLE_O_ID_AQUI
curl -X POST "http://localhost:8000/senhas/$SENHA_ID/atendimento/inicio"
curl -X POST "http://localhost:8000/senhas/$SENHA_ID/atendimento/finalizacao"
curl "http://localhost:8000/senhas/$SENHA_ID"
curl "http://localhost:8000/filas/$FILA_ID/historico?limite=20&offset=0"

# A falha fica registrada, preservando as chamadas já confirmadas.
curl -X POST http://localhost:8000/notificacoes/processamento \
  -H 'Content-Type: application/json' -d '{"simular_falha":true}'
curl "http://localhost:8000/notificacoes?fila_id=$FILA_ID"
# Uma nova execução tenta novamente os eventos que falharam.
curl -X POST http://localhost:8000/notificacoes/processamento \
  -H 'Content-Type: application/json' -d '{}'
curl "http://localhost:8000/notificacoes/simuladas?fila_id=$FILA_ID"
docker compose restart api
# Após a API voltar, consulte novamente senha, histórico e notificações.
```

Aguarde a API voltar a responder após o reinício. Estados, histórico, tentativas e
mensagens simuladas continuam armazenados. Pela documentação interativa, também
é possível listar, encerrar e
reabrir filas. Filas inexistentes retornam 404, filas encerradas retornam 409 e
entradas inválidas retornam 422.

A política continua sendo de no máximo duas prioritárias consecutivas quando há
normais aguardando, com FIFO por horário e id dentro da classe. Encerrar uma fila
cancela suas senhas aguardando ou chamadas, preservando atendimentos em andamento.
A primeira operação pertinente após a virada diária cancela pendências antigas,
preserva o histórico e reinicia os contadores do novo dia.

## Notificações simuladas

`Notificador`, definido em `gestao_compartilhada.notificacoes`, é a porta
substituível de envio. A composição padrão usa `FakeNotificador`; outro adaptador
pode ser injetado em `criar_app(uow, notificador=adaptador)` sem mudar os casos de
uso. Nenhuma mensagem real é enviada e nenhum contato pessoal é necessário.

`POST /notificacoes/processamento` processa manualmente um lote pendente, depois
do commit da chamada. Primeiro persiste a reserva e o início da tentativa; depois
chama o notificador **sem uma transação aberta**; por fim grava sucesso ou falha
em nova transação. A chamada da senha nunca é revertida por falha de envio.
O retorno HTTP 200 informa quantas tentativas tiveram sucesso ou falha no lote.

Falhas ficam disponíveis para a próxima execução. Se o processo for interrompido,
a reserva expira em 30 segundos; a próxima execução registra `reserva_expirada`
na tentativa anterior e tenta de novo. O id do evento permanece estável. O Fake
registra uma única mensagem por evento, inclusive se houver reenvio após perda de
confirmação. Um provedor real precisaria respeitar essa chave para evitar mensagens
duplicadas; a integração tem semântica de pelo menos uma tentativa.

Use `/notificacoes` para verificar pendências e resultados,
`/notificacoes/{evento_id}/tentativas` para consultar cada tentativa e
`/notificacoes/simuladas` para inspecionar as mensagens. Nenhum processador
automático ou serviço adicional é necessário para a demonstração.

## Testes

Regressões rápidas em memória, sem banco:

```bash
PERSISTENCIA=memoria python -m unittest discover -s tests -v
```

Sem `TEST_DATABASE_URL`, os testes PostgreSQL são marcados como ignorados.
Para executar todos os testes, crie um banco separado (com o Compose iniciado):

```bash
docker compose exec postgres sh -c 'createdb -U "$POSTGRES_USER" gestao_filas_teste'
set -a
source .env
set +a
# Defina a URL do banco de teste com sua senha local; codifique caracteres especiais.
export TEST_DATABASE_URL='postgresql+psycopg://gestao:SENHA@localhost:5432/gestao_filas_teste'
PERSISTENCIA=memoria python -m unittest discover -s tests -v
```

Adapte usuário, porta e senha da URL à sua configuração. O usuário do banco de
teste precisa poder criar e remover schemas. Cada classe cria um schema exclusivo,
aplica migrações reais e remove apenas esse schema ao terminar. As tabelas são
limpas entre cenários; use um banco de teste separado.

Os testes incluem as regressões existentes de prioridade, FIFO, concorrência,
virada, encerramento e rollback no adaptador real. Verificam também falhas de
integridade após gravações SQL, independência dos bloqueios entre filas, chamadas
em pools independentes, migrações reproduzíveis e reinício de um processo Uvicorn
com preservação de senhas, contadores, histórico e Outbox.
Também verificam o fluxo HTTP completo, filtros e paginação, transições inválidas,
falha e retentativa do notificador, idempotência, recuperação de reservas e
persistência das mensagens simuladas e dos atendimentos após reiniciar a API.

## Limites desta etapa

O envio é simulado e o processamento é manual, sem agendamento ou política de
backoff. Autenticação permanece fora deste escopo. A consulta da fila ativa
ainda carrega as senhas da fila; a meta de carga do ASR02 não foi medida.
O Compose inicial usa uma instância da API e executa as migrações na inicialização.

## Documentação

- [Requisitos e regras de negócio](docs/requisites.md)
- [ADR-001 — Stack inicial do backend](docs/adr/ADR-001-escolha-da-stack-do-backend.md)
- [ADR-002 — Monólito modular, Arquitetura Hexagonal e eventos internos](docs/adr/ADR-002-monolito-modular-hexagonal-eventos.md)
- [ADR-003 — PostgreSQL e estratégia de persistência](docs/adr/ADR-003-postgresql-persistencia.md)
- [ADR-004 — Notificações após a chamada](docs/adr/ADR-004-notificacoes.md)
- [Transações no SQLAlchemy](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)
- [Bloqueios no PostgreSQL](https://www.postgresql.org/docs/17/explicit-locking.html)
