import { chromium } from '@playwright/test'
import { mkdirSync } from 'node:fs'

const BASE = process.env.SHOT_BASE_URL ?? 'http://127.0.0.1:5173'
const OUT = process.argv[2] ?? new URL('../../docs/screenshots', import.meta.url).pathname
const QUESTION =
  'Are the extreme age values concentrated in one source system? Compare sources, show a chart, and distinguish observations from possible causes.'

mkdirSync(OUT, { recursive: true })

// SHOT_CHANNEL=chrome reuses a local Chrome install in a fresh temporary profile,
// which avoids downloading Playwright's bundled browser.
const browser = await chromium.launch(
  process.env.SHOT_CHANNEL ? { channel: process.env.SHOT_CHANNEL } : {},
)
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 2,
  colorScheme: 'light',
})
const page = await context.newPage()

const shot = async (name, opts = {}) => {
  await page.waitForTimeout(700)
  await page.screenshot({ path: `${OUT}/${name}.png`, ...opts })
  console.log('captured', name)
}

// Loading the demo clears the session, so only do it when the demo is not already
// the active dataset. That keeps a completed investigation reusable across runs.
const current = await page.request.get(`${BASE}/api/datasets/current`)
const loaded = current.ok() ? await current.json() : null
if (loaded?.file_name !== 'suspicious_customers.csv') {
  const res = await page.request.post(`${BASE}/api/datasets/demo`)
  if (!res.ok()) throw new Error(`demo load failed: ${res.status()}`)
}
await page.goto(BASE)
await page.getByRole('heading', { name: 'suspicious_customers.csv' }).waitFor()

// 1. Investigation first: it is the slow one.
await page.getByRole('tab', { name: /Investigator/ }).click()

// The backend keeps one session, so a finished investigation from an earlier run is
// reused rather than paying for a second live model call.
const session = await (await page.request.get(`${BASE}/api/datasets/current`)).json()
const existing = (session.investigations ?? []).some((i) => i.status === 'completed')
if (existing) {
  console.log('reusing the completed investigation already in this session')
} else {
  await page.getByLabel('What would you like to understand?').fill(QUESTION)
  await page.getByRole('button', { name: 'Run investigation' }).click()
  console.log('investigation started')
}
await page
  .getByRole('button', { name: 'Investigation in progress' })
  .waitFor({ state: 'detached', timeout: 900_000 })
  .catch(() => console.log('progress button never appeared or already finished'))
await page.waitForFunction(
  () => !document.body.innerText.includes('Investigation in progress'),
  null,
  { timeout: 900_000, polling: 1000 },
)
console.log('investigation finished')
await page.waitForTimeout(2500)
await shot('investigator', { fullPage: true })

// The expandable trace is the point of the app: every claim traces to code that ran.
await page.getByText('View investigation trace').click()
await page.locator('.trace[open]').waitFor()
// Frame the first executed code block rather than the summary above it.
await page.locator('.trace-step').first().scrollIntoViewIfNeeded()
await page.mouse.wheel(0, -120)
await shot('trace')
await page.getByText('View investigation trace').click()

// 2. Overview, light and dark.
await page.getByRole('tab', { name: /Overview/ }).click()
await shot('overview-light')
await page.getByRole('button', { name: 'Switch to dark theme' }).click()
await page.locator('html.dark').waitFor()
await shot('overview-dark')
await page.getByRole('button', { name: 'Switch to light theme' }).click()
await page.locator('html:not(.dark)').waitFor()

// 3. Findings.
await page.getByRole('tab', { name: /Findings/ }).click()
await shot('findings', { fullPage: true })

// 4. Columns with a numeric distribution.
await page.getByRole('tab', { name: 'Columns' }).click()
await page.getByRole('button', { name: 'age', exact: true }).click()
await page.getByLabel('age distribution').waitFor()
await shot('columns')

await browser.close()
console.log('done')
