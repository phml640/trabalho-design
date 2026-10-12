# Requisitos iniciais — Gestão de filas presenciais

## Contexto e escopo

O sistema organiza senhas e atendimentos presenciais em uma unidade de atendimento. Uma pessoa solicita uma senha, aguarda a chamada, é atendida em um guichê e o atendimento fica registrado.

## Atores

| Ator | Responsabilidade |
| --- | --- |
| Usuário | Solicita senha e aguarda atendimento. |
| Atendente | Chama a próxima senha e registra o atendimento. |
| Administrador | Configura filas, guichês e regras de prioridade. |
| Painel de chamadas | Recebe a informação de cada chamada para exibição. |

## Requisitos funcionais

| ID | Requisito |
| --- | --- |
| RF01 | Emitir uma senha vinculada a uma fila de atendimento. |
| RF02 | Classificar a senha emitida como normal ou prioritária. |
| RF03 | Consultar as senhas que aguardam atendimento em uma fila. |
| RF04 | Selecionar a próxima senha segundo a política de prioridade vigente. |
| RF05 | Permitir que um atendente chame a próxima senha para um guichê. |
| RF06 | Iniciar e finalizar um atendimento associado a uma senha chamada. |
| RF07 | Registrar e consultar o histórico dos atendimentos realizados. |
| RF08 | Notificar o painel de chamadas quando uma senha for chamada. |