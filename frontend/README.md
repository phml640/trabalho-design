# Frontend · Em fila

Interface local em React, Vite e TypeScript para demonstrar o backend existente.
Usa CSS próprio, sem biblioteca de componentes, gerenciador global de estado ou
WebSockets. Não há dados de fila fictícios nem seleção de prioridade no cliente:
a ordem, a virada diária e as transições continuam sob responsabilidade da API.

## Executar

Para a entrega completa, execute `docker compose up --build` na raiz do repositório.
O build React é servido por Nginx em <http://localhost:8080>, com `/usuario`,
`/admin` e proxy `/api`. Não exige Node no host. Os passos abaixo são opcionais
para desenvolvimento com hot reload.

Inicie o backend e o PostgreSQL conforme o [README principal](../README.md).
Em outro terminal, com Node.js 24 LTS (ou 22.12+ na linha 22) e npm:

```bash
cd frontend
npm ci
cp .env.example .env
npm run dev
```

- Início: <http://localhost:5173>
- Usuário: <http://localhost:5173/usuario>
- Administrador/atendente: <http://localhost:5173/admin>

Não há autenticação. Os botões apenas escolhem a visão e **não constituem uma
fronteira de segurança**. O sistema é destinado à demonstração local. A
classificação prioritária é demonstrativa e não verifica elegibilidade real.

## Configuração e organização

| Variável em `frontend/.env` | Padrão | Uso |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `/api` | Prefixo das chamadas HTTP do navegador. |
| `VITE_API_PROXY_TARGET` | `http://127.0.0.1:8000` | Destino do proxy local, usado por `dev` e `preview`. |

Reinicie o Vite ao mudar o `.env`. Variáveis `VITE_*` são públicas; não coloque
senhas, tokens ou outros segredos nelas. O proxy remove o prefixo `/api` antes de
encaminhar ao backend. Assim, não é necessário modificar CORS na API. Se usar uma
URL absoluta diretamente no navegador, será necessário configurar a origem no
servidor correspondente.

| Arquivo | Responsabilidade |
| --- | --- |
| `src/api.ts` | Chamadas HTTP tipadas, timeout, cancelamento, filtros e erros. |
| `src/types.ts` | Tipos alinhados aos contratos REST existentes. |
| `src/hooks.ts` | Atualização a cada três segundos, descarte de respostas antigas e bloqueio de cliques repetidos durante operações. |
| `src/UserPage.tsx` | Emissão, recuperação do identificador e acompanhamento da senha. |
| `src/AdminPage.tsx` | Filas, chamada e ciclo do atendimento. |
| `src/AdminPanels.tsx` | Histórico, notificações, mensagens simuladas e tentativas, com paginação. |
| `src/components.tsx` | Layout, indicadores, feedback e confirmação de encerramento. |
| `src/styles.css` | Estilos e ajustes para telas pequenas. |

O único dado salvo em `localStorage` é o id da senha, sob a chave
`em-fila:senha-id`. Os demais dados são relidos da API, sem cache persistente local.
Um identificador simbólico de usuário é gerado para cada emissão, sem solicitar
nome ou contato. Não há valores de senha, atendente ou guichê fixados na interface.
O id salvo pertence à origem do frontend: use o mesmo endereço e porta ao
recarregar. Uma visão de usuário acompanha uma senha de cada vez.

## Roteiro em duas janelas

1. Abra `/admin`, clique em **Nova fila** e cadastre uma fila.
2. Informe a identificação do **Atendente** e do **Guichê**; esses valores são
   associados pelo backend à senha chamada.
3. Em outra janela, abra `/usuario`, selecione a fila e o tipo, e clique em
   **Emitir minha senha**. O número retornado pelo backend fica em destaque.
4. No painel, clique em **Chamar próxima senha**. Em até cerca de três segundos
   após a próxima consulta, a visão do usuário exibirá a chamada e o guichê.
5. Clique em **Iniciar atendimento** e depois em **Finalizar atendimento**.
   A visão do usuário acompanha os estados. Recarregue-a para demonstrar que o
   identificador é recuperado e o estado é relido do servidor.
6. Na aba **Histórico**, consulte as transições ou filtre por `Finalizada`.
   Use os botões de paginação para consultar registros anteriores.
7. Na aba **Notificações**, clique em **Simular falha no envio**. Inspecione a
   falha e as tentativas: a chamada permanece confirmada. Em seguida, clique em
   **Processar notificações** para tentar novamente e visualizar a mensagem
   simulada. O processamento atua sobre até 20 pendências de todas as filas,
   enquanto a consulta mostra os registros da fila selecionada.
8. Emita outra senha e encerre a fila, confirmando a ação. A senha aguardando ou
   chamada será cancelada; o usuário verá o motivo. Atendimentos em andamento
   ainda podem ser finalizados. Reabra a fila para permitir novas emissões.

Para demonstrar prioridade, use janelas de usuário independentes ou outro perfil
de navegador para emitir senhas normais e prioritárias. O painel apresenta os
tipos, mas quem escolhe a próxima senha é o backend, mantendo a política de duas
prioritárias consecutivas e FIFO. Reabrir a fila não reativa senhas canceladas.

## Build e preview

```bash
npm run build
npm run preview
```

O build verifica os tipos e gera `dist/`. O preview local fica na porta 4173,
com o mesmo proxy `/api`. Um servidor de arquivos estáticos de produção precisa
configurar esse proxy separadamente e encaminhar `/usuario` e `/admin` para
`index.html`; a configuração do Vite não é incorporada ao JavaScript compilado.
Na entrega Docker isso já é feito por `nginx.conf` e pelo Dockerfile em dois
estágios. O build da imagem fixa o prefixo `/api`, sem incorporar `.env` local.

## Testes de navegador

Os testes usam a API real e criam filas e senhas. Execute-os com um banco
PostgreSQL separado e descartável: o processamento de notificações é global.
Não aponte os testes para um ambiente com dados de atendimento reais.

Prepare o banco conforme o README principal, exporte `TEST_DATABASE_URL` e inicie
a API de teste na raiz do projeto, com o ambiente Python ativado:

```bash
export DATABASE_URL="$TEST_DATABASE_URL"
alembic upgrade head
PERSISTENCIA=postgres uvicorn gestao_filas.api:app --host 127.0.0.1 --port 8000
```

Em outro terminal:

```bash
cd frontend
npm ci
npx playwright install chromium
npm run test:e2e
```

O Playwright inicia o Vite na porta 5173. A API deve estar disponível antes do
teste. Se ela usar outra porta, forneça `VITE_API_PROXY_TARGET` no ambiente do
comando; evite reaproveitar um Vite já iniciado com outro destino. Um Chrome já
instalado pode ser usado com `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`, dispensando
o download do Chromium. Capturas e traces de falhas ficam em `test-results/`.

Para testar o frontend compilado já servido pelo Nginx, sem iniciar Vite:

```bash
E2E_BASE_URL=http://localhost:8080 npm run test:e2e
```

Use uma instância descartável, pois esses testes criam filas e processam
notificações. Os testes de API que dispensam Node estão no README principal.

A suíte verifica as duas janelas com atualização automática, o ciclo completo,
prioridade, histórico, notificações com falha e retentativa, cancelamento e
reabertura, restauração do identificador, erros HTTP, recuperação da conexão e
ausência de transbordamento horizontal em telas pequenas.

## Limites

A consulta da fila ativa mantém o array disponibilizado pelo backend. Histórico e
notificações são paginados. A atualização periódica pode atrasar em abas suspensas
pelo navegador e é retomada nas consultas seguintes. Não há envio real de
notificações, autenticação ou publicação em nuvem. O serviço Docker de frontend
serve somente arquivos compilados e o proxy, sem servidor Vite de desenvolvimento.

O `npm audit` apontou um alerta transitivo em `picomatch`, usado pelas ferramentas
de desenvolvimento Vite, sem versão corrigida disponível na linha atual durante
esta implementação. As dependências estão travadas em `package-lock.json`; o
servidor de desenvolvimento está limitado ao endereço local. Revise o alerta ao
atualizar essas ferramentas.
