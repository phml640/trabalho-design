import { defineConfig } from '@playwright/test';

const externalUrl = process.env.E2E_BASE_URL;

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  timeout: 60000,
  expect: { timeout: 12000 },
  reporter: 'list',
  use: {
    baseURL: externalUrl || 'http://127.0.0.1:5173',
    viewport: { width: 1440, height: 1000 },
    locale: 'pt-BR',
    timezoneId: 'America/Sao_Paulo',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    launchOptions: {
      ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH
        ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH }
        : {}),
    },
  },
  webServer: externalUrl
    ? undefined
    : {
        command: 'npm run dev -- --port 5173 --strictPort',
        url: 'http://127.0.0.1:5173',
        reuseExistingServer: !process.env.CI,
      },
});
