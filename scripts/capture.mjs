import fs from 'node:fs/promises'
import { createRequire } from 'node:module'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const require = createRequire(new URL('../frontend/package.json', import.meta.url))
const { chromium } = require('playwright')
const root = fileURLToPath(new URL('../docs/screenshots/', import.meta.url))
await fs.mkdir(root, { recursive: true })
const browser = await chromium.launch({
  headless: true,
  ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}),
})
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1080 }, deviceScaleFactor: 1, reducedMotion: 'reduce' })
  const base = process.env.BASE_URL || 'http://localhost:8090'
  await page.goto(base, { waitUntil: 'domcontentloaded' })
  await page.waitForFunction(() => document.querySelector('.download-submit') && !document.querySelector('.download-submit').disabled)
  for (const name of ['home', 'queue', 'library', 'learning', 'settings']) {
    await page.goto(`${base}/#${name}`, { waitUntil: 'domcontentloaded' })
    await page.locator(name === 'home' ? '.hero-panel' : '.page-heading').waitFor()
    if (name === 'learning') {
      const first = page.locator('.learning-item').filter({ hasText: '已整理要点' }).first()
      if (await first.count()) {
        await first.click()
        await page.locator('.summary-card').waitFor()
      }
    }
    await page.screenshot({ path: path.join(root, `${name}.png`), fullPage: true })
  }
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto(`${base}/#home`, { waitUntil: 'domcontentloaded' })
  await page.locator('.hero-panel').waitFor()
  await page.screenshot({ path: path.join(root, 'mobile.png'), fullPage: true })
  console.log(`Screenshots saved to ${root}`)
} finally {
  await browser.close()
}
