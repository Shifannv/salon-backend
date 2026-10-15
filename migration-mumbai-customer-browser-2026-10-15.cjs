// Read-only browser evidence. No credentials, API calls, or bookings.
const { chromium } = require('D:/salon/salon-QR-Walking-Web/walking-customer-web/node_modules/playwright-core');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const origin = 'https://salon-customer-webpage.vercel.app';
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, serviceWorkers: 'block' });
  const blocked = [];
  await context.route('**/*', async route => {
    const request = route.request();
    const url = new URL(request.url());
    const staticOrDocument = url.origin === origin && request.method() === 'GET' &&
      (['/s', '/'].includes(url.pathname) || url.pathname.startsWith('/_next/static/') ||
       /\.(png|jpg|jpeg|svg|webp|ico|woff2?)$/.test(url.pathname));
    if (staticOrDocument && !['xhr', 'fetch', 'eventsource', 'websocket'].includes(request.resourceType())) {
      await route.continue();
    } else {
      blocked.push({ origin: url.origin, pathname: url.pathname, type: request.resourceType() });
      await route.abort('blockedbyclient');
    }
  });
  const page = await context.newPage();
  const results = [];
  try {
    for (const pathname of ['/s', '/']) {
      const response = await page.goto(origin + pathname, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.locator('body').waitFor();
      const item = { pathname, status: response.status(), title: await page.title(),
        visibleText: (await page.locator('body').innerText()).slice(0, 3500),
        links: await page.locator('a[href]').evaluateAll(elements => elements.map(e => ({ text: e.textContent.trim(), href: new URL(e.href).pathname }))) };
      await page.screenshot({ path: path.join(__dirname, pathname === '/s' ? 'migration-mumbai-customer-s-2026-10-15.png' : 'migration-mumbai-customer-root-2026-10-15.png'), fullPage: true });
      results.push(item);
    }
    const evidence = { target: origin, mode: 'Read-only; browser API and cross-origin requests blocked', results, blockedRequests: blocked };
    fs.writeFileSync(path.join(__dirname, 'migration-mumbai-customer-browser-2026-10-15.json'), JSON.stringify(evidence, null, 2));
    console.log(JSON.stringify(evidence, null, 2));
  } finally {
    await context.close();
    await browser.close();
  }
})().catch(error => { console.error(JSON.stringify({ status: 'failed', errorType: error.name, message: error.message })); process.exitCode = 1; });
