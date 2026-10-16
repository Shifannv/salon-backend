// Local fixture browser: fetch the real API, wait for a committed mutation, refresh.
const {chromium} = require(process.env.RECOVERY_PLAYWRIGHT_MODULE || 'playwright');
const readline = require('node:readline');
const target = new URL(process.argv[2]);
if (target.hostname !== '127.0.0.1') throw Error('Loopback only');
(async () => {
  const browser = await chromium.launch({headless:true});
  try {
    const page = await browser.newPage();
    await page.route('**/*', route => new URL(route.request().url()).origin === target.origin ? route.continue() : route.abort());
    await page.goto(target.href);
    await page.waitForFunction(() => document.querySelector('#result').textContent !== 'loading');
    console.log(JSON.stringify({before: JSON.parse(await page.locator('#result').textContent())}));
    await new Promise(resolve => {
      const input = readline.createInterface({input:process.stdin});
      input.once('line', line => { input.close(); resolve(line); });
    });
    await page.reload();
    await page.waitForFunction(() => document.querySelector('#result').textContent !== 'loading');
    console.log(JSON.stringify({after: JSON.parse(await page.locator('#result').textContent())}));
  } finally { await browser.close(); }
})().then(() => process.exit(0)).catch(error => { console.error(error); process.exit(1); });
