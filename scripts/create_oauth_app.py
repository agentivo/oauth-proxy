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

    print("\nAfter creating the OAuth App:")
    print("1. Copy the Client ID")
    print("2. Generate a new Client Secret")
    print("3. Store them securely for use in extensions")
    print()
    print("For extensions that use this OAuth App:")
    print("  - Add GITHUB_OAUTH_CLIENT_ID to extension config")
    print("  - The oauth-proxy handles the callback redirect")


if __name__ == "__main__":
    main()
