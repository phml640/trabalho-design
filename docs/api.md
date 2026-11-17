# API do protótipo

Base local: `http://localhost:8000`. O contrato OpenAPI atualizado está em
`/openapi.json` e a documentação interativa em `/docs`.

O protótipo não possui autenticação ou autorização. As visões de usuário e
administrador/atendente orientam a apresentação e **não constituem uma fronteira
de segurança**. Todos os endpoints estão acessíveis ao cliente local. Use apenas
identificadores fictícios na demonstração. A prioridade é demonstrativa: a
elegibilidade real não é verificada.

## Endpoints

| Método | Caminho | Operação e corpo |
| --- | --- | --- |
| GET | `/health` | Verifica se o processo HTTP responde. |
| GET | `/filas` | Lista filas; `?abertas=true` restringe às abertas. |
| POST | `/filas` | Cria fila: `{"nome":"Caixa","descricao":"Atendimento"}`; retorna 201. |
| GET | `/filas/{fila_id}` | Consulta dados, estado, dia e contador da fila. |
| POST | `/filas/{fila_id}/encerramento` | Encerra e cancela pendências; sem corpo. |
| POST | `/filas/{fila_id}/reabertura` | Reabre sem reativar senhas canceladas; sem corpo. |
| POST | `/filas/{fila_id}/senhas` | Emite: `{"usuario_id":"demo","tipo":"normal","canal":"totem"}`; retorna 201. |
| GET | `/filas/{fila_id}/senhas` | Lista senhas ativas do dia corrente. |
| GET | `/senhas/{senha_id}` | Consulta individual, incluindo finalizadas e canceladas. |
| POST | `/filas/{fila_id}/senhas/chamada` | Chama próxima: `{"atendente_id":"a1","guiche_id":"g1"}`. |
| POST | `/senhas/{senha_id}/atendimento/inicio` | Inicia uma senha chamada; sem corpo. |
| POST | `/senhas/{senha_id}/atendimento/finalizacao` | Finaliza atendimento em andamento; sem corpo. |
| GET | `/filas/{fila_id}/historico` | Histórico paginado, incluindo dias anteriores. |
| GET | `/notificacoes` | Eventos da Outbox e situação de processamento, paginados. |
| POST | `/notificacoes/processamento` | Processa um lote: `{"limite":20,"simular_falha":false}`; corpo opcional. |
| GET | `/notificacoes/simuladas` | Mensagens registradas pelo Fake, paginadas. |
| GET | `/notificacoes/{evento_id}/tentativas` | Tentativas de um evento, paginadas. |

Exceto as criações, operações bem-sucedidas retornam 200. Os identificadores de
fila, senha e evento são UUIDs. Para emitir, `usuario_id` é obrigatório; `tipo`
aceita `normal` (padrão) ou `prioritaria`, e `canal` aceita `online` (padrão) ou
`totem`. Nome, identificação de usuário, atendente e guichê não podem ser vazios.

## Senha e atendimento

O ciclo permitido é `aguardando → chamada → em_atendimento → finalizada`.
Uma fila encerrada bloqueia emissão, chamada e início de atendimento. Consultas
continuam disponíveis e um atendimento já iniciado pode ser finalizado, inclusive
após encerramento ou meia-noite. Encerramento e virada diária cancelam apenas
senhas aguardando ou chamadas, com histórico e motivo registrados.

A consulta individual executa a virada diária pendente da fila antes de responder.
Senhas finalizadas ou canceladas permanecem consultáveis pelo id, mas saem da
lista ativa. A fila ativa e a numeração diária seguem `America/Sao_Paulo`.

As respostas de emissão e consulta de senha contêm `id`, `fila_id`, `numero`,
`tipo`, `estado`, `emitida_em`, `dia_operacional`, `canal`, `guiche_id`,
`chamada_em`, `atendimento_iniciado_em`, `atendimento_finalizado_em` e
`motivo_cancelamento`. O identificador do usuário é omitido. Chamada e transições
de atendimento retornam esses campos e `atendente_id`. A API preserva esse dado
operacional no histórico, sem incluí-lo nas respostas públicas de consulta.

Os horários incluem referência de fuso; dados relidos do PostgreSQL usam UTC.
Cada transição válida grava o histórico na mesma transação. Transições inválidas
retornam 409 e não acrescentam registros nem alteram o estado.

## Histórico e paginação

Histórico, Outbox, mensagens simuladas e tentativas recebem `limite` entre 1 e 100
(padrão 20) e `offset` não negativo (padrão 0). O retorno tem o formato:

```json
{"itens": [], "limite": 20, "offset": 0, "tem_mais": false}
```

Para avançar, some o limite ao offset enquanto `tem_mais` for verdadeiro.
O histórico segue a ordem de registro das transições, e tentativas seguem seu
número. Outbox segue a ordem de registro dos eventos; mensagens simuladas seguem
o horário de registro e o id do evento para desempate. Listas de filas e de
senhas ativas mantêm seu formato de array.

O histórico permite filtrar por `senha_id` e por `estado`: `aguardando`, `chamada`,
`em_atendimento`, `finalizada` ou `cancelada`. Esse filtro seleciona a transição
registrada, não o estado atual da senha. Exemplos:

```text
GET /filas/{fila_id}/historico?estado=finalizada&limite=20
GET /filas/{fila_id}/historico?estado=cancelada
GET /filas/{fila_id}/historico?senha_id={senha_id}&limite=2&offset=0
```

Cada registro contém `id`, `senha_id`, `fila_id`, `estado_anterior`, `estado`,
`quando`, `atendente_id`, `guiche_id` e `motivo`. O motivo de cancelamento é
`encerramento_diario` ou `encerramento_administrativo`. Nenhum histórico é apagado
na virada ou no encerramento da fila.

## Notificações e demonstração de falha

A chamada registra `SenhaChamada` atomicamente na Outbox. Sua resposta confirma
a solicitação de notificação; o processamento é feito posteriormente por um POST
separado. Não é preciso iniciar outro serviço.

`GET /notificacoes` retorna, para cada item, `evento` (`id`, `fila_id`, `senha_id`,
`chamada_em`), `tentativas`, `processado_em`, `ultimo_erro`, `reservado_ate` e
`status` (`pendente`, `em_processamento`, `falha` ou `processada`).
Essa consulta e `/notificacoes/simuladas` aceitam filtros `fila_id` e `senha_id`.

Para simular indisponibilidade do provedor:

```http
POST /notificacoes/processamento
Content-Type: application/json

{"limite":20,"simular_falha":true}
```

Havendo um evento pendente, o resultado será:

```json
{"processadas":1,"sucessos":0,"falhas":1}
```

O HTTP 200 informa que o lote foi executado. A falha de envio está no resultado
e no registro persistido, e não desfaz a chamada. O modo `simular_falha` usa um
adaptador de falha apenas para esse lote. Para tentar novamente, repita o POST
com `{}` ou `{"simular_falha":false}`. Eventos já processados são ignorados.

Em `/notificacoes/{evento_id}/tentativas`, cada item contém `id`, `evento_id`,
`numero`, `iniciada_em`, `finalizada_em` e `erro`. O erro é nulo no sucesso; uma
tentativa em andamento ainda não tem horário final. Se uma reserva expirar, a
tentativa anterior termina com `reserva_expirada` na próxima execução.

`/notificacoes/simuladas` permite inspecionar `evento_id`, `senha_id`, `fila_id`,
`mensagem` e `criada_em`. A mensagem contém apenas número da senha e guichê.
O Fake persiste uma única mensagem por evento, sem envio ao celular. Reservas,
tentativas, mensagens e resultados sobrevivem a reinícios quando PostgreSQL é usado.

O envio é posterior ao commit e ocorre sem transação aberta. Não há agendamento
automático, backoff ou promessa de entrega exatamente uma vez. Um processo
interrompido deixa uma reserva de até 30 segundos; outra execução pode retomá-la.
O id do evento é a chave estável de idempotência para qualquer futuro adaptador.

## Erros

| Código | Situação |
| --- | --- |
| 404 | Fila, senha ou evento não encontrado; também quando não há senha aguardando para chamar. |
| 409 | Nome de fila duplicado, fila encerrada para a operação solicitada ou transição de estado inválida. |
| 422 | UUID, corpo, filtro ou parâmetros de paginação inválidos. |

Erros de negócio retornam `{"detail":"mensagem"}`. Erros de validação do
FastAPI retornam uma lista em `detail`, indicando campos inválidos. Os modelos
de resposta e os códigos estão declarados no OpenAPI.
