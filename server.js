const http = require('http');
const https = require('https');
const url = require('url');

const PORT = process.env.PORT || 3000;
const ALLOWED_PROVIDERS = (process.env.ALLOWED_PROVIDERS || 'github').split(',');

// Support multiple GitHub OAuth apps via JSON: {"client_id":"secret", ...}
// Falls back to single GITHUB_CLIENT_ID/GITHUB_CLIENT_SECRET for backwards compatibility
const GITHUB_CLIENTS = process.env.GITHUB_CLIENTS ? JSON.parse(process.env.GITHUB_CLIENTS) : {};
if (process.env.GITHUB_CLIENT_ID && process.env.GITHUB_CLIENT_SECRET) {
  GITHUB_CLIENTS[process.env.GITHUB_CLIENT_ID] = process.env.GITHUB_CLIENT_SECRET;
}

function getClientSecret(clientId) {
  return GITHUB_CLIENTS[clientId];
}

const server = http.createServer(async (req, res) => {
  const parsedUrl = url.parse(req.url, true);

  // CORS headers for extension requests
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  if (parsedUrl.pathname === '/health') {
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end('ok');
    return;
  }

  if (parsedUrl.pathname === '/config') {
    // Return public OAuth config (client_ids only, never secrets)
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      github: {
        client_ids: Object.keys(GITHUB_CLIENTS),
        authorize_url: 'https://github.com/login/oauth/authorize',
        callback_url: 'https://oauth.neevs.io/callback'
      }
    }));
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

    if (!parsedState.provider) {
      res.writeHead(400, { 'Content-Type': 'text/plain' });
      res.end('Invalid state: missing provider');
      return;
    }

    if (!ALLOWED_PROVIDERS.includes(parsedState.provider)) {
      res.writeHead(400, { 'Content-Type': 'text/plain' });
      res.end(`Provider not allowed: ${parsedState.provider}`);
      return;
    }

    // Exchange code for token immediately for web apps
    if (parsedState.redirect_url) {
      const clientId = parsedState.client_id;
      const clientSecret = getClientSecret(clientId);

      if (!clientId || !clientSecret) {
        const errorUrl = `${parsedState.redirect_url}?error=${encodeURIComponent('Unknown client_id')}`;
        res.writeHead(302, { 'Location': errorUrl });
        res.end();
        return;
      }

      try {
        const tokenResponse = await exchangeGitHubCode(code, clientId, clientSecret);
        if (tokenResponse.error) {
          const errorUrl = `${parsedState.redirect_url}?error=${encodeURIComponent(tokenResponse.error_description || tokenResponse.error)}`;
          res.writeHead(302, { 'Location': errorUrl });
          res.end();
          return;
        }
        const successUrl = `${parsedState.redirect_url}?token=${encodeURIComponent(tokenResponse.access_token)}`;
        res.writeHead(302, { 'Location': successUrl });
        res.end();
        return;
      } catch (err) {
        const errorUrl = `${parsedState.redirect_url}?error=${encodeURIComponent(err.message)}`;
        res.writeHead(302, { 'Location': errorUrl });
        res.end();
        return;
      }
    }

    // Redirect back to Chrome extension (legacy flow)
    if (!parsedState.extensionId) {
      res.writeHead(400, { 'Content-Type': 'text/plain' });
      res.end('Invalid state: missing extensionId or redirect_url');
      return;
    }
    const redirectUrl = `https://${parsedState.extensionId}.chromiumapp.org/?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`;
    res.writeHead(302, { 'Location': redirectUrl });
    res.end();
    return;
  }

  if (parsedUrl.pathname === '/exchange' && req.method === 'POST') {
    // Exchange authorization code for access token
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', async () => {
      try {
        const { code, provider, client_id } = JSON.parse(body);

        if (!code || !provider) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'Missing code or provider' }));
          return;
        }

        if (provider !== 'github') {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'Unsupported provider' }));
          return;
        }

        // Use provided client_id or fall back to first available
        const clientId = client_id || Object.keys(GITHUB_CLIENTS)[0];
        const clientSecret = getClientSecret(clientId);

        if (!clientId || !clientSecret) {
          res.writeHead(500, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'OAuth not configured for this client' }));
          return;
        }

        // Exchange code for token with GitHub
        const tokenResponse = await exchangeGitHubCode(code, clientId, clientSecret);

        if (tokenResponse.error) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: tokenResponse.error_description || tokenResponse.error }));
          return;
        }

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
          access_token: tokenResponse.access_token,
          token_type: tokenResponse.token_type,
          scope: tokenResponse.scope
        }));
      } catch (err) {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: err.message }));
      }
    });
    return;
  }

  res.writeHead(404, { 'Content-Type': 'text/plain' });
  res.end('Not found');
});

function exchangeGitHubCode(code, clientId, clientSecret) {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify({
      client_id: clientId,
      client_secret: clientSecret,
      code: code
    });

    const options = {
      hostname: 'github.com',
      port: 443,
      path: '/login/oauth/access_token',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Content-Length': Buffer.byteLength(postData)
      }
    };

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch {
          reject(new Error('Invalid response from GitHub'));
        }
      });
    });

    req.on('error', reject);
    req.write(postData);
    req.end();
  });
}

server.listen(PORT, () => {
  console.log(`OAuth proxy server running on port ${PORT}`);
  console.log(`Configured GitHub clients: ${Object.keys(GITHUB_CLIENTS).length}`);
});
