import { expect, test } from '@playwright/test';
import type { APIRequestContext, Page } from '@playwright/test';

const queueName = () => `Fila teste ${crypto.randomUUID().slice(0, 8)}`;
async function createQueue(request: APIRequestContext) {
  const response = await request.post('/api/filas', {
    data: { nome: queueName(), descricao: 'Atendimento de demonstração' },
  });
  expect(response.status()).toBe(201);
  return response.json() as Promise<{ id: string; nome: string }>;
}
async function selectQueue(page: Page, name: string) {
  await page.getByRole('button', { name: new RegExp(name) }).click();
}
async function configureCounter(page: Page) {
  await page.getByLabel('Atendente', { exact: true }).fill('Atendente de teste');
  await page.getByLabel('Guichê', { exact: true }).fill('Guichê teste');
}
async function noOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
}

test('página inicial permite escolher as duas visões', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('link', { name: /Acessar como usuário/ })).toHaveAttribute(
    'href',
    '/usuario',
  );
  await expect(page.getByRole('link', { name: /Acessar como administrador/ })).toHaveAttribute(
    'href',
    '/admin',
  );
  await expect(page.getByText(/não realiza login/)).toBeVisible();
  await noOverflow(page);
});

test('duas janelas concluem atendimento, histórico e notificações sem Swagger', async ({
  browser,
  page: admin,
  baseURL,
}, testInfo) => {
  const userContext = await browser.newContext({
    locale: 'pt-BR',
    baseURL,
  });
  const user = await userContext.newPage();
  try {
    await admin.goto('/admin');
    await admin.getByRole('button', { name: 'Nova fila', exact: true }).click();
    const nome = queueName();
    await admin.getByLabel('Nome da fila').fill(nome);
    await admin.getByLabel(/Descrição/).fill('Atendimento de demonstração');
    await admin.getByRole('button', { name: 'Criar fila', exact: true }).click();
    await expect(admin.getByRole('heading', { name: nome, exact: true })).toBeVisible();
    await configureCounter(admin);

    await user.goto('/usuario');
    await selectQueue(user, nome);
    const emitted = user.waitForResponse(
      (response) => response.url().endsWith('/senhas') && response.request().method() === 'POST',
    );
    await user.getByRole('button', { name: 'Emitir minha senha' }).click();
    const senha = await (await emitted).json();
    await expect(user.getByTestId('user-ticket-number')).toHaveText(senha.numero);
    await expect(user.getByRole('button', { name: 'Emitir minha senha' })).toBeDisabled();
    await expect(admin.getByRole('button', { name: 'Chamar próxima senha' })).toBeEnabled();
    await admin.getByRole('button', { name: 'Chamar próxima senha' }).click();
    await expect(admin.getByTestId('admin-ticket-number')).toHaveText(senha.numero);
    await expect(user.getByText('É a sua vez!', { exact: false })).toBeVisible();
    await expect(user.getByText(/Dirija-se ao guichê Guichê teste/)).toBeVisible();
    await admin.getByRole('button', { name: 'Iniciar atendimento', exact: true }).click();
    await expect(user.getByText('Seu atendimento está em andamento.')).toBeVisible();
    await admin.getByRole('button', { name: 'Finalizar atendimento', exact: true }).click();
    await expect(user.getByText('Atendimento concluído. Obrigado pela visita!')).toBeVisible();
    await user.reload();
    await expect(user.getByTestId('user-ticket-number')).toHaveText(senha.numero);
    await expect(user.getByText('Atendimento concluído. Obrigado pela visita!')).toBeVisible();
    expect(await user.evaluate(() => ({ ...localStorage }))).toEqual({
      'em-fila:senha-id': senha.id,
    });

    await admin.getByRole('button', { name: 'Histórico', exact: true }).click();
    await admin.getByLabel('Filtrar histórico por estado').selectOption('finalizada');
    await expect(
      admin.getByRole('row').filter({ hasText: senha.numero }).filter({ hasText: 'Finalizada' }),
    ).toBeVisible();
    await admin.getByRole('button', { name: 'Notificações', exact: true }).click();
    await admin.getByRole('button', { name: 'Simular falha no envio' }).click();
    await expect(
      admin.getByRole('alert').filter({ hasText: 'As chamadas foram preservadas' }),
    ).toBeVisible();
    await expect(admin.getByText('Falha no envio', { exact: true })).toBeVisible();
    await admin.getByRole('button', { name: 'Processar notificações', exact: true }).click();
    await expect(
      admin.getByText(`Senha ${senha.numero} chamada no guichê Guichê teste.`, { exact: true }),
    ).toBeVisible();
    await admin.getByRole('button', { name: `Ver tentativas da senha ${senha.numero}` }).click();
    await expect(admin.getByText('Tentativa 2', { exact: true })).toBeVisible();
    await expect(user.getByText('Atendimento concluído. Obrigado pela visita!')).toBeVisible();
    await noOverflow(admin);
    await admin.screenshot({ path: testInfo.outputPath('admin.png'), fullPage: true });
    await user.screenshot({ path: testInfo.outputPath('usuario.png'), fullPage: true });
  } finally {
    await userContext.close();
  }
});

test('senha prioritária segue a seleção do backend', async ({
  page,
  request,
  browser,
  baseURL,
}) => {
  const fila = await createQueue(request);
  const normalResponse = await request.post(`/api/filas/${fila.id}/senhas`, {
    data: { usuario_id: crypto.randomUUID(), tipo: 'normal' },
  });
  expect(normalResponse.status()).toBe(201);
  const normal = await normalResponse.json();
  await page.goto('/usuario');
  await selectQueue(page, fila.nome);
  await page.getByRole('radio', { name: 'Prioritário', exact: true }).check();
  const response = page.waitForResponse(
    (r) => r.url().endsWith('/senhas') && r.request().method() === 'POST',
  );
  await page.getByRole('button', { name: 'Emitir minha senha' }).click();
  const prioritaria = await (await response).json();
  expect(prioritaria.tipo).toBe('prioritaria');
  const admin = await browser.newPage({ baseURL });
  try {
    await admin.goto('/admin');
    await selectQueue(admin, fila.nome);
    await configureCounter(admin);
    await admin.getByRole('button', { name: 'Chamar próxima senha' }).click();
    await expect(admin.getByTestId('admin-ticket-number')).toHaveText(prioritaria.numero);
    await expect(page.getByText('É a sua vez!', { exact: false })).toBeVisible();
    await admin.getByRole('button', { name: 'Chamar próxima senha' }).click();
    await expect(admin.getByTestId('admin-ticket-number')).toHaveText(normal.numero);
  } finally {
    await admin.close();
  }
});

test('encerramento cancela a senha no celular e a reabertura permite nova emissão', async ({
  page: admin,
  browser,
  request,
  baseURL,
}, testInfo) => {
  const fila = await createQueue(request);
  const mobile = await browser.newPage({ baseURL, viewport: { width: 390, height: 844 } });
  try {
    await mobile.goto('/usuario');
    await selectQueue(mobile, fila.nome);
    const emitted = mobile.waitForResponse(
      (r) => r.url().endsWith('/senhas') && r.request().method() === 'POST',
    );
    await mobile.getByRole('button', { name: 'Emitir minha senha' }).click();
    const antiga = await (await emitted).json();
    await expect(mobile.getByTestId('user-ticket-number')).toHaveText(antiga.numero);
    await admin.goto('/admin');
    await selectQueue(admin, fila.nome);
    await admin.getByRole('button', { name: 'Encerrar fila', exact: true }).click();
    await admin
      .getByRole('dialog')
      .getByRole('button', { name: 'Encerrar fila', exact: true })
      .click();
    await expect(
      mobile.getByText('Sua senha foi cancelada porque a fila foi encerrada.'),
    ).toBeVisible();
    await expect(mobile.getByRole('button', { name: 'Emitir minha senha' })).toBeDisabled();
    await noOverflow(mobile);
    await mobile.screenshot({ path: testInfo.outputPath('usuario-mobile.png'), fullPage: true });
    await admin.getByRole('button', { name: 'Reabrir fila', exact: true }).click();
    await mobile.getByRole('button', { name: 'Solicitar outra senha' }).click();
    await expect(mobile.getByRole('button', { name: 'Emitir minha senha' })).toBeEnabled();
    const next = mobile.waitForResponse(
      (r) => r.url().endsWith('/senhas') && r.request().method() === 'POST',
    );
    await mobile.getByRole('button', { name: 'Emitir minha senha' }).click();
    const nova = await (await next).json();
    expect(nova.id).not.toBe(antiga.id);
    expect((await (await request.get(`/api/senhas/${antiga.id}`)).json()).estado).toBe('cancelada');
  } finally {
    await mobile.close();
  }
});

test('erro de negócio é apresentado e o painel cabe em uma tela pequena', async ({
  page,
  request,
}) => {
  const fila = await createQueue(request);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/admin');
  await selectQueue(page, fila.nome);
  await expect(page.getByRole('heading', { name: fila.nome, exact: true })).toBeVisible();
  await noOverflow(page);
  await page.getByRole('button', { name: 'Nova fila', exact: true }).click();
  await page.getByLabel('Nome da fila').fill(fila.nome);
  await page.getByRole('button', { name: 'Criar fila', exact: true }).click();
  await expect(
    page.getByRole('alert').filter({ hasText: 'Já existe uma fila com esse nome.' }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Fechar formulário', exact: true }).click();
  await page.getByRole('button', { name: 'Histórico', exact: true }).click();
  await noOverflow(page);
});

test('indisponibilidade é informada e a atualização se recupera automaticamente', async ({
  page,
  request,
}) => {
  const fila = await createQueue(request);
  await page.route('**/api/filas', (route) => route.abort());
  await page.goto('/usuario');
  await expect(
    page.getByRole('alert').filter({ hasText: 'Não foi possível acessar o serviço.' }),
  ).toBeVisible();
  await page.unroute('**/api/filas');
  await expect(page.getByRole('button', { name: new RegExp(fila.nome) })).toBeVisible();
  await expect(page.getByRole('alert')).toHaveCount(0);
});

test('identificador inexistente pode ser removido sem inventar estado local', async ({ page }) => {
  await page.addInitScript(
    (id) => localStorage.setItem('em-fila:senha-id', id),
    crypto.randomUUID(),
  );
  await page.goto('/usuario');
  await expect(
    page.getByRole('alert').filter({ hasText: 'A senha salva não está disponível' }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Remover identificador salvo' }).click();
  expect(await page.evaluate(() => localStorage.getItem('em-fila:senha-id'))).toBeNull();
  await expect(page.getByText('Sua senha aparece aqui.')).toBeVisible();
});
