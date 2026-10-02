import { expect, test } from '@playwright/test'

test('project workflow preserves readiness guards and rights evidence through the UI', async ({ page, request }) => {
  const source = `https://example.com/studio-browser-${Date.now()}.mp4`
  const created = await request.post('/api/tasks', {
    data: { urls: [source], scheduled_at: new Date(Date.now() + 86400000).toISOString() },
  })
  expect(created.status()).toBe(201)
  const task = (await created.json()).added[0]
  const name = `浏览器交付项目 ${Date.now()}`
  let projectId = ''
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  try {
    await page.goto('/#studio')
    await page.getByRole('button', { name: '创建项目', exact: true }).click()
    const dialog = page.getByRole('dialog')
    await dialog.getByLabel('项目名称').fill(name)
    await dialog.getByLabel('客户 / 团队').fill('内容制作验收')
    await dialog.getByLabel('项目预算（元）').fill('1500.50')
    await dialog.getByLabel('交付说明').fill('这是一份模拟项目记录，验证真实交付操作。')
    await dialog.getByRole('button', { name: '保存项目' }).click()
    await expect(page.getByRole('heading', { name, exact: true })).toBeVisible()
    const projects = await (await request.get('/api/studio/projects')).json()
    const project = projects.find((p: { name: string }) => p.name === name)
    projectId = project.id
    expect(project.budget_cents).toBe(150050)
    await expect(page.getByRole('button', { name: '标记已交付' })).toBeDisabled()

    await page.getByRole('button', { name: '管理素材' }).click()
    await dialog.getByRole('checkbox', { name: new RegExp(source.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')) }).check()
    await dialog.getByRole('button', { name: '保存素材清单' }).click()
    await expect(page.getByRole('button', { name: '授权记录' })).toBeVisible()
    await page.getByRole('button', { name: '授权记录' }).click()
    await dialog.getByLabel('授权类型').selectOption('cc-by')
    await dialog.getByLabel('署名文字').fill('Synthetic fixture — browser acceptance only')
    await dialog.getByLabel('授权证据链接').fill('https://example.com/license')
    await dialog.getByLabel('我已核验授权适用于本项目用途').check()
    await dialog.getByRole('button', { name: '保存授权' }).click()
    await expect(dialog).not.toBeVisible()
    await expect(page.getByText('授权已核验', { exact: true })).toBeVisible()
    const detail = await (await request.get(`/api/studio/projects/${projectId}`)).json()
    expect(detail.checklist.licensed).toBe(1)
    expect(detail.checklist.ready).toBe(false)
    await expect(page.getByRole('button', { name: '标记已交付' })).toBeDisabled()
    await expect(page.getByRole('button', { name: '下载交付 ZIP' })).toBeDisabled()
    expect((await request.get(`/api/studio/projects/${projectId}/export?format=json`)).status()).toBe(200)
    expect(errors).toEqual([])
  } finally {
    if (!projectId) {
      const projects = await (await request.get('/api/studio/projects')).json()
      projectId = projects.find((p: { name: string }) => p.name === name)?.id || ''
    }
    if (projectId) await request.delete(`/api/studio/projects/${projectId}`)
    await request.delete(`/api/tasks/${task.id}`)
  }
})

test('subtitle search, markers and source-backed reviews form a complete learning workflow', async ({ page, request }) => {
  const created = await request.post('/api/tasks', {
    data: { urls: [`https://example.com/knowledge-browser-${Date.now()}.mp4`], scheduled_at: new Date(Date.now() + 86400000).toISOString() },
  })
  const task = (await created.json()).added[0]
  const title = `原句学习验证 ${Date.now()}`
  await request.patch(`/api/tasks/${task.id}`, { data: { title } })
  const phrase = `证据词${Date.now()}`
  await request.post(`/api/tasks/${task.id}/transcript`, {
    data: { text: `WEBVTT\n\n00:00:01.000 --> 00:00:04.000\n${phrase}：字幕检索需要保留原文证据，复习卡应当在字幕更新时撤下。` },
  })
  try {
    await page.goto('/#learning')
    await page.getByLabel('搜索所有字幕').fill(phrase)
    await page.getByRole('button', { name: '搜索字幕', exact: true }).click()
    await expect(page.getByText('找到 1 处相关片段')).toBeVisible()
    const match = page.locator('.search-match').filter({ hasText: title })
    await expect(match).toContainText('0:01')
    // Queued transcripts remain searchable; playback becomes available after completion.
    expect((await request.get(`/api/knowledge/tasks/${task.id}/brief?format=json`)).status()).toBe(200)
    const marker = await request.post(`/api/knowledge/tasks/${task.id}/markers`, { data: { position: 1, label: '事务边界' } })
    expect(marker.status()).toBe(201)
    const generated = await (await request.post(`/api/knowledge/tasks/${task.id}/cards/generate`)).json()
    expect(generated.added.length).toBeGreaterThan(0)
    await page.reload()
    await page.getByRole('button', { name: '开始复习' }).click()
    const review = page.locator('.review-card')
    await expect(review).toBeVisible()
    await review.getByRole('button', { name: '想好以后，查看答案' }).click()
    await expect(review).toContainText('原句：')
    await review.getByRole('button', { name: '基本记住' }).click()
    await expect(page.getByText('复习已完成。新建复习卡后，可以回到这里开始。')).toBeVisible()
    const cards = await (await request.get(`/api/knowledge/tasks/${task.id}/cards`)).json()
    expect(cards[0].interval_days).toBe(1)
  } finally {
    await request.delete(`/api/tasks/${task.id}`)
  }
})

test('commercial views and ROI calculations fit a narrow viewport', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.setViewportSize({ width: 390, height: 844 })
  for (const [route, heading] of [
    ['studio', '把灵感，交付成作品'],
    ['insights', '看见每一份积累的价值'],
    ['learning', '让好内容，长出小收获'],
  ]) {
    await page.goto(`/#${route}`)
    await expect(page.getByRole('heading', { name: heading!, exact: true })).toBeVisible()
    if (route === 'insights') {
      await expect(page.getByLabel('人工时薪（元 / 小时）')).toBeVisible()
      await page.getByLabel('人工时薪（元 / 小时）').fill('200')
      await page.getByLabel('每份手动处理时间（分钟）').fill('10')
      await expect(page.getByText('预计节省时间')).toBeVisible()
      await expect(page.getByText(/结果为假设估算/)).toBeVisible()
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), `${route} fits mobile`).toBe(true)
  }
  expect(errors).toEqual([])
})

test('a custom workflow runs from the UI and skips an existing scheduled source', async ({ page, request }) => {
  const source = `https://example.com/recipe-browser-${Date.now()}.mp4`
  const name = `研究配方 ${Date.now()}`
  const created = await request.post('/api/tasks', {
    data: { urls: [source], scheduled_at: new Date(Date.now() + 86400000).toISOString() },
  })
  const task = (await created.json()).added[0]
  let workflowId = ''
  try {
    await page.goto('/#studio')
    await page.getByRole('button', { name: '自定义配方' }).click()
    const dialog = page.getByRole('dialog')
    await dialog.getByLabel('配方名称').fill(name)
    await dialog.getByLabel('用途说明').fill('模拟工作流验收，不执行实际网络下载。')
    await dialog.getByLabel('标签（用逗号分隔）').fill('客户素材, 研究')
    await dialog.getByRole('button', { name: '保存配方' }).click()
    await expect(dialog).not.toBeVisible()
    const recipe = page.locator('.recipe-card').filter({ hasText: name })
    await expect(recipe).toBeVisible()
    const workflows = await (await request.get('/api/studio/workflows')).json()
    workflowId = workflows.find((w: { name: string }) => w.name === name).id
    await recipe.getByRole('button', { name: '使用配方' }).click()
    await dialog.getByLabel('视频链接（每行一个）').fill(source)
    await dialog.getByRole('button', { name: '运行配方' }).click()
    await expect(dialog.getByRole('status')).toContainText('已加入 0 个下载任务，跳过 1 个重复链接')
    await dialog.getByRole('button', { name: '关闭', exact: true }).click()
    await page.goto('/#insights')
    await expect(page.getByText('运行工作流', { exact: true }).first()).toBeVisible()
  } finally {
    if (!workflowId) {
      const workflows = await (await request.get('/api/studio/workflows')).json()
      workflowId = workflows.find((w: { name: string }) => w.name === name)?.id || ''
    }
    if (workflowId) await request.delete(`/api/studio/workflows/${workflowId}`)
    await request.delete(`/api/tasks/${task.id}`)
  }
})
