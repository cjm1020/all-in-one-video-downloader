import { expect, test } from '@playwright/test'

const source = 'https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4'

test('schedule and control a real queue entry through the workbench', async ({ page, request }) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.goto('/')
  await expect(page.getByRole('heading', { name: /把喜欢的片刻/ })).toBeVisible()
  await expect(page.getByRole('button', { name: '开始收藏', exact: true })).toBeEnabled()
  await page.getByRole('textbox', { name: '视频链接', exact: true }).fill(source)
  await page.getByRole('button', { name: '更多小偏好' }).click()
  const future = new Date(Date.now() + 3600000)
  const local = new Date(future.getTime() - future.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
  await page.getByLabel('预约下载时间').fill(local)
  // Distinct clip range avoids clashing with the separate live smoke test.
  await page.getByLabel('灵感剪辑 · 开始秒数').fill('0.25')
  await page.getByLabel('结束秒数', { exact: true }).fill('1.75')
  await page.getByRole('button', { name: '开始收藏', exact: true }).click()
  await expect(page.getByRole('heading', { name: '精彩，正在慢慢抵达' })).toBeVisible()
  const item = page.locator('.queue-item').filter({ hasText: '0.25–1.75' })
  await expect(item.getByText('已预约', { exact: true })).toBeVisible()
  const tasks = await (await request.get('/api/tasks')).json()
  const task = tasks.find((t: { clip_start: number }) => t.clip_start === 0.25)
  try {
    await item.getByRole('button', { name: '暂停任务' }).click()
    await expect(item.getByText('已暂停', { exact: true })).toBeVisible()
    await item.getByRole('button', { name: '继续任务' }).click()
    await expect(item.getByText('已预约', { exact: true })).toBeVisible()
    await item.getByRole('button', { name: '取消任务' }).click()
    await expect(item.getByText('已取消', { exact: true })).toBeVisible()
    expect(errors).toEqual([])
  } finally {
    await request.delete(`/api/tasks/${task.id}`)
  }
})

test('create a collection and keep keyboard focus inside the dialog', async ({ page, request }) => {
  await page.goto('/#library')
  await page.getByRole('button', { name: '新建合集' }).click()
  const dialog = page.getByRole('dialog')
  const name = `浏览器验证-${Date.now()}`
  await dialog.getByLabel('合集名称').fill(name)
  await dialog.getByRole('button', { name: '淡紫色' }).click()
  await dialog.getByRole('button', { name: '创建小抽屉' }).focus()
  await page.keyboard.press('Tab')
  await expect(dialog.getByRole('button', { name: '关闭弹窗' })).toBeFocused()
  await dialog.getByRole('button', { name: '创建小抽屉' }).click()
  await expect(page.getByRole('button', { name: new RegExp(name) })).toBeVisible()
  const collections = await (await request.get('/api/collections')).json()
  const created = collections.find((c: { name: string }) => c.name === name)
  await request.delete(`/api/collections/${created.id}`)
})

test('all five views fit a narrow screen and the mobile menu works', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.goto('/')
  for (const [name, heading] of [
    ['下载工作台', '把喜欢的片刻'],
    ['下载队列', '精彩，正在慢慢抵达'],
    ['媒体收藏', '喜欢的，都在这里'],
    ['学习花园', '让好内容，长出小收获'],
    ['偏好设置', '按你的节奏来'],
  ]) {
    await page.getByRole('button', { name: '打开导航' }).click()
    await page
      .getByRole('navigation')
      .getByRole('button', { name: new RegExp(name!) })
      .click()
    await expect(page.getByRole('heading', { name: new RegExp(heading!) }).first()).toBeVisible()
    const fits = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)
    expect(fits, `${name} should have no horizontal overflow`).toBeTruthy()
  }
  expect(errors).toEqual([])
})
