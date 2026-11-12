// 锦囊 SafeKeep 本地静态服务器（零依赖，仅用 Node 内置模块）
// 用法：node serve.cjs [port]   默认 8123，根目录为本文件所在目录
// 为什么需要它：file:// 打开时部分浏览器不提供 Web Crypto；localhost 是安全上下文，
// crypto.subtle 一定可用，锦囊的加密功能才能跑。
const http = require('http');
const fs = require('fs');
const path = require('path');

const root = __dirname;
const port = parseInt(process.argv[2], 10) || 8123;
const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.cjs': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
  '.txt': 'text/plain; charset=utf-8',
  '.md': 'text/plain; charset=utf-8'
};

http.createServer((req, res) => {
  let p = decodeURIComponent((req.url || '/').split('?')[0]);
  if (p === '/') p = '/index.html';
  const file = path.join(root, path.normalize(p).replace(/^([/\\])+/, ''));
  if (!file.startsWith(root)) { res.writeHead(403); return res.end('forbidden'); }
  fs.readFile(file, (err, buf) => {
    if (err) { res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' }); return res.end('404 ' + p); }
    res.writeHead(200, {
      'Content-Type': TYPES[path.extname(file).toLowerCase()] || 'application/octet-stream',
      'Cache-Control': 'no-store'
    });
    res.end(buf);
  });
}).listen(port, '127.0.0.1', () => {
  console.log('锦囊 SafeKeep 本地服务已启动：http://127.0.0.1:' + port + '/index.html');
  console.log('工具说明：                    http://127.0.0.1:' + port + '/README.md');
  console.log('按 Ctrl+C 停止服务。仅监听 127.0.0.1，不对外暴露。');
});
