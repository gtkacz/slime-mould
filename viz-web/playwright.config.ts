import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 60_000,
  use: { baseURL: 'http://127.0.0.1:8001', trace: 'retain-on-failure' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'uv run zipmould viz serve --port 8001',
    url: 'http://127.0.0.1:8001/api/health',
    timeout: 30_000,
    reuseExistingServer: !process.env.CI,
    cwd: '..',
  },
})
