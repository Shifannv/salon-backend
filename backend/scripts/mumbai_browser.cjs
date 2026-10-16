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
let phase = 'startup';
const api = 'http://127.0.0.1:8056';
const allowed = new Set(['127.0.0.1', 'localhost', 'wqjlgpnbiapcrlkxumcp.supabase.co']);
const record = (name, facts = {}) => {
 checks.push({check: name, status: 'passed', ...facts});
 fs.writeFileSync(path.join(root,'browser-progress.json'),JSON.stringify(checks,null,2));
};

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
   page.setDefaultTimeout(20_000);
  }
  await Promise.all([
   customer.goto('http://localhost:8081', {waitUntil:'domcontentloaded',timeout:120_000}),
   owner.goto('http://localhost:8082/bookings', {waitUntil:'domcontentloaded',timeout:120_000})
  ]);
  await owner.bringToFront();
  phase = 'owner_calendar_date';
  await owner.getByText('Choose date',{exact:true}).first().click();
  const chosenDate = new Date(data.params.date+'T12:00:00Z');
  await owner.getByTestId('bookings-calendar-day-'+data.params.date).click();
  await owner.getByTestId('bookings-calendar-confirm').click();
  await owner.getByText('Synthetic customer',{exact:false}).first().waitFor({timeout:45_000});
  record('owner_real_app_renders_customer_booking');
  await customer.bringToFront();
  phase = 'customer_service_ui';
  await customer.getByText('Mumbai synthetic updated salon',{exact:false}).first().waitFor({timeout:45_000});
  record('customer_real_app_lists_synthetic_salon');
  const response = await contexts.owner.request.patch(api+'/v1/salons/me', {headers:data.headers.owner,data:{name:'Mumbai synthetic polling updated'}});
  if (!response.ok()) throw Error('Synthetic salon mutation failed');
  const salonChangedAt = Date.now();
  await customer.getByText('Mumbai synthetic polling updated',{exact:false}).first().waitFor({timeout:45_000});
  record('mounted_customer_salon_poll_observes_owner_mutation', {visible_after_response_ms:Date.now()-salonChangedAt});
  // A real API failure must recover while the screen remains mounted.
  await customer.route('**/v1/salons?*', route => route.abort('internetdisconnected'));
  await customer.waitForTimeout(32_000);
  await customer.unroute('**/v1/salons?*');
  await customer.evaluate(() => { window.dispatchEvent(new Event('online')); document.dispatchEvent(new Event('visibilitychange')); });
  const listRetry = customer.getByText('Retry',{exact:true});
  if (await listRetry.first().isVisible().catch(()=>false)) await listRetry.first().click();
  await customer.getByLabel('View services at Mumbai synthetic polling updated',{exact:true}).first().waitFor({timeout:70_000});
  record('customer_network_failure_recovers_without_realtime');
  // Create from a second HTTP session while the owner's dated list stays mounted.
  await owner.bringToFront();
  const slots = await contexts.customer.request.get(api+'/v1/availability', {params:{staff_id:data.ids.staff,date:data.params.date,service_ids:data.ids.service}});
  const freeSlot = (await slots.json())[0];
  if (!freeSlot) throw Error('Synthetic slot missing');
  const remoteBooking = await contexts.customer.request.post(api+'/v1/bookings', {
    headers:{...data.headers.outsider,'Idempotency-Key':require('node:crypto').randomUUID()},
    data:{salon_id:data.ids.salon,staff_id:data.ids.staff,service_ids:[data.ids.service],start_datetime:freeSlot.slot_start,
      customer_name:'Synthetic remote booking',source:'app',payment_preference:'pay_at_salon'}
  });
  if (remoteBooking.status() !== 201) {
    checks.push({check:'synthetic_remote_booking_response',status:'failed',http_status:remoteBooking.status()});
    throw Error('Synthetic remote booking failed');
  }
  const bookedAt = Date.now();
  await owner.getByText('Synthetic remote booking',{exact:false}).first().waitFor({timeout:45_000});
  record('mounted_owner_poll_observes_new_customer_booking', {visible_after_response_ms:Date.now()-bookedAt});
  await customer.bringToFront();
  await customer.getByLabel('View services at Mumbai synthetic polling updated',{exact:true}).first().click();
  await customer.getByText('Synthetic refresh service',{exact:true}).first().waitFor();
  record('customer_services_render_from_fastapi');
  phase = 'customer_service_selection';
  const serviceCheckbox = customer.getByLabel(/^Synthetic refresh service,/).first();
  // React Native's animated web control exposes selection in its accessible label.
  if (!(await serviceCheckbox.getAttribute('aria-label')).endsWith('. Selected')) await serviceCheckbox.click();
  await customer.getByText(/1 service.*30 mins/).first().waitFor();
  phase = 'customer_service_continue';
  await customer.getByLabel('Continue with selected services',{exact:true}).click();
  phase = 'customer_availability_ui';
  await customer.getByText(String(chosenDate.getUTCDate()),{exact:true}).first().click();
  const customerSlots = customer.getByRole('radio').filter({hasText:/\d.*(?:AM|PM)/i});
  await customerSlots.first().waitFor({timeout:25_000});
  const paused = await contexts.owner.request.patch(api+'/v1/salons/me/settings',{headers:data.headers.owner,data:{accepting_bookings:false}});
  if (!paused.ok()) throw Error('Synthetic pause failed');
  const pausedAt = Date.now();
  await customer.getByText('No times are currently available. Please choose another date or barber.',{exact:true}).waitFor({timeout:25_000});
  if (!await customer.getByRole('button',{name:'Confirm & Continue',exact:true}).isDisabled()) throw Error('Stale customer booking control remained active');
  record('mounted_customer_availability_observes_owner_pause', {visible_after_response_ms:Date.now()-pausedAt});
  await contexts.owner.request.patch(api+'/v1/salons/me/settings',{headers:data.headers.owner,data:{accepting_bookings:true}});
  await customerSlots.first().waitFor({timeout:25_000});
  await customer.route('**/v1/availability?*', route => route.abort('internetdisconnected'));
  phase = 'customer_availability_failure';
  await customer.getByLabel('Refresh failed. Retry',{exact:true}).waitFor({timeout:25_000});
  if (!await customer.getByRole('button',{name:'Confirm & Continue',exact:true}).isDisabled()) throw Error('Failed customer availability remained actionable');
  await customer.unroute('**/v1/availability?*');
  await customer.getByLabel('Refresh failed. Retry',{exact:true}).click();
  await customerSlots.first().waitFor({timeout:25_000});
  record('customer_availability_error_fails_closed_and_manual_retry_recovers');
  phase = 'owner_availability_ui';
  // Use a short synthetic service so real late-night walk-in availability is testable.
  const shortened = await contexts.owner.request.patch(api+'/v1/salons/me/services/'+data.ids.service, {headers:data.headers.owner,data:{duration_minutes:5}});
  if (!shortened.ok()) throw Error('Synthetic service duration update failed');
  await owner.bringToFront();
  await owner.goto('http://localhost:8082/add-walkin',{waitUntil:'domcontentloaded'});
  await owner.getByRole('combobox',{name:'Select a service',exact:true}).click();
  await owner.getByRole('radio',{name:'Synthetic refresh service',exact:true}).click();
  await owner.getByLabel('Assign to Synthetic refresh staff',{exact:true}).click();
  const ownerSlots = owner.getByLabel(/^Time slot /);
  await ownerSlots.first().waitFor({timeout:25_000});
  await contexts.owner.request.patch(api+'/v1/salons/me/settings',{headers:data.headers.owner,data:{accepting_bookings:false}});
  await ownerSlots.first().waitFor({state:'detached',timeout:25_000});
  await contexts.owner.request.patch(api+'/v1/salons/me/settings',{headers:data.headers.owner,data:{accepting_bookings:true}});
  await ownerSlots.first().waitFor({timeout:25_000});
  record('mounted_owner_availability_refreshes_after_mutation');
  phase = 'owner_availability_failure';
  await owner.route('**/v1/availability?*', route => route.abort('internetdisconnected'));
  await owner.getByRole('button',{name:'Retry availability',exact:true}).waitFor({timeout:25_000});
  if(await ownerSlots.count()) throw Error('Failed owner availability remained selectable');
  await owner.unroute('**/v1/availability?*');
  await owner.getByRole('button',{name:'Retry availability',exact:true}).click();
  await ownerSlots.first().waitFor({timeout:25_000});
  record('owner_availability_error_fails_closed_and_manual_retry_recovers');
  if(sockets.length) throw Error('Application Realtime channel opened');
  record('no_supabase_realtime_connection');
  await customer.screenshot({path:path.join(root,'customer-local.png')});
  await owner.screenshot({path:path.join(root,'owner-local.png')});
 } catch(error) {
  checks.push({check:phase,status:'failed',error_type:error.name,
    message:error.message.split('\n')[0].slice(0,240)});
  for(const [i,context] of browser.contexts().entries()) for(const page of context.pages()) {
   await page.screenshot({path:path.join(root,`browser-failure-${i}.png`)}).catch(()=>{});
   fs.writeFileSync(path.join(root,`browser-body-${i}.txt`),await page.locator('body').innerText().catch(()=>''));
   const controls = await page.locator('[aria-label]').evaluateAll(elements => elements
     .filter(element => /Synthetic refresh service|Continue with selected services/.test(element.getAttribute('aria-label') || ''))
     .map(element => ({role:element.getAttribute('role'),label:element.getAttribute('aria-label'),checked:element.getAttribute('aria-checked'),disabled:element.getAttribute('aria-disabled')})));
   fs.writeFileSync(path.join(root,`browser-controls-${i}.json`),JSON.stringify(controls,null,2));
  }
 } finally {
  await browser.close();
  fs.writeFileSync(path.join(root,'browser-results.json'),JSON.stringify({checks,applicationRealtimeSockets:sockets.length,pageErrorTypes:errors},null,2));
  console.log(JSON.stringify({browserChecks:checks,applicationRealtimeSockets:sockets.length}));
 }
 process.exitCode = checks.some(c=>c.status==='failed') ? 1 : 0;
})().catch(error=>{console.log(JSON.stringify({status:'blocked',error_type:error.name}));process.exitCode=1;});
