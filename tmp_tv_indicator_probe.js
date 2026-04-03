const path = require('path');
const { chromium } = require(path.resolve('C:/Users/anmar/.openclaw/workspace/tradingview/node_modules/playwright'));

(async () => {
  const ctx = await chromium.launchPersistentContext(path.resolve('C:/Users/anmar/.openclaw/workspace/tradingview/profile'), {
    headless: true,
    channel: 'chromium',
    viewport: { width: 1800, height: 1100 },
    args: ['--enable-gpu', '--use-angle=d3d11', '--disable-dev-shm-usage'],
  });
  for (const p of ctx.pages()) {
    try { await p.close({ runBeforeUnload: false }); } catch {}
  }

  const page = await ctx.newPage();
  await page.goto('https://www.tradingview.com/pine-screener/', { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(5000);

  try {
    const closeBtn = page.getByRole('button', { name: 'Close' }).last();
    if (await closeBtn.count()) await closeBtn.click({ force: true, timeout: 2000 });
  } catch {}
  await page.waitForTimeout(500);

  const before = (await page.locator('[data-qa-id="pine-screener-indicator-selector"]').innerText()).replace(/\s+/g, ' ').trim();
  await page.getByRole('button', { name: 'Choose indicator' }).click({ force: true });
  await page.waitForTimeout(1200);

  const item = page.locator('.background-wJ4EfuBP', { hasText: 'OC Hybrid Edge Screener v4.2' }).first();
  const itemCount = await item.count();
  if (itemCount > 0) {
    await item.click({ force: true, timeout: 10000 });
    await page.waitForTimeout(1500);
  }

  const after = (await page.locator('[data-qa-id="pine-screener-indicator-selector"]').innerText()).replace(/\s+/g, ' ').trim();
  const hasScan = await page.getByRole('button', { name: /Scan|Rescan/i }).count();
  const body = (await page.locator('body').innerText()).slice(0, 2000);

  console.log(JSON.stringify({ before, itemCount, after, hasScan, body }, null, 2));
  await ctx.close();
})();
