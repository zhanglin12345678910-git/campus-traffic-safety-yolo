// Read-only UI audit: never executes, confirms, uploads, or changes production records.
const fs = require('fs')
const path = require('path')
const { chromium } = require('playwright')

const baseUrl = (process.env.E2E_BASE_URL || 'http://127.0.0.1:5173').replace(/\/$/, '')
const phase = process.env.UI_POLISH_PHASE || 'after'
if (!['before', 'after'].includes(phase)) throw new Error('UI_POLISH_PHASE must be before or after')
const outputDir = path.resolve(__dirname, `../output/playwright/ui-polish/${phase}`)
fs.mkdirSync(outputDir, { recursive: true })
const cases = []
const errors = []
const assert = (condition, message) => { if (!condition) throw new Error(message) }

async function check(name, action) {
  try { await action(); cases.push({ name, status: 'passed' }) }
  catch (error) { cases.push({ name, status: 'failed', error: String(error.stack || error) }) }
}

async function stable(page, route, marker) {
  const response = await page.goto(`${baseUrl}${route}`, { waitUntil: 'networkidle', timeout: 30_000 })
  assert(response?.ok(), `Navigation failed: ${route}`)
  await page.getByText(marker, { exact: false }).first().waitFor({ state: 'visible' })
  await page.evaluate(async () => {
    await document.fonts.ready
    await Promise.all([...document.images].map(image => image.decode().catch(() => undefined)))
  })
  // Allow chart and Element Plus progress animations to finish before accepting screenshots.
  await page.waitForTimeout(1200)
  const layout = await page.evaluate(() => ({
    overflow: document.documentElement.scrollWidth - innerWidth,
    brokenImages: [...document.images].filter(image => image.getBoundingClientRect().width > 0 && (!image.complete || !image.naturalWidth)).map(image => image.alt),
  }))
  assert(layout.overflow <= 1, `${route}: horizontal overflow ${layout.overflow}px`)
  assert(!layout.brokenImages.length, `${route}: broken images ${layout.brokenImages}`)
}

async function main() {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || undefined })
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'zh-CN', reducedMotion: 'reduce' })
    const page = await context.newPage()
    page.on('pageerror', error => errors.push(String(error)))
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()) })
    page.on('response', response => { if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`) })
    page.on('requestfailed', request => errors.push(`${request.url()} ${request.failure()?.errorText}`))
    const tasksResponse = await context.request.get(`${baseUrl}/api/v1/inspections`)
    assert(tasksResponse.ok(), 'Cannot read current tasks')
    const list = await tasksResponse.json()
    let detail
    for (const item of list.items || list) {
      const response = await context.request.get(`${baseUrl}/api/v1/inspections/${item.id}`)
      if (!response.ok()) continue
      const task = await response.json()
      if (task.risk_result?.knowledge_references?.length && task.risk_result?.recommendations?.length) { detail = task; break }
    }
    assert(detail, 'A real task with references and recommendations is required')
    const routes = [
      ['/dashboard', '风险事件队列', '01-dashboard'],
      ['/inspection/new', '创建现场巡检', '02-create'],
      ['/inspections', '历史巡检记录', '03-archives'],
      ['/reviews', '人工复核队列', '04-reviews'],
      ['/analytics', '巡检数据分析', '05-analytics'],
      ['/knowledge', '校园交通安全知识库', '06-knowledge'],
      ['/settings', '服务与访问配置', '07-settings'],
      [`/inspection/${detail.id}`, 'AI Agent 执行轨迹', '08-detail'],
    ]
    for (const [route, marker, name] of routes) {
      await check(`1440px ${name}: stable assets and layout`, async () => {
        await stable(page, route, marker)
        await page.screenshot({ path: path.join(outputDir, `${name}-1440x1000.png`), fullPage: true })
      })
    }
    if (phase === 'after') {
      await check('Knowledge file picker and keyboard document selection', async () => {
        await stable(page, '/knowledge', '校园交通安全知识库')
        const picker = page.locator('.knowledge-file-picker')
        assert(await picker.innerText() === '选择知识文档', 'File picker has no explicit Chinese prompt')
        const sourceDir = path.resolve(__dirname, '../../knowledge')
        const sourceFile = fs.readdirSync(sourceDir).find(name => name.endsWith('.md'))
        await picker.locator('input').setInputFiles(path.join(sourceDir, sourceFile))
        assert((await picker.innerText()).includes(sourceFile), 'Selected filename does not reflect the actual file')
        const second = page.locator('.document-list [role="button"]').nth(1)
        await second.focus()
        await second.press('Space')
        assert(await second.getAttribute('aria-pressed') === 'true', 'Space did not select the source')
        assert((await page.locator('.selected-doc-hero strong').innerText()) === (await second.locator('strong').innerText()), 'Metadata selection mismatch')
        await page.screenshot({ path: path.join(outputDir, '06-knowledge-file-keyboard.png'), fullPage: true })
      })
      await check('Readable service cards, model names and touch controls', async () => {
        await stable(page, '/settings', '服务与访问配置')
        const facts = await page.evaluate(() => ({
          columns: getComputedStyle(document.querySelector('.settings-service-grid')).gridTemplateColumns.split(' ').length,
          cards: [...document.querySelectorAll('.settings-service-grid p, .settings-service-grid article > small')].map(node => ({
            font: parseFloat(getComputedStyle(node).fontSize), whiteSpace: getComputedStyle(node).whiteSpace,
            color: getComputedStyle(node).color, overflow: node.scrollWidth - node.clientWidth,
          })),
        }))
        assert(facts.columns === 4, `Expected 4 desktop service columns, got ${facts.columns}`)
        assert(facts.cards.every(node => node.font >= 12 && node.whiteSpace !== 'nowrap' && node.overflow <= 1), `Clipped/small service text: ${JSON.stringify(facts)}`)
        assert((await page.locator('.model-role-grid .role-vision strong').innerText()) === 'qwen3-vl-plus', 'Actual Qwen model is not shown')
        await page.setViewportSize({ width: 2560, height: 1440 })
        await stable(page, '/settings', '服务与访问配置')
        assert(await page.locator('.settings-service-grid').evaluate(node => getComputedStyle(node).gridTemplateColumns.split(' ').length) === 7, 'Wide service grid should have 7 columns')
        await page.screenshot({ path: path.join(outputDir, '07-settings-2560x1440.png'), fullPage: true })
      })
      await check('Risk summary and full reference disclosure match real task', async () => {
        await page.setViewportSize({ width: 1440, height: 1000 })
        await stable(page, `/inspection/${detail.id}`, 'AI Agent 执行轨迹')
        assert(await page.locator('.risk-summary-copy').innerText() === detail.risk_result.problem_summary, 'Risk summary content changed')
        const summaryStyle = await page.locator('.risk-summary-copy').evaluate(node => ({ font: parseFloat(getComputedStyle(node).fontSize), weight: Number(getComputedStyle(node).fontWeight) }))
        assert(summaryStyle.font >= 14 && summaryStyle.weight <= 500, `Risk summary is still a small bold heading: ${JSON.stringify(summaryStyle)}`)
        const reference = page.locator('.detail-knowledge-list details').first()
        // innerText collapses whitespace by design; compare raw DOM text to preserve source newlines.
        assert(await reference.locator('p').textContent() === detail.risk_result.knowledge_references[0].content, 'Full knowledge content does not match the API')
        await reference.locator('summary').focus()
        await reference.locator('summary').press('Enter')
        assert(await reference.getAttribute('open') === null, 'Enter did not collapse the reference')
        await reference.locator('summary').press('Enter')
        assert(await reference.getAttribute('open') !== null, 'Enter did not expand the reference')
        assert(await reference.locator('p').evaluate(node => getComputedStyle(node).webkitLineClamp) === 'none', 'Full reference is line-clamped')
        await page.screenshot({ path: path.join(outputDir, '08-detail-reference-keyboard.png'), fullPage: true })
      })
      await page.setViewportSize({ width: 390, height: 844 })
      for (const [route, marker, name] of routes) {
        await check(`390px ${name}: reflow, complete controls and assets`, async () => {
          await stable(page, route, marker)
          const targets = await page.locator('.task-actions .el-button, .page-toolbar .el-button, .search-empty-state button, .knowledge-file-picker, .status-filter-list button').evaluateAll(nodes => nodes.filter(node => node.getBoundingClientRect().width > 0).map(node => {
            const box = node.getBoundingClientRect()
            return { text: node.textContent.trim(), left: box.left, right: box.right, height: box.height }
          }))
          assert(targets.every(box => box.left >= 0 && box.right <= 391 && box.height >= 40), `Clipped/small touch target: ${JSON.stringify(targets)}`)
          if (route === '/settings' || route === '/knowledge') {
            const labels = await page.locator('.settings-summary article > span, .settings-summary article > small, .knowledge-summary article > span, .knowledge-summary article > small').evaluateAll(nodes => nodes.map(node => ({
              text: node.textContent.trim(), width: node.getBoundingClientRect().width,
              height: node.getBoundingClientRect().height, lineHeight: parseFloat(getComputedStyle(node).lineHeight),
            })))
            assert(labels.length > 0 && labels.every(node => node.width >= 80 && node.height <= node.lineHeight * 2 + 1), `Summary labels squeezed into vertical text: ${JSON.stringify(labels)}`)
            const values = await page.locator('.settings-summary strong, .knowledge-summary strong').evaluateAll(nodes => nodes.map(node => ({ text: node.textContent.trim(), overflow: node.scrollWidth - node.clientWidth })))
            assert(values.every(node => node.overflow <= 1), `Summary value clipped: ${JSON.stringify(values)}`)
          }
          await page.screenshot({ path: path.join(outputDir, `${name}-390x844.png`), fullPage: true })
        })
      }
    }
    await check('No browser or network errors', async () => assert(!errors.length, JSON.stringify(errors)))
    const report = { phase, generated_at: new Date().toISOString(), summary: { total: cases.length, passed: cases.filter(item => item.status === 'passed').length, failed: cases.filter(item => item.status === 'failed').length }, cases, errors }
    fs.writeFileSync(path.join(outputDir, 'report.json'), JSON.stringify(report, null, 2))
    console.log(JSON.stringify(report, null, 2))
    if (report.summary.failed) process.exitCode = 1
  } finally { await browser.close() }
}

main().catch(error => { console.error(error); process.exitCode = 1 })
