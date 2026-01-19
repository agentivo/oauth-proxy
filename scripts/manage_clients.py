#!/usr/bin/env python3
"""
Manage OAuth clients for the oauth-proxy.

Stores client_id:secret pairs in OAUTH_CLIENTS GitHub secret.
"""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
CLIENTS_FILE = REPO_ROOT / "clients.json"


def run_cmd(cmd, check=True):
    result = subprocess.run(cmd, shell=True, cwd=REPO_ROOT, capture_output=True, text=True)
    if check and result.returncode != 0:
        return None
    return result.stdout.strip()


def load_clients():
    """Load client IDs from local tracking file."""
    if not CLIENTS_FILE.exists():
        return {}
    return json.loads(CLIENTS_FILE.read_text())


def save_clients(clients):
    """Save client IDs to local tracking file (IDs only, no secrets)."""
    # Only save IDs and names, not secrets
    tracking = {cid: clients[cid].get("name", "") for cid in clients}
    CLIENTS_FILE.write_text(json.dumps(tracking, indent=2) + "\n")


def update_github_secret(clients_with_secrets):
    """Update OAUTH_CLIENTS GitHub secret."""
    # Build the JSON with just id:secret pairs
    oauth_clients = {cid: data["secret"] for cid, data in clients_with_secrets.items()}
    json_value = json.dumps(oauth_clients)

    # Use gh CLI to set the secret
    result = run_cmd(f"gh secret set OAUTH_CLIENTS --body '{json_value}'", check=False)
    return result is not None


def main():
    if not run_cmd("which gh", check=False):
        print("Error: GitHub CLI (gh) not installed")
        sys.exit(1)

    print("OAuth Proxy - Client Manager\n")

    # Load existing client IDs
    existing = load_clients()
    if existing:
        print("Existing clients:")
        for cid, name in existing.items():
            print(f"  - {cid} ({name})")
        print()

    # Menu
    print("Options:")
    print("  1. Add new client")
    print("  2. Update all secrets (re-enter all)")
    print("  3. Remove client")
    print("  4. Exit")
    print()

    choice = input("Choice [1-4]: ").strip()

    if choice == "1":
        # Add new client
        print("\nAdd new OAuth client:")
        name = input("App name (e.g., 'Panopto AI'): ").strip()
        client_id = input("Client ID: ").strip()
        client_secret = input("Client Secret: ").strip()

        if not client_id or not client_secret:
            print("Error: Client ID and secret required")
            sys.exit(1)

        # Add to existing
        existing[client_id] = name

        # Now need secrets for ALL clients
        print("\nEnter secrets for all clients to update GitHub:")
        clients_with_secrets = {}
        for cid, cname in existing.items():
            if cid == client_id:
                clients_with_secrets[cid] = {"name": cname, "secret": client_secret}
            else:
                secret = input(f"  Secret for {cid} ({cname}): ").strip()
                if not secret:
                    print(f"Error: Secret required for {cid}")
                    sys.exit(1)
                clients_with_secrets[cid] = {"name": cname, "secret": secret}

        # Update GitHub secret
        print("\nUpdating OAUTH_CLIENTS secret...")
        if update_github_secret(clients_with_secrets):
            save_clients(clients_with_secrets)
            print("Done! Restart the GitHub Action to apply changes.")
        else:
            print("Failed to update secret. Check gh auth status.")

    elif choice == "2":
        # Update all secrets
        if not existing:
            print("No clients to update. Add a client first.")
            sys.exit(0)

        print("\nEnter secrets for all clients:")
        clients_with_secrets = {}
        for cid, name in existing.items():
            secret = input(f"  Secret for {cid} ({name}): ").strip()
            if not secret:
                print(f"Error: Secret required for {cid}")
                sys.exit(1)
            clients_with_secrets[cid] = {"name": name, "secret": secret}

        print("\nUpdating OAUTH_CLIENTS secret...")
        if update_github_secret(clients_with_secrets):
            print("Done! Restart the GitHub Action to apply changes.")
        else:
            print("Failed to update secret.")

    elif choice == "3":
        # Remove client
        if not existing:
            print("No clients to remove.")
            sys.exit(0)

        print("\nSelect client to remove:")
        clients_list = list(existing.items())
        for i, (cid, name) in enumerate(clients_list, 1):
            print(f"  {i}. {cid} ({name})")

        idx = input("Number: ").strip()
        try:
            idx = int(idx) - 1
            if 0 <= idx < len(clients_list):
                cid_to_remove = clients_list[idx][0]
                del existing[cid_to_remove]

                if existing:
                    print("\nEnter secrets for remaining clients:")
                    clients_with_secrets = {}
                    for cid, name in existing.items():
                        secret = input(f"  Secret for {cid} ({name}): ").strip()
                        clients_with_secrets[cid] = {"name": name, "secret": secret}

                    print("\nUpdating OAUTH_CLIENTS secret...")
                    if update_github_secret(clients_with_secrets):
                        save_clients(clients_with_secrets)
                        print("Done!")
                else:
                    # No clients left - set empty
                    run_cmd("gh secret set OAUTH_CLIENTS --body '{}'")
                    CLIENTS_FILE.unlink(missing_ok=True)
                    print("All clients removed.")
        except (ValueError, IndexError):
            print("Invalid selection")

    else:
        print("Bye!")


if __name__ == "__main__":
    main()
