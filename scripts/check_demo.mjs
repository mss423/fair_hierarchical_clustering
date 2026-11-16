// Optional UI verification: npm install --no-save playwright, then node this file.
import assert from 'node:assert/strict';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import fs from 'node:fs/promises';
const {chromium} = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const browser = await chromium.launch({
  headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE || undefined,
});
try {
  const errors = [];
  const page = await browser.newPage({viewport: {width: 1440, height: 1050}});
  page.on('pageerror', e => errors.push(e.message));
  const requests = [];
  page.on('request', request => requests.push(request.url()));
  const output = process.env.QA_OUTPUT || 'docs/qa';
  await fs.mkdir(output, {recursive: true});
  await page.goto(pathToFileURL(path.resolve('docs/demo.html')).href);
  const count = Number((await page.locator('#position').textContent()).split('/')[1].trim());
  assert.equal(count, 27);
  const startCost = Number(await page.locator('#cost').textContent());
  assert.equal(await page.locator('#clusters').textContent(), '63');
  await page.getByRole('button', {name: 'Next →', exact: true}).click();
  assert.equal(await page.locator('#phase').textContent(), 'move');
  assert.ok(await page.locator('circle[stroke="#e5a52b"]').count() > 0);
  await page.getByRole('button', {name: 'Next fold', exact: true}).click();
  assert.equal(await page.locator('#phase').textContent(), 'fold');
  await page.screenshot({path: path.join(output, 'demo-fold-desktop.png'), fullPage: true});
  await page.getByRole('button', {name: 'Final tree', exact: true}).click();
  assert.equal(await page.locator('#phase').textContent(), 'finish');
  assert.equal(await page.locator('#clusters').textContent(), '5');
  assert.ok(Number(await page.locator('#cost').textContent()) >= startCost);
  await page.locator('.node').first().click();
  assert.match(await page.locator('#inspect').textContent(), /64 points/);
  await page.keyboard.press('ArrowLeft');
  assert.notEqual(await page.locator('#phase').textContent(), 'finish');
  await page.getByRole('button', {name: 'Start', exact: true}).click();
  assert.equal(await page.locator('#phase').textContent(), 'start');

  const widths = [1440, 901, 900, 768, 390, 320];
  const layoutChecks = [];
  for (const width of widths) {
    await page.setViewportSize({width, height: width <= 390 ? 844 : 1050});
    if (await page.getByRole('button', {name: 'Start', exact: true}).isEnabled()) {
      await page.getByRole('button', {name: 'Start', exact: true}).click();
    }
    for (let step = 0; step < count; step++) {
      if (step) await page.getByRole('button', {name: 'Next →', exact: true}).click();
      const layout = await page.evaluate(() => ({
        viewport: window.innerWidth,
        document: document.documentElement.scrollWidth,
        overflowingContainers: [...document.querySelectorAll('main, .controls, .stats, .stat, .layout, .card, .scroll')]
          .map(e => ({element: e.id || e.className || e.tagName, left: e.getBoundingClientRect().left,
            right: e.getBoundingClientRect().right}))
          .filter(e => e.left < 0 || e.right > window.innerWidth),
      }));
      if (layout.document > layout.viewport || layout.overflowingContainers.length) {
        await page.screenshot({path: path.join(output, `demo-overflow-${width}-step-${step + 1}.png`), fullPage: true});
      }
      assert.ok(layout.document <= layout.viewport && !layout.overflowingContainers.length,
        `Horizontal page overflow at width=${width}, step=${step + 1}: ${JSON.stringify(layout)}`);
    }
    assert.equal(await page.locator('#position').textContent(), `${count} / ${count}`);
    layoutChecks.push({width, states: count, page_overflow: false});
    if (width === 1440 || width === 390) {
      await page.screenshot({path: path.join(output,
        width === 1440 ? 'demo-final-desktop.png' : 'demo-final-mobile.png'), fullPage: true});
    }
    if (width <= 390) {
      // The wide tree must remain accessible inside its own scrolling area.
      const treeScroll = await page.locator('.scroll').evaluate(e => {
        e.scrollLeft = e.scrollWidth;
        const result = {content: e.scrollWidth, visible: e.clientWidth, position: e.scrollLeft};
        e.scrollLeft = 0;
        return result;
      });
      assert.ok(treeScroll.content > treeScroll.visible && treeScroll.position > 0,
        `Tree must scroll locally on mobile: ${JSON.stringify(treeScroll)}`);
    }
  }
  await page.getByText('What the steps mean', {exact: true}).click();
  assert.equal(await page.locator('details').getAttribute('open'), '');
  assert.deepEqual(errors, []);
  assert.ok(requests.every(url => url.startsWith('file:')));
  await fs.writeFile(path.join(output, 'browser-check.json'), JSON.stringify({
    states: count, navigation: true, highlights: true, inspector: true,
    mobile_overflow: false, local_tree_scrolling: true, layout_checks: layoutChecks,
    browser: await browser.version(), external_requests: 0, errors,
  }, null, 2) + '\n');
  console.log('All trace states, navigation, highlights, inspector, and offline/mobile checks passed.');
} finally {
  await browser.close();
}
