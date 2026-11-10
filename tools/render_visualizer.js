#!/usr/bin/env node
/*
 * Render wraps on the legacy Model Y with the Tesla Wrap Gallery visualizer
 * (https://teslawrapgallery.com/visualizer/), which shows a wrap on a 3D model
 * that carries Tesla's own wrap UVs - the closest thing to the car's screen.
 *
 *   node tools/render_visualizer.js <out-dir> <wrap.png> [more.png ...]
 *
 * Writes <out-dir>/<wrap name>_<view>.png for the views in VIEWS (override with
 * VIEWS=left,front,...).  Needs Playwright with Chromium and network access to
 * teslawrapgallery.com.  Uses HTTPS_PROXY when it is set.
 */
const { chromium } = require('playwright');
const path = require('path');

const PAGE = 'https://teslawrapgallery.com/model-y-classic-wraps/';
const ALL_VIEWS = ['left', 'right', 'front', 'rear', 'top', 'fl', 'fr', 'rl', 'rr'];

(async () => {
  const [outDir, ...wraps] = process.argv.slice(2);
  if (!outDir || !wraps.length) { console.error('usage: render_visualizer.js <out-dir> <wrap.png>...'); process.exit(2); }
  const want = process.env.VIEWS ? process.env.VIEWS.split(',') : ALL_VIEWS;
  const browser = await chromium.launch({
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
    proxy: process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined,
  });
  const page = await browser.newPage({ viewport: { width: 1700, height: 1000 }, deviceScaleFactor: 2 });
  await page.route(/clarity\.ms|cloudflareinsights|fonts\.g/, r => r.abort());      // analytics and web fonts are not needed
  await page.goto(PAGE, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForFunction(() => window.app && window.app.model && window.app.wrapMeshes && window.app.wrapMeshes.length > 0, null, { timeout: 90000 });
  await page.waitForTimeout(2500);
  // hide the site's floating button bar so it does not cover the car
  await page.addStyleTag({ content: '.viewer-controls { visibility: hidden !important; }' });
  const box = await page.evaluate(() => {
    const app = window.app; app.model.updateMatrixWorld(true);
    const min = [1e9, 1e9, 1e9], max = [-1e9, -1e9, -1e9];
    for (const m of app.wrapMeshes) {
      const p = m.geometry.attributes.position, e = m.matrixWorld.elements;
      for (let i = 0; i < p.count; i++) {
        const x = p.getX(i), y = p.getY(i), z = p.getZ(i);
        const w = [e[0]*x+e[4]*y+e[8]*z+e[12], e[1]*x+e[5]*y+e[9]*z+e[13], e[2]*x+e[6]*y+e[10]*z+e[14]];
        for (let k = 0; k < 3; k++) { if (w[k] < min[k]) min[k] = w[k]; if (w[k] > max[k]) max[k] = w[k]; }
      }
    }
    return { min, max };
  });
  const c = box.min.map((v, i) => (v + box.max[i]) / 2);
  const L = Math.max(...box.min.map((v, i) => box.max[i] - v));
  const D = 1.28 * L, up = 0.02 * L;           // +x is the car's left, +z its nose
  const cams = {
    left: [c[0] + D, c[1] + up, c[2]], right: [c[0] - D, c[1] + up, c[2]],
    front: [c[0], c[1] + 0.12 * L, c[2] + 0.8 * L], rear: [c[0], c[1] + 0.12 * L, c[2] - 0.8 * L],
    top: [c[0], c[1] + 1.5 * L, c[2] + 0.001],
    fl: [c[0] + 0.85 * L, c[1] + 0.5 * L, c[2] + 0.95 * L], fr: [c[0] - 0.85 * L, c[1] + 0.5 * L, c[2] + 0.95 * L],
    rl: [c[0] + 0.85 * L, c[1] + 0.5 * L, c[2] - 0.95 * L], rr: [c[0] - 0.85 * L, c[1] + 0.5 * L, c[2] - 0.95 * L],
  };
  const canvas = await page.$('canvas');
  for (const wrap of wraps) {
    await page.setInputFiles('#wrap-upload', wrap);
    await page.waitForTimeout(3500);
    const name = path.basename(wrap, '.png');
    for (const v of want) {
      await page.evaluate(([pos, c]) => {
        const app = window.app; app.controls.target.set(c[0], c[1], c[2]); app.camera.position.set(pos[0], pos[1], pos[2]);
        app.camera.lookAt(c[0], c[1], c[2]); app.controls.update();
      }, [cams[v], c]);
      await page.waitForTimeout(700);
      await canvas.screenshot({ path: path.join(outDir, `${name}_${v}.png`) });
    }
    console.log('rendered', name, want.join(','));
  }
  await browser.close();
})().catch(e => { console.error('render failed:', e.message || e); process.exit(1); });
