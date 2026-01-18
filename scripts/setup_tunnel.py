#!/usr/bin/env python3
"""
Creates a Cloudflare Tunnel for the OAuth proxy.
"""

import json
import os
import sys
from pathlib import Path

# Add parent's scripts to path for shared tunnel manager
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "whatsapp-automation" / "scripts"))

try:
    from cloudflare_tunnel_manager import CloudflareTunnelManager
except ImportError:
    print("Error: cloudflare_tunnel_manager.py not found.")
    print("Make sure ../whatsapp-automation/scripts/cloudflare_tunnel_manager.py exists")
    sys.exit(1)


def main():
    # Load from environment or .env file
    api_token = os.environ.get("CLOUDFLARE_API_TOKEN")
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")

    if not api_token or not account_id:
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()
            api_token = os.environ.get("CLOUDFLARE_API_TOKEN")
            account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")

    if not api_token or not account_id:
        print("Error: CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID required")
        print("Set them in environment or create .env file")
        sys.exit(1)

    domain = os.environ.get("TUNNEL_DOMAIN", "neevs.io")
    subdomain = os.environ.get("TUNNEL_SUBDOMAIN", "oauth")

    manager = CloudflareTunnelManager(api_token, account_id)

    print(f"Setting up tunnel: {subdomain}.{domain}")

    tunnel = manager.create_or_get_tunnel(
        name=f"oauth-proxy-{subdomain}",
        subdomain=subdomain,
        domain=domain,
        service_url="http://localhost:3000"
    )

    # Save tunnel config
    config_path = Path(__file__).parent.parent / "tunnel.json"
    config_path.write_text(json.dumps(tunnel, indent=2))

    print(f"\nTunnel created!")
    print(f"  URL: https://{subdomain}.{domain}")
    print(f"  Token saved to: tunnel.json")
    print(f"\nAdd TUNNEL_TOKEN to GitHub secrets:")
    print(f"  gh secret set TUNNEL_TOKEN --repo agentivo/oauth-proxy")


if __name__ == "__main__":
    main()
