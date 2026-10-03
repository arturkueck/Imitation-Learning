'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),{pathToFileURL}=require('node:url');
const {chromium}=require(path.join(process.env.LEARN_NODE_DEPS,'playwright'));
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.LEARN_CHROME});
  try{
    const context=await browser.newContext({viewport:{width:1200,height:1000},colorScheme:'light'}),page=await context.newPage(),errors=[],requests=[];
    page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url());});
    await page.goto(pathToFileURL(path.join(__dirname,'index.html')).href);await page.waitForSelector('#error-chart svg');
    const screenshots=path.join(__dirname,'_qa');fs.mkdirSync(screenshots,{recursive:true});
    const set=async(id,value)=>page.locator('#'+id).evaluate((el,v)=>{el.value=v;el.dispatchEvent(new Event('input',{bubbles:true}));},String(value));
    const tabs=['error','data','coupling','chunk','diffusion','noise'];
    for(const tab of tabs){await page.locator(`[data-tab="${tab}"]`).click();await page.locator('#'+tab+' svg').first().waitFor();assert.ok(await page.locator('#'+tab).isVisible());await page.screenshot({path:path.join(screenshots,tab+'-desktop.png'),fullPage:true});}
    await page.locator('[data-tab="error"]').click();const before=await page.locator('#error-result').textContent();await set('q',.7);assert.notEqual(await page.locator('#error-result').textContent(),before);
    await page.locator('[data-tab="data"]').click();await page.locator('#dagger-round').click();assert.match(await page.locator('#round-count').textContent(),/^1 /);await page.locator('#data-reset').click();assert.match(await page.locator('#round-count').textContent(),/^0 /);
    await page.locator('[data-tab="coupling"]').click();assert.match(await page.locator('#coupling-result').textContent(),/instabiler/);await set('c',0);assert.match(await page.locator('#coupling-result').textContent(),/asymptotisch stabil/);await page.locator('#coupling-mode').selectOption('product');assert.ok(await page.locator('#d').isDisabled());await set('c',2);assert.match(await page.locator('#coupling-result').textContent(),/Am Ursprung/);await page.screenshot({path:path.join(screenshots,'product-desktop.png'),fullPage:true});
    await page.locator('[data-tab="chunk"]').click();await page.locator('#ensemble').check();assert.ok(await page.locator('#horizon').isDisabled());assert.ok(await page.locator('#m').isEnabled());await set('m',1);
    await page.locator('[data-tab="diffusion"]').click();await page.locator('#denoise-next').click();assert.equal(await page.locator('#denoise-step').inputValue(),'10');await set('denoise-step',100);assert.match(await page.locator('#diffusion-result').textContent(),/120 Samples/);await page.screenshot({path:path.join(screenshots,'diffusion-final-desktop.png'),fullPage:true});await page.locator('#sample-seed').selectOption('21');await page.locator('#denoise-reset').click();assert.equal(await page.locator('#denoise-step').inputValue(),'0');
    await page.setViewportSize({width:390,height:844});
    for(const tab of tabs){await page.locator(`[data-tab="${tab}"]`).click();await page.waitForTimeout(160);const size=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,width:innerWidth}));assert.ok(size.scroll<=size.width,`${tab}: horizontal overflow`);assert.ok(await page.locator('#'+tab+' svg').count());await page.screenshot({path:path.join(screenshots,tab+'-mobile.png'),fullPage:true});}
    await page.emulateMedia({colorScheme:'dark'});await page.locator('[data-tab="coupling"]').click();await page.screenshot({path:path.join(screenshots,'coupling-dark-mobile.png'),fullPage:true});
    assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);
    const report={checked_at:new Date().toISOString(),runtime:'Chromium via installed Chrome, headless',desktop:[1200,1000],mobile:[390,844],tabs:6,external_network_requests:requests,page_errors:errors,checks:['all six lab panels render','controls change computed results','DAgger round/reset','linear eigenvalue outcome','product mode disables d','ensemble disables execution horizon','sampler next/reset/seed','no mobile horizontal overflow','light/dark screenshots']};
    fs.writeFileSync(path.join(screenshots,'browser_validation.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
