import { expect, test } from '@playwright/test'

async function loadDemo(page: import('@playwright/test').Page) {
  // The persisted local session may already contain a dataset, which hides the
  // upload-screen control. Seed the same endpoint the control calls, then
  // verify the complete rendered demo workspace through the browser.
  const response = await page.request.post('/api/datasets/demo')
  expect(response.ok()).toBeTruthy()
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'suspicious_customers.csv' })).toBeVisible()
  await expect(page.getByRole('tab', { name: /Overview/ })).toHaveAttribute('data-state', 'active')
}

test.describe('Dataset Investigator core UI', () => {
  // The local backend holds one active dataset, so these live-stack checks must be serial.
  test.describe.configure({ mode: 'serial' })

  test.beforeEach(async ({ page }) => {
    await loadDemo(page)
  })

  test('profiles the built-in demo and renders overview metrics', async ({ page }) => {
    await expect(page.getByText('1,212', { exact: true }).first()).toBeVisible()
    await expect(page.getByText('Missingness by column', { exact: true })).toBeVisible()
    await expect(page.getByLabel('Missingness by column')).toBeVisible()
    await expect(page.getByText('11 total', { exact: true })).toBeVisible()
  })

  test('uploads a CSV through the file input and shows its filename and shape', async ({ page }) => {
    await page.locator('input[type=file]').setInputFiles({
      name: 'browser_upload.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from('value,source\n1,A\n2,B\n3,A\n'),
    })

    await expect(page.getByRole('heading', { name: 'browser_upload.csv' })).toBeVisible()
    await expect(page.getByText('3 rows', { exact: true })).toBeVisible()
    await expect(page.getByText('2 columns', { exact: true })).toBeVisible()
  })

  test('uploads a Parquet fixture through the file input and shows its filename and shape', async ({ page }) => {
    await page.locator('input[type=file]').setInputFiles('../tests/fixtures/browser_upload.parquet')

    await expect(page.getByRole('heading', { name: 'browser_upload.parquet' })).toBeVisible()
    await expect(page.getByText('3 rows', { exact: true })).toBeVisible()
    await expect(page.getByText('2 columns', { exact: true })).toBeVisible()
  })

  test('filters findings and closes a detail sheet with Escape', async ({ page }) => {
    await page.getByRole('tab', { name: /Findings/ }).click()
    await page.locator('.filter-chip', { hasText: 'Medium' }).click()
    await expect(page.getByText('8 of 11 findings', { exact: true })).toBeVisible()

    await page.getByLabel('Filter by source').selectOption('agent')
    await expect(page.getByRole('heading', { name: 'No findings in this view' })).toBeVisible()

    await page.getByLabel('Filter by source').selectOption('profiler')
    await page.getByRole('button', { name: /Possible inconsistent labels in state/ }).first().press('Enter')
    await expect(page.getByRole('dialog', { name: 'Finding details' })).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(page.getByRole('dialog', { name: 'Finding details' })).toBeHidden()
  })

  test('renders numeric and categorical column charts', async ({ page }) => {
    await page.getByRole('tab', { name: 'Columns' }).click()
    await page.getByRole('button', { name: 'age', exact: true }).click()
    await expect(page.getByLabel('age distribution')).toBeVisible()
    await page.getByRole('button', { name: 'Box plot', exact: true }).click()
    await expect(page.getByLabel('age distribution')).toBeVisible()

    await page.getByRole('button', { name: 'state', exact: true }).click()
    await expect(page.getByText('Most frequent values', { exact: true })).toBeVisible()
    await expect(page.getByLabel('state distribution')).toBeVisible()
  })

  test('keeps the mobile column selector and details synchronized after search', async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.getByRole('tab', { name: 'Columns' }).click()
    await page.getByLabel('Search columns').fill('income')

    await expect(page.getByRole('combobox', { name: 'Select column' })).toHaveValue('income')
    await expect(page.getByRole('heading', { name: 'income', exact: true })).toBeVisible()
    await expect(page.getByLabel('income distribution')).toBeVisible()
    await page.screenshot({ path: testInfo.outputPath('mobile-column-search.png') })
  })

  test('switches between light and dark themes', async ({ page }) => {
    const themeToggle = page.getByRole('button', { name: 'Switch to dark theme' })
    await themeToggle.click()
    await expect(page.locator('html')).toHaveClass(/dark/)
    await expect(page.getByRole('button', { name: 'Switch to light theme' })).toBeVisible()

    await page.getByRole('button', { name: 'Switch to light theme' }).click()
    await expect(page.locator('html')).not.toHaveClass(/dark/)
  })

  test('shows a useful error for malformed CSV input without replacing the active dataset', async ({ page }) => {
    await page.locator('input[type=file]').setInputFiles({
      name: 'broken.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from('customer_id,age\n"unterminated'),
    })

    const error = page.getByRole('alert')
    await expect(error).toBeVisible()
    await expect(error).not.toContainText('Traceback')
    await expect(page.getByRole('heading', { name: 'suspicious_customers.csv' })).toBeVisible()
  })
})
