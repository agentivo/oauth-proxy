const http = require('http');
const url = require('url');

const PORT = process.env.PORT || 3000;
const ALLOWED_PROVIDERS = (process.env.ALLOWED_PROVIDERS || 'github').split(',');

const server = http.createServer((req, res) => {
  const parsedUrl = url.parse(req.url, true);

  if (parsedUrl.pathname === '/health') {
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end('ok');
    return;
  }

  if (parsedUrl.pathname === '/callback') {
    const { code, state, error, error_description } = parsedUrl.query;

    if (error) {
      res.writeHead(400, { 'Content-Type': 'text/plain' });
      res.end(`OAuth error: ${error} - ${error_description}`);
      return;
    }

    if (!code || !state) {
      res.writeHead(400, { 'Content-Type': 'text/plain' });
      res.end('Missing code or state parameter');
      return;
    }

    let parsedState;
    try {
      parsedState = JSON.parse(Buffer.from(state, 'base64').toString());
    } catch {
      res.writeHead(400, { 'Content-Type': 'text/plain' });
      res.end('Invalid state parameter');
      return;
    }

    if (!parsedState.extensionId || !parsedState.provider) {
      res.writeHead(400, { 'Content-Type': 'text/plain' });
      res.end('Invalid state: missing extensionId or provider');
      return;
    }

    if (!ALLOWED_PROVIDERS.includes(parsedState.provider)) {
      res.writeHead(400, { 'Content-Type': 'text/plain' });
      res.end(`Provider not allowed: ${parsedState.provider}`);
      return;
    }

    // Redirect back to Chrome extension
    const redirectUrl = `https://${parsedState.extensionId}.chromiumapp.org/?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`;
    res.writeHead(302, { 'Location': redirectUrl });
    res.end();
    return;
  }

  res.writeHead(404, { 'Content-Type': 'text/plain' });
  res.end('Not found');
});

server.listen(PORT, () => {
  console.log(`OAuth proxy server running on port ${PORT}`);
});
