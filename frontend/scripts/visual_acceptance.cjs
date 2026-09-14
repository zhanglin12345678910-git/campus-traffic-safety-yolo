const fs = require('fs')
const path = require('path')
const { chromium } = require('playwright')

const baseUrl = (process.env.E2E_BASE_URL || 'http://127.0.0.1:5173').replace(/\/$/, '')
const outputDir = path.resolve(__dirname, '../output/playwright/visual-audit')
const chromiumExecutable = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || undefined
fs.mkdirSync(outputDir, { recursive: true })

const cases = []
const signals = { pageErrors: [], consoleErrors: [], failedRequests: [], httpErrors: [] }

function observePage(page, device) {
  page.on('pageerror', error => signals.pageErrors.push(`${device}: ${error}`))
  page.on('console', message => {
    if (message.type() === 'error') signals.consoleErrors.push(`${device}: ${message.text()} @ ${message.location().url || 'unknown'}`)
  })
  page.on('requestfailed', request => signals.failedRequests.push(`${device}: ${request.url()} :: ${request.failure()?.errorText || ''}`))
  page.on('response', response => {
    if (response.status() >= 400) signals.httpErrors.push(`${device}: ${response.status()} ${response.url()}`)
  })
}

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function runCase(name, action) {
  const started = Date.now()
  try {
    await action()
    cases.push({ name, status: 'passed', duration_ms: Date.now() - started })
  } catch (error) {
    cases.push({ name, status: 'failed', duration_ms: Date.now() - started, error: String(error.stack || error) })
  }
}

async function goto(page, route) {
  const response = await page.goto(`${baseUrl}${route}`, { waitUntil: 'domcontentloaded', timeout: 60_000 })
  assert(response && response.status() < 400, `${route} returned ${response && response.status()}`)
}

async function main() {
  const browser = await chromium.launch({ headless: true, executablePath: chromiumExecutable })
  const desktop = await browser.newContext({ viewport: { width: 1489, height: 1070 }, locale: 'zh-CN' })
  const page = await desktop.newPage()
  observePage(page, 'desktop')

  await runCase('运行态 API 健康、分析数据与边界', async () => {
    const health = await desktop.request.get(`${baseUrl}/api/v1/health`)
    assert(health.status() === 200, `health returned ${health.status()}`)
    const healthBody = await health.json()
    assert(healthBody.status === 'ok', 'health status is not ok')
    assert(healthBody.services.database === 'ok', 'database is not ok')
    assert(healthBody.services.qdrant.status === 'ok', 'qdrant is not ok')
    assert(healthBody.services.yolo.configured === true, 'traffic-sign YOLO is not configured')
    assert(healthBody.services.general_yolo.configured === true, 'general YOLO is not configured')
    assert(healthBody.services.general_yolo.model_name === 'yolo26m.pt', 'runtime is not configured for YOLO26m')
    assert(healthBody.services.amap.configured === true, 'AMap is not configured')

    const analytics = await desktop.request.get(`${baseUrl}/api/v1/analytics/overview`)
    assert(analytics.status() === 200, `analytics returned ${analytics.status()}`)
    const payload = await analytics.json()
    assert(payload.summary.total_tasks >= 1, 'analytics summary has no persisted tasks')
    assert(payload.daily_trend.length === 30, 'analytics trend is not 30 days')
    assert(payload.area_breakdown.length >= 1, 'area breakdown is empty')
    assert(payload.agent_performance.length >= 1, 'agent performance is empty')

    const missing = await desktop.request.get(`${baseUrl}/api/v1/inspections/not-a-real-task`)
    assert(missing.status() === 404, `missing task returned ${missing.status()}`)
  })

  await runCase('GIS 总览参考尺寸渲染与主导航', async () => {
    await goto(page, '/dashboard')
    await page.getByText('风险事件队列', { exact: false }).first().waitFor({ state: 'visible', timeout: 30_000 })
    await page.getByText('今日巡检', { exact: true }).waitFor({ state: 'visible' })
    await page.locator('.map-mode').waitFor({ state: 'visible' })
    assert(await page.getByText(/演示数据|演示态势|演示队列|演示知识/).count() === 0, 'dashboard exposes synthetic data')
    assert(await page.locator('nav.primary-nav a').count() === 7, 'sidebar does not expose seven routes')
    const metrics = await page.evaluate(() => ({
      viewport: innerWidth,
      documentWidth: document.documentElement.scrollWidth,
      bodyWidth: document.body.scrollWidth,
      mapWidth: document.querySelector('.gis-panel')?.getBoundingClientRect().width || 0,
      mapGap: (() => {
        const map = document.querySelector('.gis-map')?.getBoundingClientRect()
        const panel = document.querySelector('.gis-panel')?.getBoundingClientRect()
        return map && panel ? Math.round(panel.bottom - map.bottom) : Number.POSITIVE_INFINITY
      })(),
      queueWidth: document.querySelector('.incident-queue')?.getBoundingClientRect().width || 0,
      bodyFont: getComputedStyle(document.body).fontFamily,
      kpiBorders: [...document.querySelectorAll('.command-kpi')]
        .map(node => getComputedStyle(node).borderTopColor),
    }))
    assert(metrics.documentWidth <= metrics.viewport + 1, `dashboard overflows: ${JSON.stringify(metrics)}`)
    assert(metrics.mapWidth > metrics.queueWidth * 1.8, `dashboard hierarchy is too flat: ${JSON.stringify(metrics)}`)
    assert(Math.abs(metrics.mapGap) <= 2, `dashboard map does not fit its panel: ${JSON.stringify(metrics)}`)
    assert(metrics.bodyFont.includes('Noto Sans SC'), `installed Chinese UI font is not active: ${JSON.stringify(metrics)}`)
    assert(new Set(metrics.kpiBorders).size >= 4, `dashboard KPI semantic colors collapsed: ${JSON.stringify(metrics)}`)
    await page.screenshot({ path: path.join(outputDir, 'dashboard-1489x1070.png'), fullPage: true })
  })

  await runCase('真实数据分析七图与刷新交互', async () => {
    await goto(page, '/analytics')
    await page.getByRole('heading', { name: '巡检数据分析', exact: true }).waitFor({ state: 'visible' })
    await page.locator('.chart-panel').first().waitFor({ state: 'visible' })
    await page.waitForTimeout(1_500)
    assert(await page.locator('.chart-panel').count() === 7, 'analytics does not contain seven panels')
    assert(await page.locator('.data-chart canvas').count() >= 7, 'one or more ECharts canvases are missing')
    assert(await page.locator('.analytics-error').count() === 0, 'analytics page reports an API error')
    const refreshResponse = page.waitForResponse(response => response.url().endsWith('/api/v1/analytics/overview'), { timeout: 20_000 })
    await page.getByRole('button', { name: '刷新数据', exact: true }).click()
    assert((await refreshResponse).status() === 200, 'analytics refresh request failed')
    await page.locator('.el-loading-mask').waitFor({ state: 'hidden', timeout: 20_000 })
    const metrics = await page.evaluate(() => ({
      viewport: innerWidth,
      documentWidth: document.documentElement.scrollWidth,
      panels: [...document.querySelectorAll('.chart-panel')].map(node => Math.round(node.getBoundingClientRect().width)),
      canvases: document.querySelectorAll('.data-chart canvas').length,
    }))
    assert(metrics.documentWidth <= metrics.viewport + 1, `analytics overflows: ${JSON.stringify(metrics)}`)
    assert(Math.min(...metrics.panels) >= 300, `analytics panel is too narrow: ${JSON.stringify(metrics)}`)
    await page.screenshot({ path: path.join(outputDir, 'analytics-1489x1070.png'), fullPage: true })
    await page.getByRole('button', { name: '进入复核队列', exact: true }).click()
    await page.waitForURL('**/reviews', { timeout: 20_000 })
  })

  await runCase('现有页面路由、标题与主要空态校验', async () => {
    const routes = [
      ['/inspection/new', '创建现场巡检', 'new-inspection-1489x1070.png'],
      ['/inspections', '历史巡检记录', 'inspections-1489x1070.png'],
      ['/reviews', '人工复核队列', 'reviews-1489x1070.png'],
      ['/knowledge', '校园交通安全知识库', 'knowledge-1489x1070.png'],
      ['/settings', '服务与访问配置', 'settings-1489x1070.png'],
    ]
    for (const [route, heading, screenshot] of routes) {
      await goto(page, route)
      await page.getByRole('heading', { name: heading, exact: true }).waitFor({ state: 'visible', timeout: 20_000 })
      await page.waitForTimeout(700)
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
      assert(overflow <= 1, `${route} overflows by ${overflow}px`)
      assert(await page.getByText(/演示数据|演示态势|演示队列|演示知识/).count() === 0, `${route} exposes synthetic data`)
      await page.screenshot({ path: path.join(outputDir, screenshot), fullPage: true })
    }

    await goto(page, '/inspection/new')
    await page.getByRole('button', { name: '开始智能巡检', exact: true }).click()
    await page.getByText('请填写地点并选择巡检图片', { exact: true }).waitFor({ state: 'visible', timeout: 10_000 })

    await goto(page, '/reviews')
    await page.locator('.review-list article').first().waitFor({ state: 'visible', timeout: 20_000 })
    const reviewButton = page.getByRole('button', { name: '进入复核', exact: true }).first()
    assert(await reviewButton.count() === 1, 'real review entry is missing')
    {
      await reviewButton.click()
      await page.waitForURL(/\/inspection\/[0-9a-f-]{36}$/, { timeout: 30_000 })
      await page.getByText('AI Agent 执行轨迹', { exact: true }).waitFor({ state: 'visible', timeout: 20_000 })
      await page.locator('.trace-item').first().waitFor({ state: 'visible', timeout: 20_000 })
      assert(await page.locator('.trace-item').count() >= 4, 'inspection detail has too few trace steps')
    }

    await goto(page, '/settings')
    await page.getByText('高德地图 Web 服务', { exact: true }).waitFor({ state: 'visible' })
    await page.getByText('DeepSeek 风险研判', { exact: true }).waitFor({ state: 'visible' })
    await page.getByText('deepseek-v4-flash', { exact: true }).first().waitFor({ state: 'visible' })
  })

  await desktop.close()

  const reference = await browser.newContext({ viewport: { width: 1680, height: 945 }, locale: 'zh-CN' })
  const referencePage = await reference.newPage()
  observePage(referencePage, 'reference-1680x945')
  await runCase('六张参考图同尺寸首屏与真实数据边界', async () => {
    const routes = [
      ['/dashboard', '风险事件队列', 'dashboard-reference-1680x945.png'],
      ['/analytics', '巡检数据分析', 'analytics-reference-1680x945.png'],
      ['/inspection/new', '创建现场巡检', 'new-inspection-reference-1680x945.png'],
      ['/knowledge', '校园交通安全知识库', 'knowledge-reference-1680x945.png'],
      ['/settings', '服务与访问配置', 'settings-reference-1680x945.png'],
      ['/reviews', '人工复核队列', 'reviews-reference-1680x945.png'],
    ]
    for (const [route, marker, screenshot] of routes) {
      await goto(referencePage, route)
      await referencePage.getByText(marker, { exact: false }).first().waitFor({ state: 'visible', timeout: 30_000 })
      await referencePage.waitForTimeout(800)
      assert(await referencePage.getByText(/演示数据|演示态势|演示队列|演示知识/).count() === 0, `${route} exposes synthetic data`)
      const overflow = await referencePage.evaluate(() => document.documentElement.scrollWidth - innerWidth)
      assert(overflow <= 1, `${route} overflows by ${overflow}px at reference viewport`)
      await referencePage.screenshot({ path: path.join(outputDir, screenshot) })
    }

    await goto(referencePage, '/inspection/new')
    await referencePage.locator('label.el-radio-button').filter({ hasText: '视频轨迹分析' }).click()
    await referencePage.locator('.upload-zone input[accept^="video/"]').waitFor({ state: 'attached' })
    await referencePage.screenshot({ path: path.join(outputDir, 'video-mode-reference-1680x945.png') })

    await goto(referencePage, '/reviews')
    await referencePage.getByRole('button', { name: '进入复核', exact: true }).first().click()
    await referencePage.waitForURL(/\/inspection\/[0-9a-f-]{36}$/, { timeout: 30_000 })
    await referencePage.getByText('AI Agent 执行轨迹', { exact: true }).waitFor({ state: 'visible', timeout: 20_000 })
    await referencePage.screenshot({ path: path.join(outputDir, 'review-detail-reference-1680x945.png') })
  })
  await reference.close()

  const wide = await browser.newContext({ viewport: { width: 2353, height: 1156 }, locale: 'zh-CN' })
  const widePage = await wide.newPage()
  observePage(widePage, 'wide-2353x1156')
  await runCase('超宽屏巡检排版与真实检测复核页', async () => {
    await goto(widePage, '/inspection/new')
    await widePage.getByRole('heading', { name: '创建现场巡检', exact: true }).waitFor({ state: 'visible', timeout: 20_000 })
    await widePage.waitForTimeout(800)
    const creationLayout = await widePage.evaluate(() => {
      const form = document.querySelector('.two-column-form')?.getBoundingClientRect()
      const recent = document.querySelector('.recent-inspections-panel')?.getBoundingClientRect()
      const signature = document.querySelector('.sidebar-campus-signature')?.getBoundingClientRect()
      const signatureImage = document.querySelector('.sidebar-campus-signature img')
      return {
        gap: form && recent ? Math.round(recent.top - form.bottom) : Number.POSITIVE_INFINITY,
        recentWidth: recent?.width || 0,
        signatureVisible: Boolean(signature && signature.width > 0 && signature.height > 0),
        signatureLoaded: signatureImage instanceof HTMLImageElement && signatureImage.complete && signatureImage.naturalWidth > 0,
        overflow: document.documentElement.scrollWidth - innerWidth,
      }
    })
    assert(creationLayout.gap >= 0 && creationLayout.gap <= 20, `recent tasks gap is too large: ${JSON.stringify(creationLayout)}`)
    assert(creationLayout.recentWidth >= 1200, `recent tasks does not follow the primary work area: ${JSON.stringify(creationLayout)}`)
    assert(creationLayout.signatureVisible && creationLayout.signatureLoaded, `campus sidebar signature is missing: ${JSON.stringify(creationLayout)}`)
    assert(creationLayout.overflow <= 1, `new inspection wide viewport overflows: ${JSON.stringify(creationLayout)}`)
    await widePage.screenshot({ path: path.join(outputDir, 'new-inspection-wide-2353x1156.png'), fullPage: true })

    const inspectionsResponse = await wide.request.get(`${baseUrl}/api/v1/inspections?page_size=100`)
    assert(inspectionsResponse.status() === 200, `inspections returned ${inspectionsResponse.status()}`)
    const inspections = await inspectionsResponse.json()
    let detectedTask
    for (const item of inspections.items || []) {
      const detailResponse = await wide.request.get(`${baseUrl}/api/v1/inspections/${item.id}`)
      if (detailResponse.status() !== 200) continue
      const detail = await detailResponse.json()
      if (detail.task_no === 'AX-20260910-B01B59') { detectedTask = detail; break }
      if (!detectedTask && (detail.detections || []).length) detectedTask = detail
    }
    assert(detectedTask && detectedTask.detections.length > 0, 'no persisted inspection with real detections is available')
    await goto(widePage, `/inspection/${detectedTask.id}`)
    await widePage.getByText('双模型视觉检测', { exact: true }).waitFor({ state: 'visible', timeout: 20_000 })
    await widePage.locator('.trace-item').first().waitFor({ state: 'visible', timeout: 20_000 })
    const reviewLayout = await widePage.evaluate(() => ({
      detections: document.querySelectorAll('.el-table__body-wrapper tbody tr').length,
      riskInRightColumn: Boolean(document.querySelector('.detail-side-stack > .risk-summary')),
      metadataCells: document.querySelectorAll('.task-meta-strip > div').length,
      evidenceGap: (() => {
        const visual = document.querySelector('.detail-main-stack > .visual-card')?.getBoundingClientRect()
        const evidence = document.querySelector('.detail-main-stack > .review-evidence-grid')?.getBoundingClientRect()
        return visual && evidence ? Math.round(evidence.top - visual.bottom) : Number.POSITIVE_INFINITY
      })(),
      statAccents: [...document.querySelectorAll('.vision-stat-grid > div')]
        .map(node => getComputedStyle(node).boxShadow),
      overflow: document.documentElement.scrollWidth - innerWidth,
    }))
    assert(reviewLayout.detections > 0, `detected-task table is empty: ${JSON.stringify(reviewLayout)}`)
    assert(reviewLayout.riskInRightColumn, `risk assessment is not in the right rail: ${JSON.stringify(reviewLayout)}`)
    assert(reviewLayout.metadataCells === 6, `review metadata strip is incomplete: ${JSON.stringify(reviewLayout)}`)
    assert(reviewLayout.evidenceGap >= 0 && reviewLayout.evidenceGap <= 20, `review evidence leaves an internal blank strip: ${JSON.stringify(reviewLayout)}`)
    assert(new Set(reviewLayout.statAccents).size >= 4, `review vision statistics lost semantic colors: ${JSON.stringify(reviewLayout)}`)
    assert(reviewLayout.overflow <= 1, `review detail wide viewport overflows: ${JSON.stringify(reviewLayout)}`)
    await widePage.screenshot({ path: path.join(outputDir, 'review-detail-detected-wide-2353x1156.png'), fullPage: true })
  })
  await wide.close()

  const userScreen = await browser.newContext({ viewport: { width: 2560, height: 1440 }, locale: 'zh-CN' })
  const userPage = await userScreen.newPage()
  observePage(userPage, 'user-2560x1440')
  await runCase('用户宽屏五页留白、千问与真实档案分页', async () => {
    const health = await (await userScreen.request.get(`${baseUrl}/api/v1/health`)).json()
    assert(health.services.vision_llm?.model, 'frontend proxy is serving an old backend without VLM health')
    for (const [route, name] of [['/dashboard', 'dashboard'], ['/inspection/new', 'new-inspection'], ['/inspections', 'archive'], ['/knowledge', 'knowledge'], ['/settings', 'settings']]) {
      await goto(userPage, route)
      await userPage.waitForTimeout(900)
      assert(await userPage.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${route} overflows user viewport`)
      if (route === '/inspection/new' || route === '/settings') {
        await userPage.locator('.model-evidence-panel').waitFor({ state: 'visible' })
        assert((await userPage.locator('.model-evidence-panel').innerText()).includes(health.services.vision_llm.model), 'VLM model name does not match live health')
      }
      if (route === '/knowledge') {
        await userPage.locator('.document-list article').first().click()
        await userPage.getByPlaceholder('例如：停车场标志被遮挡如何处置？').fill('停车场标志被遮挡如何处置')
        await userPage.getByRole('button', { name: '检索', exact: true }).click()
        await userPage.locator('.hit-list article').first().waitFor({ state: 'visible' })
        const layout = await userPage.evaluate(() => ({ align: getComputedStyle(document.querySelector('.knowledge-workbench')).alignItems, scroll: getComputedStyle(document.querySelector('.hit-list')).overflowY }))
        assert(layout.align === 'start' && layout.scroll === 'auto', 'knowledge cards stretch to the full search-result height')
      }
      if (route === '/inspections') {
        assert(await userPage.locator('.archive-table .el-table__body tbody tr').count() <= 10, 'archive page exceeds ten rows')
        const next = userPage.locator('.archive-list-footer .btn-next')
        if (!await next.isDisabled()) {
          const firstPage = await userPage.locator('.archive-table').innerText()
          await next.click()
          assert(await userPage.locator('.archive-table').innerText() !== firstPage, 'pagination did not change real records')
          await userPage.locator('.archive-list-footer .btn-prev').click()
          assert(await userPage.locator('.archive-table').innerText() === firstPage, 'returning to page one did not restore records')
        }
      }
      await userPage.screenshot({ path: path.join(outputDir, `${name}-user-2560x1440.png`), fullPage: true })
    }
  })
  await userScreen.close()

  const continuityContext = await browser.newContext({ viewport: { width: 2560, height: 1440 }, locale: 'zh-CN' })
  const continuityPage = await continuityContext.newPage()
  observePage(continuityPage, 'continuity')
  await runCase('完整校名、知识库独立列与整改建议可读性', async () => {
    await goto(continuityPage, '/knowledge')
    await continuityPage.locator('.document-list article').first().waitFor({ state: 'visible' })
    assert(await continuityPage.locator('.brand-copy span').innerText() === '四川现代职业学院', 'sidebar school name is abbreviated')
    const checkColumnGaps = async () => {
      const gaps = await continuityPage.locator('.knowledge-column').evaluateAll(columns => columns.map(column => {
        const cards = [...column.children].filter(node => node.classList.contains('content-card'))
        return cards.length === 2 ? cards[1].getBoundingClientRect().top - cards[0].getBoundingClientRect().bottom : Infinity
      }))
      assert(gaps.length === 3 && gaps.every(gap => gap >= 0 && gap <= 16), `knowledge column gaps: ${JSON.stringify(gaps)}`)
    }
    await checkColumnGaps()
    await continuityPage.screenshot({ path: path.join(outputDir, 'knowledge-continuity-empty-2560x1440.png'), fullPage: true })
    const secondDocument = continuityPage.locator('.document-list article').nth(1)
    const selectedName = await secondDocument.locator('strong').innerText()
    await secondDocument.focus()
    await continuityPage.keyboard.press('Enter')
    assert(await continuityPage.locator('.selected-doc-hero strong').innerText() === selectedName, 'document selection no longer updates metadata')
    const searchResponse = continuityPage.waitForResponse(response => response.url().endsWith('/api/v1/knowledge/search') && response.request().method() === 'POST')
    await continuityPage.locator('.search-empty-state button').first().click()
    const response = await searchResponse
    assert(response.status() === 200, `knowledge search returned ${response.status()}`)
    const searchBody = await response.json()
    await continuityPage.locator('.hit-list article').first().waitFor({ state: 'visible' })
    assert(await continuityPage.locator('.hit-list article').count() === searchBody.hits.length, 'rendered hits differ from real search response')
    await checkColumnGaps()
    await continuityPage.screenshot({ path: path.join(outputDir, 'knowledge-continuity-hits-2560x1440.png'), fullPage: true })

    const listResponse = await continuityContext.request.get(`${baseUrl}/api/v1/inspections?page_size=100`)
    assert(listResponse.status() === 200, 'inspection list failed')
    const list = await listResponse.json()
    let taskWithRecommendations
    for (const item of list.items || []) {
      const detailResponse = await continuityContext.request.get(`${baseUrl}/api/v1/inspections/${item.id}`)
      if (detailResponse.status() !== 200) continue
      const detail = await detailResponse.json()
      if (detail.risk_result?.recommendations?.length && detail.detections?.length) {
        taskWithRecommendations = detail
        break
      }
    }
    assert(taskWithRecommendations, 'no real task with recommendations available')
    await goto(continuityPage, `/inspection/${taskWithRecommendations.id}`)
    await continuityPage.locator('.recommendation-card li').first().waitFor({ state: 'visible' })
    const renderedRecommendations = await continuityPage.locator('.recommendation-card li span').allTextContents()
    assert(JSON.stringify(renderedRecommendations) === JSON.stringify(taskWithRecommendations.risk_result.recommendations), 'recommendations differ from backend data')
    const recommendationMetrics = await continuityPage.evaluate(() => {
      const trace = document.querySelector('.detail-action-stack > .review-trace-card').getBoundingClientRect()
      const recommendations = document.querySelector('.detail-action-stack > .recommendation-card').getBoundingClientRect()
      const list = document.querySelector('.recommendation-card .recommendations')
      return { gap: recommendations.top - trace.bottom, widthDifference: Math.abs(recommendations.width - trace.width), fontSize: parseFloat(getComputedStyle(list).fontSize), overflow: document.documentElement.scrollWidth - innerWidth }
    })
    assert(recommendationMetrics.gap >= 0 && recommendationMetrics.gap <= 16, `recommendations do not follow trace: ${JSON.stringify(recommendationMetrics)}`)
    assert(recommendationMetrics.widthDifference <= 1 && recommendationMetrics.fontSize >= 16 && recommendationMetrics.overflow <= 1, `recommendation readability: ${JSON.stringify(recommendationMetrics)}`)
    await continuityPage.screenshot({ path: path.join(outputDir, 'detail-continuity-2560x1440.png'), fullPage: true })
    for (const route of ['/knowledge', `/inspection/${taskWithRecommendations.id}`]) {
      await continuityPage.setViewportSize({ width: 390, height: 844 })
      await goto(continuityPage, route)
      await continuityPage.waitForTimeout(800)
      assert(await continuityPage.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${route} mobile layout overflows`)
      if (route.startsWith('/inspection/')) {
        const actionsVisible = await continuityPage.locator('.task-actions .el-button').evaluateAll(buttons => buttons.every(button => {
          const rect = button.getBoundingClientRect()
          return rect.left >= 0 && rect.right <= innerWidth + 1
        }))
        assert(actionsVisible, 'mobile detail action buttons are clipped')
      }
      await continuityPage.screenshot({ path: path.join(outputDir, `${route === '/knowledge' ? 'knowledge' : 'detail'}-continuity-mobile-390x844.png`), fullPage: true })
    }
  })
  await continuityContext.close()

  const identityContext = await browser.newContext({ viewport: { width: 2560, height: 1392 }, locale: 'zh-CN' })
  const identityPage = await identityContext.newPage()
  observePage(identityPage, 'identity')
  await runCase('官方校徽、校训、复核排版与键盘入口', async () => {
    await goto(identityPage, '/reviews')
    await identityPage.locator('.review-list article').first().waitFor({ state: 'visible' })
    const metrics = await identityPage.evaluate(async () => {
      await Promise.all([...document.querySelectorAll('.official-school-mark img')].map(img => img.decode()))
      const style = selector => getComputedStyle(document.querySelector(selector))
      return {
        crests: document.querySelectorAll('.official-school-mark img').length,
        sealWidth: document.querySelector('.school-seal').getBoundingClientRect().width,
        mottoSize: parseFloat(style('.sidebar-campus-signature p').fontSize),
        titleSize: parseFloat(style('.review-task-copy > strong').fontSize),
        reasonSize: parseFloat(style('.review-reasons span').fontSize),
        buttonHeight: document.querySelector('.review-list .el-button').getBoundingClientRect().height,
        documentWidth: document.documentElement.scrollWidth,
      }
    })
    assert(metrics.crests === 2 && metrics.sealWidth >= 36, `crest dimensions: ${JSON.stringify(metrics)}`)
    assert(metrics.mottoSize >= 13 && metrics.titleSize >= 15 && metrics.reasonSize >= 12, `readability: ${JSON.stringify(metrics)}`)
    assert(metrics.buttonHeight >= 40 && metrics.documentWidth <= 2561, `layout: ${JSON.stringify(metrics)}`)
    const item = identityPage.locator('.review-list article').first()
    assert(await item.locator('.review-evidence-summary .risk-badge').count() === 1, 'risk label is missing')
    assert(!/T\d{2}:\d{2}:\d{2}\.\d{3,}/.test(await item.innerText()), 'raw fractional timestamp remains visible')
    await identityPage.screenshot({ path: path.join(outputDir, 'reviews-identity-2560x1392.png'), fullPage: true })
    const button = item.getByRole('button', { name: '进入复核', exact: true })
    await button.focus()
    await identityPage.keyboard.press('Enter')
    await identityPage.waitForURL(/\/inspection\/[0-9a-f-]{36}$/)
    await identityPage.locator('.sidebar-collapse').click()
    assert(await identityPage.locator('.sidebar-campus-signature').isVisible() === false, 'collapsed sidebar still shows motto')
  })
  await identityContext.close()

  const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: 'zh-CN' })
  const mobilePage = await mobile.newPage()
  observePage(mobilePage, 'mobile')
  await runCase('移动端总览与分析页无横向溢出', async () => {
    for (const [route, marker, screenshot] of [
      ['/dashboard', '风险事件队列', 'dashboard-mobile-390x844.png'],
      ['/analytics', '巡检数据分析', 'analytics-mobile-390x844.png'],
      ['/inspection/new', '创建现场巡检', 'new-inspection-mobile-390x844.png'],
      ['/reviews', '人工复核队列', 'reviews-mobile-390x844.png'],
    ]) {
      await goto(mobilePage, route)
      await mobilePage.getByText(marker, { exact: false }).first().waitFor({ state: 'visible', timeout: 30_000 })
      await mobilePage.waitForTimeout(800)
      const metrics = await mobilePage.evaluate(() => ({
        viewport: innerWidth,
        documentWidth: document.documentElement.scrollWidth,
        bodyWidth: document.body.scrollWidth,
        navItems: document.querySelectorAll('nav.primary-nav a').length,
      }))
      assert(metrics.documentWidth <= metrics.viewport + 1, `${route} mobile document overflow: ${JSON.stringify(metrics)}`)
      assert(metrics.bodyWidth <= metrics.viewport + 1, `${route} mobile body overflow: ${JSON.stringify(metrics)}`)
      assert(metrics.navItems === 7, `${route} mobile navigation does not have seven entries`)
      await mobilePage.screenshot({ path: path.join(outputDir, screenshot), fullPage: true })
    }
  })

  await mobile.close()
  await browser.close()

  // Abort failures are evidence too. Do not silently exclude failed API/assets.
  const ignoredRequestFailures = []
  const unexpectedRequestFailures = signals.failedRequests
  const unexpectedSignals = [...signals.pageErrors, ...signals.consoleErrors, ...unexpectedRequestFailures, ...signals.httpErrors]
  cases.push({
    name: '浏览器无非预期页面、控制台或请求错误',
    status: unexpectedSignals.length ? 'failed' : 'passed',
    duration_ms: 0,
    ...(unexpectedSignals.length ? { error: unexpectedSignals.join('; ') } : {}),
  })

  const report = {
    base_url: baseUrl,
    generated_at: new Date().toISOString(),
    summary: {
      total: cases.length,
      passed: cases.filter(item => item.status === 'passed').length,
      failed: cases.filter(item => item.status === 'failed').length,
    },
    cases,
    browser_signals: signals,
    ignored_expected_signals: {
      navigation_aborts: ignoredRequestFailures.length,
    },
  }
  fs.writeFileSync(path.join(outputDir, 'visual-acceptance-report.json'), JSON.stringify(report, null, 2), 'utf8')
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`)
  process.exitCode = report.summary.failed ? 1 : 0
}

main().catch(error => {
  process.stderr.write(`${error.stack || error}\n`)
  process.exitCode = 1
})
