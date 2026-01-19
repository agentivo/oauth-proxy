#!/usr/bin/env python3
"""
Creates a GitHub OAuth App for agentivo extensions.

This OAuth App is shared across all agentivo Chrome extensions.
The callback URL points to the oauth-proxy tunnel.
"""

import signal
import sys
import webbrowser
from urllib.parse import quote

def handle_sigint(_sig, _frame):
    print("\n\nCancelled.")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_sigint)

ORG = "agentivo"
APP_NAME = "Agentivo Extensions"
CALLBACK_URL = "https://oauth.neevs.io/callback"
HOMEPAGE = "https://github.com/agentivo"
DESCRIPTION = "OAuth for agentivo Chrome extensions"


def main():
    print(f"Creating GitHub OAuth App: {APP_NAME}\n")

    print("Configuration:")
    print(f"  Name:         {APP_NAME}")
    print(f"  Organization: {ORG}")
    print(f"  Homepage:     {HOMEPAGE}")
    print(f"  Callback URL: {CALLBACK_URL}")
    print(f"  Description:  {DESCRIPTION}")
    print()

    input("Press Enter to open browser...")

    # GitHub OAuth App creation URL
    github_url = (
        f"https://github.com/organizations/{ORG}/settings/applications/new?"
        f"oauth_application[name]={quote(APP_NAME)}&"
        f"oauth_application[url]={quote(HOMEPAGE)}&"
        f"oauth_application[callback_url]={quote(CALLBACK_URL)}&"
        f"oauth_application[description]={quote(DESCRIPTION)}"
    )

    webbrowser.open(github_url)

    print("\n" + "=" * 60)
    print("After creating the OAuth App, enter the credentials below:")
    print("=" * 60 + "\n")

    client_id = input("Client ID: ").strip()
    if not client_id:
        print("Error: Client ID is required")
        sys.exit(1)

    client_secret = input("Client Secret: ").strip()
    if not client_secret:
        print("Error: Client Secret is required")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Run these commands:")
    print("=" * 60 + "\n")

    # Command to update oauth-proxy secrets
    print("# 1. Add client to oauth-proxy OAUTH_CLIENTS env var:")
    print(f'#    Add to OAUTH_CLIENTS: {{"{client_id}":"{client_secret}"}}')
    print()
    print("# Or set as individual env vars (backwards compatible):")
    print(f"#    GITHUB_CLIENT_ID={client_id}")
    print(f"#    GITHUB_CLIENT_SECRET={client_secret}")
    print()

    # Command to set GitHub secret
    print("# 2. Add to GitHub secrets (if using GitHub Actions):")
    print(f"gh secret set GITHUB_CLIENT_ID --repo {ORG}/oauth-proxy --body '{client_id}'")
    print(f"gh secret set GITHUB_CLIENT_SECRET --repo {ORG}/oauth-proxy --body '{client_secret}'")
    print()

    # Instructions for extensions
    print("# 3. For extensions using this OAuth App:")
    print(f"#    Set GITHUB_OAUTH_CLIENT_ID={client_id} in extension config")


if __name__ == "__main__":
    main()
