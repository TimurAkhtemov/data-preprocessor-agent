import { defineConfig } from '@playwright/test'

/**
 * These tests deliberately target an already-running local `make dev` stack.
 * They do not start servers or use a user Chrome profile.
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 20_000,
  expect: { timeout: 10_000 },
  workers: 1,
  fullyParallel: false,
  outputDir: 'test-results',
  reporter: 'line',
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://127.0.0.1:5173',
    browserName: 'chromium',
    channel: process.env.E2E_CHANNEL === 'chrome' ? 'chrome' : 'chromium',
    colorScheme: 'light',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
  },
})
