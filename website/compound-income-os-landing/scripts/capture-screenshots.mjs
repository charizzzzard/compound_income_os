import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { chromium } from 'playwright'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const outputDir = resolve(projectRoot, 'review_screenshots')
const baseUrl = 'http://127.0.0.1:5173/'
const desktopViewport = { width: 1440, height: 1200 }
const mobileViewport = { width: 390, height: 844 }
const browserExecutableCandidates = [
  process.env.PLAYWRIGHT_EXECUTABLE_PATH,
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
].filter(Boolean)

const screenshots = [
  {
    filename: '01_desktop_hero_dashboard.png',
    label: 'Desktop Hero + compact dashboard hero',
    viewport: desktopViewport,
    mode: 'viewport',
  },
  {
    filename: '02_full_dashboard_preview.png',
    label: 'Full Dashboard Preview',
    viewport: desktopViewport,
    selector: '[data-screenshot="dashboard"]',
  },
  {
    filename: '03_mobile_header_hero.png',
    label: 'Mobile Header + Hero',
    viewport: mobileViewport,
    mode: 'viewport',
  },
  {
    filename: '04_dividend_snowball.png',
    label: 'Dividend Snowball Analysis',
    viewport: desktopViewport,
    selector: '[data-screenshot="dividend-snowball"]',
  },
  {
    filename: '05_sec_evidence_data_quality.png',
    label: 'SEC Evidence / Data Quality Gates',
    viewport: desktopViewport,
    selector: '[data-screenshot="evidence-quality"]',
  },
  {
    filename: '06_access_disclaimer.png',
    label: 'Access Cards + Disclaimer',
    viewport: desktopViewport,
    selector: '[data-screenshot="access-disclaimer"]',
    hideHeader: true,
  },
]

async function isServerReady() {
  try {
    const response = await fetch(baseUrl, { signal: AbortSignal.timeout(1000) })
    return response.ok
  } catch {
    return false
  }
}

async function waitForServer() {
  const deadline = Date.now() + 30_000
  while (Date.now() < deadline) {
    if (await isServerReady()) {
      return
    }
    await new Promise((resolveWait) => setTimeout(resolveWait, 500))
  }
  throw new Error(`Vite dev server did not become ready at ${baseUrl}`)
}

async function startServerIfNeeded() {
  if (await isServerReady()) {
    return null
  }
  const npmCommand = process.platform === 'win32' ? 'npm.cmd' : 'npm'
  const server = spawn(npmCommand, ['run', 'dev', '--', '--host', '127.0.0.1', '--port', '5173'], {
    cwd: projectRoot,
    stdio: ['ignore', 'pipe', 'pipe'],
  })
  server.stdout.on('data', (chunk) => process.stdout.write(chunk))
  server.stderr.on('data', (chunk) => process.stderr.write(chunk))
  await waitForServer()
  return server
}

async function openPage(browser, viewport) {
  const page = await browser.newPage({
    viewport,
    deviceScaleFactor: 1,
    colorScheme: 'light',
    reducedMotion: 'reduce',
  })
  await page.goto(baseUrl, { waitUntil: 'networkidle' })
  return page
}

async function screenshotViewport(browser, spec) {
  const page = await openPage(browser, spec.viewport)
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({
    path: resolve(outputDir, spec.filename),
    animations: 'disabled',
    clip: { x: 0, y: 0, width: spec.viewport.width, height: spec.viewport.height },
  })
  await page.close()
}

async function screenshotSelector(browser, spec) {
  const page = await openPage(browser, spec.viewport)
  const target = page.locator(spec.selector)
  if (spec.hideHeader) {
    await page.locator('header').evaluate((element) => {
      element.style.visibility = 'hidden'
    })
  }
  await target.scrollIntoViewIfNeeded()
  await target.screenshot({
    path: resolve(outputDir, spec.filename),
    animations: 'disabled',
  })
  await page.close()
}

async function writeReadme() {
  const timestamp = new Date().toISOString()
  const lines = [
    '# Landing Page Review Screenshots',
    '',
    `Generated: ${timestamp}`,
    '',
    'Generation command:',
    '',
    '```bash',
    'npm run screenshots',
    '```',
    '',
    `Source URL: ${baseUrl}`,
    '',
    'Viewport sizes:',
    '',
    '- Desktop: 1440x1200',
    '- Mobile: 390x844',
    '',
    'Screenshots:',
    '',
    ...screenshots.map((spec) => `- ${spec.filename}: ${spec.label}`),
    '',
    'The values shown are synthetic demo values.',
    'These screenshots are review artifacts and do not contain private portfolio data.',
    '',
  ]
  await writeFile(resolve(outputDir, 'README.md'), lines.join('\n'), 'utf8')
}

async function main() {
  await mkdir(outputDir, { recursive: true })
  const server = await startServerIfNeeded()
  const executablePath = browserExecutableCandidates.find((candidate) => existsSync(candidate))
  const browser = await chromium.launch(executablePath ? { executablePath } : undefined)
  try {
    for (const spec of screenshots) {
      if (spec.mode === 'viewport') {
        await screenshotViewport(browser, spec)
      } else {
        await screenshotSelector(browser, spec)
      }
      console.log(`captured ${spec.filename}`)
    }
    await writeReadme()
  } finally {
    await browser.close()
    if (server) {
      server.kill()
    }
  }
}

main().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
