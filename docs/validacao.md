# Validação da entrega

## Condições e limites da verificação

Verificação realizada em 17/11/2026, no fuso `America/Sao_Paulo`. O Docker CLI e
Compose estão disponíveis, mas o daemon retorna `permission denied` no socket
`/var/run/docker.sock`, inclusive fora do sandbox de execução de comandos.
Portanto, **build das imagens, subida do Compose e recriação dos containers não
foram executados neste ambiente**. Essa pendência deve ser conferida em uma
máquina com acesso ao daemon antes da apresentação.

Para validar o comportamento sem ocultar essa restrição, foram usados processos
temporários separados: PostgreSQL 17.12, Uvicorn com um processo e Nginx 1.26.3,
com o build Vite servido como arquivos estáticos. A configuração Nginx da entrega
foi reaproveitada, adaptando somente portas, endereço do upstream e caminho do
build ao ambiente temporário. A imagem declarada no Dockerfile usa Nginx 1.30;
isso não foi verificado como imagem em execução.

O código Python local foi executado em Python 3.13.5; o Dockerfile usa 3.12.
O frontend foi compilado com Node 24.22.3. Os bancos de regressão, entrega e carga
foram separados, sem usar dados reais de atendimento.

## Resultados funcionais

| Verificação | Resultado observado |
| --- | --- |
| `docker compose config --quiet`, sem `.env` | Passou: três serviços, padrões demonstrativos e volume nomeado. |
| `docker compose --env-file .env.example config --quiet` | Passou. |
| Build frontend (`tsc --noEmit` + Vite) | Passou. |
| `nginx -t` da configuração adaptada ao ambiente nativo | Passou. |
| Rotas `/`, `/usuario`, `/admin`, assets e proxy `/api` no Nginx real | Passaram. |
| Suíte Python com PostgreSQL real | 55 testes passaram, incluindo concorrência, bloqueios independentes, rollback, numeração, histórico, falha do notificador e migrações. |
| Playwright no frontend compilado servido pelo Nginx | 7 testes passaram, incluindo duas janelas, atendimento completo, prioridade, cancelamento, retentativa e layout móvel. |
| `scripts/verificar_api.py` pelo proxy Nginx | Passou: criar, emitir normal/prioritária, consultar, chamar, atender, histórico, eventos, falha/retentativa e encerramento com HTTP 409. |
| Comparação do registro após reiniciar Nginx, API e PostgreSQL nativos | Passou: todas as respostas registradas permaneceram iguais; migrações reaplicadas sem alteração de dados. |
| Swagger na API e asset inexistente no Nginx | HTTP 200 para `/docs`; HTTP 404 para um asset inexistente, sem retornar o HTML da SPA. |

O teste de persistência da entrega salva respostas oficiais, reinicia os processos
e o PostgreSQL e compara os dados depois. O roteiro abaixo permite repetir a mesma
comparação também após **recriar containers**, preservando o volume nomeado.
O reinício nativo passou, mas não equivale a validar o ciclo Docker neste ambiente.

### Reproduzir a verificação Docker do zero

Na raiz de um clone, em ambiente de demonstração:

```bash
docker compose up --build -d --wait
docker compose ps
docker compose exec api python scripts/verificar_api.py --registrar /tmp/verificacao-entrega.json
docker compose cp api:/tmp/verificacao-entrega.json ./verificacao-entrega.json
docker compose down
docker compose up --build -d --wait
docker compose cp ./verificacao-entrega.json api:/tmp/verificacao-entrega.json
docker compose exec api python scripts/verificar_api.py --conferir /tmp/verificacao-entrega.json
```

Não use `down -v` entre o registro e a conferência: esse comando apaga os dados que
o teste está tentando preservar. O script cria uma fila exclusiva, mas o lote de
notificações é global; execute em instância acadêmica/descartável.

As respostas comparadas incluem o estado da fila, contador prioritário, números e
estados das senhas, histórico, eventos, tentativas e mensagens simuladas. A suíte
PostgreSQL existente também verifica continuidade da numeração após reiniciar a API.

## Medição exploratória do ASR02

O requisito estabelece p95 de até 500 ms para emissão, consulta e chamada com
50 clientes concorrentes e 10 mil senhas armazenadas. Foi realizada uma medição
básica, sem carga sustentada nem repetições suficientes para uma conclusão geral.

Condições registradas em [resultados/asr02-basico.json](resultados/asr02-basico.json):

- Execução nativa temporária, **sem Docker**, em Debian 13/Linux, 8 CPUs visíveis.
- PostgreSQL 17.12 local, FastAPI 0.143.0, SQLAlchemy 2.0.58 e um processo Uvicorn.
- Cliente Python e servidor na mesma máquina, por HTTP loopback direto à API.
- Banco inicialmente com exatamente 10 mil senhas, em uma fila; todas aguardando,
  metade normais e metade prioritárias. A preparação em lote fica fora da medição.
- Uma consulta de aquecimento e uma rajada de 50 requisições por operação, na ordem
  emissão, consulta e chamada. As emissões elevam o total para 10.050 nas fases
  seguintes. A duração inclui HTTP, transferência e leitura do JSON pelo cliente.
- O frontend e os testes funcionais estavam sem carga durante as rajadas. O envio
  de notificações não foi processado, conforme o limite do ASR02.

| Operação | Requisições | Erros | p50 | p95 | Máximo |
| --- | --- | --- | --- | --- | --- |
| Emissão | 50 | 0 | 191,64 ms | 298,61 ms | 308,28 ms |
| Consulta da fila ativa | 50 | 0 | 7.680,16 ms | 14.683,49 ms | 15.870,22 ms |
| Chamada | 50 | 0 | 6.723,44 ms | 12.494,94 ms | 13.440,71 ms |

**A meta não foi atingida neste cenário**, embora as 150 requisições tenham
terminado sem erros. A consulta devolve um array grande e a chamada materializa
as senhas da fila; o bloqueio dessa fila serializa as operações. Esses custos são
compatíveis com o gargalo observado, mas não foram isolados com profiling.

A emissão ficou abaixo de 500 ms nessa rajada; isso não demonstra atendimento ao
ASR02 completo. O teste não representa várias filas, volume de produção, rede
remota ou o hardware final da apresentação. As próximas melhorias possíveis são
reduzir os dados carregados e paginar a fila ativa, medindo novamente e preservando
o contrato de seleção e a atomicidade. Nenhuma otimização extensa foi introduzida
para melhorar artificialmente o resultado desta entrega.

### Reproduzir a medição em Docker

Use outro projeto Compose e portas para manter a carga separada da demonstração:

```bash
API_PORT=18002 FRONTEND_PORT=18082 POSTGRES_PORT=55433 docker compose -p carga up --build -d --wait
docker compose -p carga exec api python scripts/medir_asr02.py --base-url http://127.0.0.1:8000 --ambiente "Compose local; registrar CPU, memoria e versoes da maquina de teste" --saida /tmp/asr02.json
docker compose -p carga cp api:/tmp/asr02.json ./asr02.json
docker compose -p carga down -v
```

O último comando remove apenas o volume do projeto `carga`. Cada execução do
script acrescenta uma fila e 10 mil senhas; comece com um volume vazio para repetir
a condição inicial. Registre a máquina, condições e versões antes de comparar
com os números nativos acima. O benchmark não roda na subida normal da aplicação.

## Dependências e pendências reais

O frontend conserva o lockfile. Na etapa de frontend, `npm audit --omit=dev`
retornou zero vulnerabilidades; a auditoria completa apontou um alerta transitivo
em `picomatch`, utilizado pelas ferramentas Vite, sem versão corrigida disponível
na linha consultada. Essa limitação está no README do frontend e deve ser revista
ao atualizar as ferramentas. A imagem Nginx final contém apenas o build, sem npm
ou dependências de desenvolvimento.

Permanecem pendentes a execução das imagens/Compose em um daemon acessível e a
validação de desempenho no hardware da demonstração. Não há afirmação de que a
meta ASR02 tenha sido cumprida, nem garantia de entrega real de notificações.

Referências de configuração: [ordem de inicialização do Compose](https://docs.docker.com/compose/how-tos/startup-order/)
e [proxy HTTP do Nginx](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass).
