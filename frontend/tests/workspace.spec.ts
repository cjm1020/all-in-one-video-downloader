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

test('play a downloaded clip save notes and study imported captions', async ({ page, request }) => {
  test.setTimeout(150000)
  const created = await request.post('/api/tasks', {
    data: {
      urls: [source],
      preset: 'archive',
      clip_start: 0.5,
      clip_end: 2.5,
    },
  })
  const task = (await created.json()).added[0]
  expect(task).toBeTruthy()
  try {
    await expect
      .poll(async () => (await (await request.get(`/api/tasks/${task.id}`)).json()).status, {
        timeout: 100000,
        intervals: [1000, 2000],
      })
      .toBe('completed')
    const title = `CC0 浏览器播放验证 ${task.id.slice(0, 8)}`
    await request.patch(`/api/tasks/${task.id}`, { data: { title } })
    await page.goto('/#library')
    await page.getByRole('button', { name: `播放 ${title}` }).click()
    const dialog = page.getByRole('dialog')
    await expect
      .poll(() => dialog.locator('video').evaluate((el: HTMLVideoElement) => el.readyState))
      .toBeGreaterThan(0)
    await dialog.getByLabel('我的灵感笔记').fill('记录一个测试灵感，验证资料卡可以持久化。')
    await dialog.getByLabel(/标签/).fill('公开授权, 测试')
    await dialog.getByRole('button', { name: '保存资料卡' }).click()
    await expect
      .poll(async () => (await (await request.get(`/api/tasks/${task.id}`)).json()).notes)
      .toContain('持久化')
    await page.keyboard.press('Escape')
    await expect(dialog).not.toBeVisible()
    const card = page.locator('.media-card').filter({ hasText: title })
    await card.getByRole('button', { name: '标记特别喜欢' }).click()
    await expect(card.getByRole('button', { name: '取消特别喜欢' })).toBeVisible()
    await card.getByRole('button', { name: '学习资料卡' }).click()
    await expect(page.locator('.learning-content').getByRole('heading', { name: title })).toBeVisible()
    await page.getByRole('button', { name: '导入字幕', exact: true }).click()
    await page
      .getByLabel('或粘贴字幕文本')
      .fill(
        '这是字幕导入功能的测试资料，不是花朵视频的原字幕。\n学习资料可以导出为 Markdown，笔记可以保存在本地。\n测试要点来自输入字幕，系统不会凭空生成内容。',
      )
    await page.getByRole('button', { name: '种下字幕' }).click()
    await page.getByRole('button', { name: '提取本地要点' }).click()
    await expect(page.locator('.summary-text')).toContainText('测试资料')
    expect((await request.get(`/api/tasks/${task.id}/export`)).status()).toBe(200)
    expect((await request.get(`/api/tasks/${task.id}/poster`)).status()).toBe(200)
  } finally {
    await request.post(`/api/tasks/${task.id}/actions/cancel`)
    await expect
      .poll(async () => (await request.delete(`/api/tasks/${task.id}`)).status(), {
        timeout: 35000,
        intervals: [1000],
      })
      .toBe(200)
  }
})
