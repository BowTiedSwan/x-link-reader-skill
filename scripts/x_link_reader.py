#!/usr/bin/env python3

import argparse
import base64
import getpass
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request


API_BASE = "https://api.x.com"
LOOKUP_FIELDS = "note_tweet,article,entities,author_id,created_at"
KEYCHAIN_SERVICE = "x-link-reader"
KEYCHAIN_ACCOUNTS = {
    "bearer": "bearer-token",
    "api_key": "api-key",
    "api_secret": "api-secret",
}
ALLOWED_HOSTS = {
    "x.com",
    "www.x.com",
    "mobile.x.com",
    "twitter.com",
    "www.twitter.com",
    "mobile.twitter.com",
}
STATUS_RE = re.compile(r"/(?:status|statuses)/([0-9]{1,19})(?:[/?#]|$)")
ARTICLE_RE = re.compile(r"/i/articles/([0-9]{1,19})(?:[/?#]|$)")
ID_RE = re.compile(r"^[0-9]{1,19}$")


class CliError(RuntimeError):
    pass


def json_dump(payload):
    print(json.dumps(payload, indent=2, sort_keys=True))


def is_macos():
    return sys.platform == "darwin"


def run_security(args, input_text=None, check=True):
    command = ["security"] + args
    result = subprocess.run(
        command,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise CliError(
            result.stderr.strip() or result.stdout.strip() or "security command failed"
        )
    return result


def keychain_get(kind):
    if not is_macos():
        return None
    result = run_security(
        [
            "find-generic-password",
            "-s",
            KEYCHAIN_SERVICE,
            "-a",
            KEYCHAIN_ACCOUNTS[kind],
            "-w",
        ],
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def keychain_set(kind, value):
    if not is_macos():
        raise CliError(
            "Keychain storage is only supported on macOS. Use environment variables on this platform."
        )
    run_security(
        [
            "add-generic-password",
            "-U",
            "-s",
            KEYCHAIN_SERVICE,
            "-a",
            KEYCHAIN_ACCOUNTS[kind],
            "-w",
            value,
        ]
    )


def keychain_delete(kind):
    if not is_macos():
        return False
    result = run_security(
        [
            "delete-generic-password",
            "-s",
            KEYCHAIN_SERVICE,
            "-a",
            KEYCHAIN_ACCOUNTS[kind],
        ],
        check=False,
    )
    return result.returncode == 0


def prompt_secret(label):
    value = getpass.getpass(f"{label}: ").strip()
    if not value:
        raise CliError(f"{label} cannot be empty")
    return value


def load_credentials():
    bearer = os.environ.get("X_API_BEARER_TOKEN") or keychain_get("bearer")
    if bearer:
        return {
            "mode": "bearer",
            "bearer_token": bearer,
            "source": credential_source("X_API_BEARER_TOKEN", "bearer"),
        }

    api_key = os.environ.get("X_API_KEY") or keychain_get("api_key")
    api_secret = os.environ.get("X_API_SECRET") or keychain_get("api_secret")
    if api_key and api_secret:
        return {
            "mode": "client_credentials",
            "api_key": api_key,
            "api_secret": api_secret,
            "source": credential_source_pair(api_key, api_secret),
        }

    raise CliError(
        "No X credentials found. Run `x-link-reader auth set-bearer`, or set X_API_BEARER_TOKEN, or provide X_API_KEY and X_API_SECRET."
    )


def credential_source(env_name, keychain_kind):
    if os.environ.get(env_name):
        return f"env:{env_name}"
    if keychain_get(keychain_kind):
        return f"keychain:{keychain_kind}"
    return "unknown"


def credential_source_pair(api_key, api_secret):
    env_key = bool(os.environ.get("X_API_KEY"))
    env_secret = bool(os.environ.get("X_API_SECRET"))
    if env_key and env_secret:
        return "env:X_API_KEY+X_API_SECRET"
    if api_key and api_secret:
        return "keychain:api_key+api_secret"
    return "unknown"


def mint_bearer_token(api_key, api_secret, timeout):
    encoded = base64.b64encode(f"{api_key}:{api_secret}".encode("utf-8")).decode(
        "ascii"
    )
    payload = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(
        "utf-8"
    )
    request = urllib.request.Request(
        f"{API_BASE}/oauth2/token",
        data=payload,
        headers={
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        },
        method="POST",
    )
    data = http_json(request, timeout)
    token = data.get("access_token")
    if not token:
        raise CliError("X token endpoint did not return an access_token")
    return token


def parse_target(target):
    target = target.strip()
    if not target:
        raise CliError("Target cannot be empty")
    if ID_RE.match(target):
        return {"id": target, "url_kind": "id", "normalized_url": None}

    parsed = urllib.parse.urlparse(target)
    host = parsed.netloc.lower().split(":", 1)[0]
    if host in ALLOWED_HOSTS:
        article_match = ARTICLE_RE.search(parsed.path)
        if article_match:
            ident = article_match.group(1)
            return {
                "id": ident,
                "url_kind": "article",
                "normalized_url": f"https://x.com/i/articles/{ident}",
            }

        status_match = STATUS_RE.search(parsed.path)
        if status_match:
            ident = status_match.group(1)
            return {
                "id": ident,
                "url_kind": "status",
                "normalized_url": f"https://x.com/i/web/status/{ident}",
            }

    raise CliError(
        "Unsupported X/Twitter URL. Expected a /status/<id> or /i/articles/<id> link, or a bare numeric ID."
    )


def http_json(request, timeout):
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        message = body
        try:
            parsed = json.loads(body)
            if parsed.get("errors"):
                message = parsed["errors"][0].get("message", body)
        except json.JSONDecodeError:
            pass
        raise CliError(f"X API request failed with HTTP {exc.code}: {message}") from exc
    except urllib.error.URLError as exc:
        raise CliError(f"Network error: {exc.reason}") from exc


def fetch_lookup(tweet_id, bearer_token, timeout):
    query = urllib.parse.urlencode({"tweet.fields": LOOKUP_FIELDS})
    api_url = f"{API_BASE}/2/tweets/{tweet_id}?{query}"
    request = urllib.request.Request(
        api_url,
        headers={"Authorization": f"Bearer {bearer_token}"},
        method="GET",
    )
    data = http_json(request, timeout)
    if "data" not in data:
        raise CliError("X API response did not include a data object")
    return api_url, data["data"], data


def extract_article_text(article_obj):
    if not isinstance(article_obj, dict):
        return None
    for key in ("text", "body", "content"):
        value = article_obj.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def normalize_record(parsed_target, input_target, api_url, tweet_obj):
    article_text = extract_article_text(tweet_obj.get("article"))
    note_tweet = (
        tweet_obj.get("note_tweet")
        if isinstance(tweet_obj.get("note_tweet"), dict)
        else {}
    )
    note_text = (
        note_tweet.get("text") if isinstance(note_tweet.get("text"), str) else None
    )
    display_text = (
        tweet_obj.get("text") if isinstance(tweet_obj.get("text"), str) else ""
    )

    if article_text:
        content_type = "article"
        text = article_text
    elif note_text:
        content_type = "note_tweet"
        text = note_text
    else:
        content_type = "post"
        text = display_text

    return {
        "api_url": api_url,
        "author_id": tweet_obj.get("author_id"),
        "content_type": content_type,
        "created_at": tweet_obj.get("created_at"),
        "display_text": display_text,
        "id": tweet_obj.get("id") or parsed_target["id"],
        "input": input_target,
        "normalized_url": parsed_target.get("normalized_url"),
        "text": text,
        "url_kind": parsed_target["url_kind"],
    }


def cmd_parse(args):
    parsed = parse_target(args.target)
    json_dump(parsed)


def cmd_fetch(args):
    parsed = parse_target(args.target)
    credentials = load_credentials()
    bearer_token = credentials.get("bearer_token")
    if credentials["mode"] == "client_credentials":
        bearer_token = mint_bearer_token(
            credentials["api_key"], credentials["api_secret"], args.timeout
        )

    api_url, tweet_obj, _raw = fetch_lookup(parsed["id"], bearer_token, args.timeout)
    record = normalize_record(parsed, args.target, api_url, tweet_obj)
    record["credential_source"] = credentials["source"]

    if args.text_only:
        print(record["text"])
        return

    json_dump(record)


def cmd_auth_status(_args):
    active_source = None
    try:
        active_source = load_credentials()["source"]
    except CliError:
        active_source = None

    payload = {
        "active": active_source,
        "env": {
            "X_API_BEARER_TOKEN": bool(os.environ.get("X_API_BEARER_TOKEN")),
            "X_API_KEY": bool(os.environ.get("X_API_KEY")),
            "X_API_SECRET": bool(os.environ.get("X_API_SECRET")),
        },
        "keychain": {
            "supported": is_macos(),
            "bearer": bool(keychain_get("bearer")) if is_macos() else False,
            "api_key": bool(keychain_get("api_key")) if is_macos() else False,
            "api_secret": bool(keychain_get("api_secret")) if is_macos() else False,
        },
    }
    json_dump(payload)


def cmd_auth_set_bearer(args):
    token = args.token
    if args.stdin:
        token = sys.stdin.read().strip()
    if not token:
        token = prompt_secret("X bearer token")
    keychain_set("bearer", token)
    print("Stored bearer token in macOS Keychain.")


def cmd_auth_set_client(args):
    api_key = args.api_key or input("X API key: ").strip()
    if not api_key:
        raise CliError("X API key cannot be empty")

    api_secret = args.api_secret
    if args.secret_stdin:
        api_secret = sys.stdin.read().strip()
    if not api_secret:
        api_secret = prompt_secret("X API secret")

    keychain_set("api_key", api_key)
    keychain_set("api_secret", api_secret)
    print("Stored API key and API secret in macOS Keychain.")


def cmd_auth_clear(_args):
    deleted = {
        "bearer": keychain_delete("bearer"),
        "api_key": keychain_delete("api_key"),
        "api_secret": keychain_delete("api_secret"),
    }
    json_dump(deleted)


def build_parser():
    parser = argparse.ArgumentParser(description="Read X links via the official X API.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parse_parser = subparsers.add_parser(
        "parse", help="Extract the X resource ID from a supported URL."
    )
    parse_parser.add_argument("target", help="An X/Twitter URL or a numeric ID.")
    parse_parser.set_defaults(func=cmd_parse)

    fetch_parser = subparsers.add_parser(
        "fetch", help="Fetch text for an X post or article."
    )
    fetch_parser.add_argument("target", help="An X/Twitter URL or a numeric ID.")
    fetch_parser.add_argument(
        "--text-only", action="store_true", help="Print only the extracted text."
    )
    fetch_parser.add_argument(
        "--timeout", type=float, default=20.0, help="HTTP timeout in seconds."
    )
    fetch_parser.set_defaults(func=cmd_fetch)

    auth_parser = subparsers.add_parser("auth", help="Manage local X credentials.")
    auth_subparsers = auth_parser.add_subparsers(dest="auth_command", required=True)

    auth_status = auth_subparsers.add_parser(
        "status", help="Show available auth sources."
    )
    auth_status.set_defaults(func=cmd_auth_status)

    auth_set_bearer = auth_subparsers.add_parser(
        "set-bearer", help="Store a bearer token in macOS Keychain."
    )
    auth_set_bearer.add_argument("--token", help="Bearer token value.")
    auth_set_bearer.add_argument(
        "--stdin", action="store_true", help="Read the bearer token from stdin."
    )
    auth_set_bearer.set_defaults(func=cmd_auth_set_bearer)

    auth_set_client = auth_subparsers.add_parser(
        "set-client", help="Store API key and secret in macOS Keychain."
    )
    auth_set_client.add_argument("--api-key", help="X API key.")
    auth_set_client.add_argument("--api-secret", help="X API secret.")
    auth_set_client.add_argument(
        "--secret-stdin", action="store_true", help="Read the API secret from stdin."
    )
    auth_set_client.set_defaults(func=cmd_auth_set_client)

    auth_clear = auth_subparsers.add_parser(
        "clear", help="Delete stored macOS Keychain credentials."
    )
    auth_clear.set_defaults(func=cmd_auth_clear)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except CliError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
