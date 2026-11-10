// Cattura il poster in strisce esatte usando Chrome DevTools Protocol.
//
// Uso:
//   1. avvia Chromium headless con il debug remoto:
//        chromium --headless=new --no-sandbox --disable-gpu --hide-scrollbars \
//          --allow-file-access-from-files --remote-debugging-port=9333 \
//          --user-data-dir=/tmp/dsh-profile --window-size=1600,1200 \
//          "file://<repo>/docs/design/design-system.html?theme=dark"
//   2. node docs/design/build/render.js dark /tmp/slices 9333
//   3. unisci le strisce (ImageMagick o PIL): sono 3200 px di larghezza, 2x.
//
// Il clip di Page.captureScreenshot evita il limite di tile memory che
// corrompe le catture full-page molto alte.
const fs = require('node:fs');
const path = require('node:path');

const [theme, outDir, portArg] = process.argv.slice(2);
const W = 1600;
const SLICE = 2000;
const SCALE = 2;
const PORT = parseInt(portArg || '9333', 10);

if (!theme || !outDir) {
  console.error('uso: node render.js <dark|light> <cartella-uscita> [porta]');
  process.exit(1);
}

async function main() {
  let targets;
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/json/list`);
      targets = await r.json();
      if (targets.some(t => t.type === 'page' && t.webSocketDebuggerUrl)) break;
    } catch { /* il browser non è ancora in ascolto */ }
    await new Promise(r => setTimeout(r, 500));
  }
  const page = (targets || []).find(t => t.type === 'page' && t.webSocketDebuggerUrl);
  if (!page) throw new Error('nessun target page: controlla la porta o l’avvio di Chromium');

  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });

  let id = 0;
  const pending = new Map();
  ws.onmessage = ev => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      const { res, rej } = pending.get(msg.id);
      pending.delete(msg.id);
      msg.error ? rej(new Error(JSON.stringify(msg.error))) : res(msg.result);
    }
  };
  const send = (method, params = {}) => new Promise((res, rej) => {
    const mid = ++id;
    pending.set(mid, { res, rej });
    ws.send(JSON.stringify({ id: mid, method, params }));
  });

  await send('Page.enable');
  await send('Runtime.enable');
  await send('Runtime.evaluate', { expression: 'document.fonts.ready', awaitPromise: true });
  await new Promise(r => setTimeout(r, 600));

  const { cssContentSize } = await send('Page.getLayoutMetrics');
  const H = Math.ceil(cssContentSize.height);
  fs.mkdirSync(outDir, { recursive: true });

  const n = Math.ceil(H / SLICE);
  for (let i = 0; i < n; i++) {
    const y = i * SLICE;
    const h = Math.min(SLICE, H - y);
    const { data } = await send('Page.captureScreenshot', {
      format: 'png',
      captureBeyondViewport: true,
      clip: { x: 0, y, width: W, height: h, scale: SCALE },
    });
    fs.writeFileSync(path.join(outDir, `slice-${String(i).padStart(2, '0')}.png`),
      Buffer.from(data, 'base64'));
    console.log(`slice ${i + 1}/${n} (y=${y}, h=${h})`);
  }
  console.log(JSON.stringify({ theme, width: W, height: H, slices: n, scale: SCALE }));
  await send('Browser.close').catch(() => {});
  ws.close();
}

main().catch(e => { console.error('ERRORE', e); process.exit(1); });
