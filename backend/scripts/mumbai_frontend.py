"""Launch an existing local app against guarded Mumbai staging; no frontend edits."""

import argparse
import os
import subprocess

from mumbai_local import BACKEND, BASE, bind


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("role", choices=("customer", "owner"))
    args = parser.parse_args()
    bind()
    app = BACKEND.parents[1] / ("Salon-Customer-APP/customer-app" if args.role == "customer" else "salon-owner-APP")
    # No backend service key, provider settings or normal app dotenv files reach Metro.
    environment = {key: value for key, value in os.environ.items() if key.upper() in {
        "SYSTEMROOT", "WINDIR", "PATH", "PATHEXT", "TEMP", "TMP", "USERPROFILE",
        "LOCALAPPDATA", "APPDATA", "COMSPEC", "PROGRAMFILES", "PROGRAMFILES(X86)",
    }}
    environment.update(EXPO_NO_DOTENV="1", EXPO_PUBLIC_API_URL="http://127.0.0.1:8056",
        EXPO_PUBLIC_API_BASE_URL="http://127.0.0.1:8056", EXPO_PUBLIC_SUPABASE_URL=BASE,
        EXPO_PUBLIC_SUPABASE_ANON_KEY=os.environ["SUPABASE_ANON_KEY"],
        EXPO_PUBLIC_USE_MOCK_API="false", BABEL_DISABLE_CACHE="1", CI="1")
    port = "8081" if args.role == "customer" else "8082"
    return subprocess.call(["node", "node_modules/expo/bin/cli", "start", "--web", "--port", port, "--localhost"],
        cwd=app, env=environment)


if __name__ == "__main__":
    raise SystemExit(main())
