import { test, expect } from '@playwright/test'
import { readFile } from 'node:fs/promises'

test('verify wall + pheromone fixes', async ({ page }) => {
  await page.goto('/')
  const fileBytes = await readFile('tests/fixtures/_repro.cbor')
  const fileChooserPromise = page.waitForEvent('filechooser')
  await page.locator('label:has-text("Drop a .cbor file here")').click()
  ;(await fileChooserPromise).setFiles({ name: 'rich.cbor', mimeType: 'application/cbor', buffer: fileBytes })
  await expect(page.locator('svg').first()).toBeVisible()

  const wallSvgs = await page.locator('g[data-layer="walls"] line').count()
  console.log('WALL ELEMENTS:', wallSvgs)

  const fp = async () =>
    page.locator('g[data-layer="pheromone"] rect').evaluateAll(
      (els) => els.map((e) => e.getAttribute('fill')).join('|')
    )

  const scrub = page.locator('[data-test="scrub"]')
  const max = parseInt((await scrub.getAttribute('max')) ?? '0')

  const samples: Record<string, { distinct: number; first8: string }> = {}
  for (const v of [0, Math.floor(max/2), max, 0, Math.floor(max/2)]) {
    await scrub.evaluate((el: HTMLInputElement, val) => {
      el.value = String(val)
      el.dispatchEvent(new Event('input', { bubbles: true }))
    }, v)
    await page.waitForTimeout(150)
    const f = await fp()
    samples[`s${Object.keys(samples).length}_at${v}`] = { distinct: new Set(f.split('|')).size, first8: f.slice(0, 80) }
  }
  console.log(JSON.stringify(samples, null, 2))

  // Check walls visible in DOM order (after pheromone group)
  const layerOrder = await page.locator('svg g[data-layer]').evaluateAll((gs) =>
    gs.map((g) => g.getAttribute('data-layer'))
  )
  console.log('LAYER ORDER:', layerOrder.join(' > '))

  await scrub.evaluate((el: HTMLInputElement) => {
    el.value = el.max
    el.dispatchEvent(new Event('input', { bubbles: true }))
  })
  await page.waitForTimeout(150)
  await page.screenshot({ path: '/tmp/viz-fixed.png', fullPage: true })
})
