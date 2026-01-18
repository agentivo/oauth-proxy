interface Env {
  ALLOWED_PROVIDERS: string;
}

interface OAuthState {
  provider: string;
  extensionId: string;
  nonce?: string;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === '/health') {
      return new Response('ok');
    }

    if (url.pathname === '/callback') {
      return handleCallback(request, env);
    }

    return new Response('Not found', { status: 404 });
  },
};

async function handleCallback(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  const code = url.searchParams.get('code');
  const stateParam = url.searchParams.get('state');
  const error = url.searchParams.get('error');
  const errorDescription = url.searchParams.get('error_description');

  if (error) {
    return new Response(`OAuth error: ${error} - ${errorDescription}`, { status: 400 });
  }

  if (!code || !stateParam) {
    return new Response('Missing code or state parameter', { status: 400 });
  }

  let state: OAuthState;
  try {
    state = JSON.parse(atob(stateParam));
  } catch {
    return new Response('Invalid state parameter', { status: 400 });
  }

  if (!state.extensionId || !state.provider) {
    return new Response('Invalid state: missing extensionId or provider', { status: 400 });
  }

  const allowedProviders = env.ALLOWED_PROVIDERS.split(',');
  if (!allowedProviders.includes(state.provider)) {
    return new Response(`Provider not allowed: ${state.provider}`, { status: 400 });
  }

  // Redirect back to the Chrome extension
  const redirectUrl = new URL(`https://${state.extensionId}.chromiumapp.org/`);
  redirectUrl.searchParams.set('code', code);
  redirectUrl.searchParams.set('state', stateParam);

  return Response.redirect(redirectUrl.toString(), 302);
}
