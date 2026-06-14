"""
One-time helper: exchange a Zoho Self-Client GRANT CODE for a permanent REFRESH TOKEN.

Why: Catalyst QuickML LLM endpoints are OAuth-protected. Access tokens expire hourly, so we
store a long-lived refresh_token and mint access tokens on demand at runtime. This script does
the one-time grant-code -> refresh-token exchange.

Prerequisites (see docs/SETUP_CATALYST.md for the click-path):
  1. api-console.zoho.<DC>  ->  Self Client  ->  copy Client ID + Client Secret
  2. Self Client -> "Generate Code":  scope = QuickML.deployment.READ,  duration 10 min
     -> copy the GRANT CODE (use it within 10 minutes)

Usage:
  python tools/get_refresh_token.py \
      --dc in --client-id 1000.XXXX --client-secret YYYY --code 1000.ZZZZ.AAAA

Prints the refresh_token (and a first access_token). Paste refresh_token into .env.
Standard library only.
"""

import argparse
import json
import urllib.parse
import urllib.request


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dc", default="in", help="Zoho data center: in | com | eu | au | jp | ca")
    ap.add_argument("--client-id", required=True)
    ap.add_argument("--client-secret", required=True)
    ap.add_argument("--code", required=True, help="grant code from Self Client (10-min validity)")
    args = ap.parse_args()

    token_url = f"https://accounts.zoho.{args.dc}/oauth/v2/token"
    payload = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "client_id": args.client_id,
        "client_secret": args.client_secret,
        "code": args.code,
    }).encode()

    req = urllib.request.Request(token_url, data=payload, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print("HTTP error:", e.code, e.read().decode())
        raise SystemExit(1)

    if "refresh_token" not in data:
        print("No refresh_token in response (grant code may be expired/used, or scope wrong):")
        print(json.dumps(data, indent=2))
        raise SystemExit(1)

    print("\nSUCCESS — paste this into .env:\n")
    print(f"ZOHO_REFRESH_TOKEN={data['refresh_token']}")
    print(f"\n(access_token prefix: {data.get('access_token','')[:24]}...)")


if __name__ == "__main__":
    main()
