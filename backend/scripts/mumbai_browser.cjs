/* Local-only browser acceptance using the actual Expo apps and real Mumbai JWTs.
 * The fixture launcher owns all data and cleanup; never print the private session file.
 */
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('D:/salon/salon-QR-Walking-Web/walking-customer-web/node_modules/playwright-core');
const root = path.resolve(__dirname, '../.artifacts/mumbai-refresh');
const data = JSON.parse(fs.readFileSync(path.join(root, 'synthetic-sessions.json'), 'utf8'));
if (data.project !== 'wqjlgpnbiapcrlkxumcp') throw Error('Wrong synthetic target');
const checks = [], sockets = [], errors = [];
const api = 'http://127.0.0.1:8056';
const allowed = new Set(['127.0.0.1', 'localhost', 'wqjlgpnbiapcrlkxumcp.supabase.co']);
const record = name => checks.push({check: name, status: 'passed'});

(async () => {
 const browser = await chromium.launch({headless: true});
 try {
  const contexts = {};
  for (const role of ['customer','owner']) {
   const context = await browser.newContext({serviceWorkers:'block', viewport:{width:1100,height:900}, geolocation:{latitude:19.076,longitude:72.8777}, permissions:['geolocation']});
   await context.route('**/*', route => allowed.has(new URL(route.request().url()).hostname) ? route.continue() : route.abort());
   await context.addInitScript(({session, role, ref}) => {
    localStorage.setItem('sb-'+ref+'-auth-token', JSON.stringify(session));
    if (role === 'owner') {
     localStorage.setItem('salon_owner_access_token',session.access_token);
     localStorage.setItem('salon_owner_refresh_token',session.refresh_token);
    }
   }, {session:data.sessions[role],role,ref:data.project});
   contexts[role] = context;
  }
  const customer = await contexts.customer.newPage(), owner = await contexts.owner.newPage();
  for (const page of [customer,owner]) {
   page.on('websocket', socket => { if(socket.url().includes('/realtime/')) sockets.push(socket.url().split('?')[0]); });
   page.on('pageerror', error => errors.push(error.name));
   page.setDefaultTimeout(60_000);
  }
  await Promise.all([
   customer.goto('http://localhost:8081', {waitUntil:'domcontentloaded',timeout:120_000}),
   owner.goto('http://localhost:8082/bookings', {waitUntil:'domcontentloaded',timeout:120_000})
  ]);
  await owner.getByText('Synthetic customer',{exact:false}).first().waitFor({timeout:90_000});
  record('owner_real_app_renders_customer_booking');
  await customer.getByText('Mumbai synthetic updated salon',{exact:false}).first().waitFor({timeout:90_000});
  record('customer_real_app_lists_synthetic_salon');
  const response = await contexts.owner.request.patch(api+'/v1/salons/me', {headers:data.headers.owner,data:{name:'Mumbai synthetic polling updated'}});
  if (!response.ok()) throw Error('Synthetic salon mutation failed');
  await customer.getByText('Mumbai synthetic polling updated',{exact:false}).first().waitFor({timeout:45_000});
  record('mounted_customer_salon_poll_observes_owner_mutation');
  // A real API failure must recover while the screen remains mounted.
  await customer.route('**/v1/salons?*', route => route.abort('internetdisconnected'));
  await customer.waitForTimeout(32_000);
  await customer.unroute('**/v1/salons?*');
  await customer.evaluate(() => { window.dispatchEvent(new Event('online')); document.dispatchEvent(new Event('visibilitychange')); });
  await customer.getByText('Mumbai synthetic polling updated',{exact:false}).first().waitFor({timeout:70_000});
  record('customer_network_failure_recovers_without_realtime');
  if(sockets.length) throw Error('Application Realtime channel opened');
  record('no_supabase_realtime_connection');
  await customer.screenshot({path:path.join(root,'customer-local.png')});
  await owner.screenshot({path:path.join(root,'owner-local.png')});
 } catch(error) {
  checks.push({check:'playwright_local_flow',status:'failed',error_type:error.name});
  for(const [i,context] of browser.contexts().entries()) for(const page of context.pages()) {
   await page.screenshot({path:path.join(root,`browser-failure-${i}.png`)}).catch(()=>{});
   fs.writeFileSync(path.join(root,`browser-body-${i}.txt`),await page.locator('body').innerText().catch(()=>''));
  }
 } finally {
  await browser.close();
  fs.writeFileSync(path.join(root,'browser-results.json'),JSON.stringify({checks,applicationRealtimeSockets:sockets.length,pageErrorTypes:errors},null,2));
  console.log(JSON.stringify({browserChecks:checks,applicationRealtimeSockets:sockets.length}));
 }
 process.exitCode = checks.some(c=>c.status==='failed') ? 1 : 0;
})().catch(error=>{console.log(JSON.stringify({status:'blocked',error_type:error.name}));process.exitCode=1;});
