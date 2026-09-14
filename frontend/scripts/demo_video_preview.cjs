// Read-only source-video compatibility probe; never submits the selected file.
const fs = require('fs')
const path = require('path')
const { chromium } = require('playwright')
const media = path.resolve(__dirname, '../../校园照片/新增照片和视频/MVIMG_20260913_190642_2等91项文件/VID_20260913_185218.mp4')
const output = path.resolve(__dirname, '../output/playwright/demo-video-preview')
fs.mkdirSync(output, { recursive: true })
async function main() {
  const cases = []
  for (const [name, executablePath] of [
    ['test-headless-shell', process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE],
    ['installed-google-chrome', 'local-path/chrome.exe'],
  ]) {
    const browser = await chromium.launch({ executablePath, headless: true })
    try {
      const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
      const writes = []
      page.on('request', request => { if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(request.method())) writes.push(request.method()) })
      await page.goto('http://127.0.0.1:5173/inspection/new', { waitUntil: 'networkidle' })
      await page.getByText('视频轨迹分析', { exact: true }).click()
      await page.locator('.upload-zone input[type="file"]').setInputFiles(media)
      await page.waitForFunction("document.querySelector('.upload-zone video')?.readyState >= 2", { timeout: 30000 })
      await page.locator('.upload-zone video').evaluate(video => video.play())
      await page.waitForTimeout(1500)
      const facts = await page.locator('.upload-zone video').evaluate(video => ({ width: video.videoWidth, height: video.videoHeight, duration: video.duration, currentTime: video.currentTime, error: video.error?.code || null }))
      await page.locator('.upload-zone video').evaluate(video => video.pause())
      await page.screenshot({ path: path.join(output, `${name}.png`), fullPage: true })
      cases.push({ name, passed: facts.width > 0 && facts.height > 0 && facts.currentTime > 0 && !facts.error && !writes.length, facts, writes })
    } finally { await browser.close() }
  }
  const report = { verified_at: new Date().toISOString(), read_only: true, cases }
  fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2))
  console.log(JSON.stringify(report, null, 2))
}
main().catch(error => { console.error(error); process.exitCode = 1 })
