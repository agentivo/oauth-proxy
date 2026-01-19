#!/usr/bin/env python3
"""
Manage OAuth clients for the oauth-proxy.

Each client has its own GitHub secret: OAUTH_SECRET_<client_id>
After adding/removing, update deploy.yml to pass the new secret.
"""

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent


def run_cmd(cmd, check=True):
    result = subprocess.run(cmd, shell=True, cwd=REPO_ROOT, capture_output=True, text=True)
    if check and result.returncode != 0:
        return None
    return result.stdout.strip()


def list_secrets():
    """List current OAUTH_SECRET_* secrets."""
    output = run_cmd("gh secret list", check=False)
    if not output:
        return []
    secrets = []
    for line in output.splitlines():
        name = line.split()[0]
        if name.startswith("OAUTH_SECRET_"):
            secrets.append(name.replace("OAUTH_SECRET_", ""))
    return secrets


def add_secret(client_id, client_secret):
    """Add a new OAuth client secret."""
    secret_name = f"OAUTH_SECRET_{client_id}"
    result = run_cmd(f"gh secret set {secret_name} --body '{client_secret}'", check=False)
    return result is not None


def remove_secret(client_id):
    """Remove an OAuth client secret."""
    secret_name = f"OAUTH_SECRET_{client_id}"
    result = run_cmd(f"gh secret delete {secret_name}", check=False)
    return result is not None


def main():
    if not run_cmd("which gh", check=False):
        print("Error: GitHub CLI (gh) not installed")
        sys.exit(1)

    print("OAuth Proxy - Client Manager\n")

    existing = list_secrets()
    if existing:
        print("Current clients:")
        for cid in existing:
            print(f"  - {cid}")
        print()

    print("Options:")
    print("  1. Add client")
    print("  2. Remove client")
    print("  3. Exit")
    print()

    choice = input("Choice [1-3]: ").strip()

    if choice == "1":
        print("\nAdd OAuth client:")
        client_id = input("Client ID: ").strip()
        client_secret = input("Client Secret: ").strip()

        if not client_id or not client_secret:
            print("Error: Both required")
            sys.exit(1)

        if add_secret(client_id, client_secret):
            print(f"\nAdded OAUTH_SECRET_{client_id}")
            print("\nNow update deploy.yml to pass this secret:")
            print(f"  OAUTH_SECRET_{client_id}: ${{{{ secrets.OAUTH_SECRET_{client_id} }}}}")
        else:
            print("Failed to add secret")

    elif choice == "2":
        if not existing:
            print("No clients to remove")
            sys.exit(0)

        print("\nRemove which client?")
        for i, cid in enumerate(existing, 1):
            print(f"  {i}. {cid}")

        idx = input("Number: ").strip()
        try:
            cid = existing[int(idx) - 1]
            if remove_secret(cid):
                print(f"\nRemoved OAUTH_SECRET_{cid}")
                print("\nNow remove from deploy.yml")
            else:
                print("Failed to remove")
        except (ValueError, IndexError):
            print("Invalid selection")

    print("\nDone!")


if __name__ == "__main__":
    main()
