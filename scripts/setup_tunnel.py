#!/usr/bin/env python3
"""
Setup Cloudflare Tunnel for OAuth proxy
"""

import json
import os
import sys
from pathlib import Path

# Add whatsapp-automation scripts for shared tunnel manager
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "whatsapp-automation" / "scripts"))

try:
    from cloudflare_tunnel_manager import CloudflareTunnelManager
except ImportError:
    print("Error: cloudflare_tunnel_manager.py not found.")
    print("Make sure ../whatsapp-automation/scripts/cloudflare_tunnel_manager.py exists")
    sys.exit(1)


def main():
    api_token = os.environ.get("CLOUDFLARE_API_TOKEN")
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    domain = os.environ.get("TUNNEL_DOMAIN", "neevs.io")
    subdomain = os.environ.get("TUNNEL_SUBDOMAIN", "oauth")
    port = os.environ.get("PORT", "3000")

    if not api_token or not account_id:
        # Try loading from .env
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()
            api_token = os.environ.get("CLOUDFLARE_API_TOKEN")
            account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")

    if not api_token or not account_id:
        print("Error: Set CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID")
        sys.exit(1)

    manager = CloudflareTunnelManager(api_token, account_id)
    tunnel_name = f"oauth-proxy-{subdomain}"

    print(f"Setting up tunnel: {tunnel_name}")
    print(f"Endpoint: https://{subdomain}.{domain}/callback")

    # Check if tunnel exists
    existing = manager.get_tunnel_by_name(tunnel_name)

    if existing:
        tunnel_id = existing["id"]
        print(f"Using existing tunnel: {tunnel_id}")
        # Get token for existing tunnel
        result = manager._request("GET", f"cfd_tunnel/{tunnel_id}/token")
        result_data = result.get("result", {})
        tunnel_token = result_data.get("token") if isinstance(result_data, dict) else result_data
    else:
        print("Creating new tunnel...")
        tunnel_id, tunnel_token = manager.create_tunnel(tunnel_name)
        print(f"Created tunnel: {tunnel_id}")

    # Configure route
    print("Configuring route...")
    manager.create_route(tunnel_id, subdomain, domain, f"http://localhost:{port}")

    # Setup DNS
    print("Setting up DNS...")
    zone_id = manager.get_zone_id(domain)
    manager.ensure_dns_record(zone_id, subdomain, domain, tunnel_id)

    # Save tunnel config
    tunnels_file = Path(__file__).parent.parent / "tunnel.json"
    config = {
        "tunnel_id": tunnel_id,
        "tunnel_name": tunnel_name,
        "tunnel_token": tunnel_token,
        "subdomain": subdomain,
        "domain": domain,
        "url": f"https://{subdomain}.{domain}",
        "service_url": f"http://localhost:{port}"
    }

    with open(tunnels_file, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\nTunnel configured!")
    print(f"URL: https://{subdomain}.{domain}")
    print(f"Config saved to: {tunnels_file}")
    print(f"\nAdd TUNNEL_TOKEN to GitHub secrets:")
    print(f"  gh secret set TUNNEL_TOKEN --repo agentivo/oauth-proxy --body '{tunnel_token}'")


if __name__ == "__main__":
    main()
