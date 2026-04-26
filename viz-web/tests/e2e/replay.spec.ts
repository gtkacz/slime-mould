import { test, expect } from '@playwright/test'
import { readFile } from 'node:fs/promises'

test('upload a CBOR trace and scrub to the last frame', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('ZipMould Visualizer')).toBeVisible()

  const fileBytes = await readFile('tests/fixtures/tiny-trace.cbor')
  const fileChooserPromise = page.waitForEvent('filechooser')
  await page.locator('label:has-text("Drop a .cbor file here")').click()
  const fileChooser = await fileChooserPromise
  await fileChooser.setFiles({
    name: 'tiny.cbor',
    mimeType: 'application/cbor',
    buffer: fileBytes,
  })

  await expect(page.locator('svg').first()).toBeVisible()

  // Scrub to the end via the range input
  const scrub = page.locator('[data-test="scrub"]')
  await scrub.evaluate((el: HTMLInputElement) => {
    el.value = el.max
    el.dispatchEvent(new Event('input', { bubbles: true }))
  })

  // FooterSummary text comes from the fixture: best_fitness=0.5, iters=10
  await expect(page.getByText('iterations')).toBeVisible()
})
