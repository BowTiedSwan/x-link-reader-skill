---
name: x-link-reader
description: |
  Read X.com and Twitter post links with the official X API, including regular posts, long-form posts, and article links. Use this skill whenever the user shares an `x.com` or `twitter.com` URL and wants the actual text, asks to read a post or article, wants a thread/article summarized from a link, or needs the post ID extracted and fetched through the official API instead of scraping. This skill assumes a local `x-link-reader` CLI is installed so secrets stay out of prompts and requires X API credentials to be available through environment variables or local secret storage.
version: 1.0.0
homepage: https://github.com/BowTiedSwan/x-link-reader-skill
metadata:
  openclaw:
    requires:
      env:
        - X_API_BEARER_TOKEN
        - X_API_KEY
        - X_API_SECRET
      bins:
        - python3
    primaryEnv: X_API_BEARER_TOKEN
    os:
      - darwin
      - linux
---

# X Link Reader

Use this skill when the user shares an X link and wants the text content fetched via the official X API.

## What this skill does

- Extracts the X resource ID from `https://x.com/<user>/status/<id>`, `https://x.com/i/article/<id>`, and `https://x.com/i/articles/<id>` links.
- Calls the official X API endpoint `GET /2/tweets/{id}`.
- Requests `tweet.fields=note_tweet,article,entities,author_id,created_at` so long-form content is available when present.
- Returns content using this priority:
  1. `data.article.text`
  2. `data.note_tweet.text`
  3. `data.text`

## Required setup

The local CLI must be installed first. Once installed, configure credentials once using one of these methods:

```bash
# Preferred: store a bearer token locally
x-link-reader auth set-bearer

# Or store API key + API secret and let the CLI mint a bearer token
x-link-reader auth set-client --api-key "YOUR_X_API_KEY"
```

The CLI stores secrets outside prompts. On macOS it can use Keychain. Environment variables also work:

```bash
export X_API_BEARER_TOKEN="..."
# or
export X_API_KEY="..."
export X_API_SECRET="..."
```

For OpenClaw-style runtimes, prefer environment-variable injection over Keychain-specific setup. The runtime metadata above declares the required environment variables and `python3` as the required binary.

## Core commands

```bash
# Fetch structured JSON for a post or article link
x-link-reader fetch "https://x.com/jack/status/20"

# Get plain text only
x-link-reader fetch "https://x.com/jack/status/20" --text-only

# Parse a URL without calling the network
x-link-reader parse "https://x.com/someone/status/1234567890123456789"

# Check whether auth is available
x-link-reader auth status
```

## How to use it during a task

1. Run `x-link-reader auth status` if auth availability is unclear.
2. Run `x-link-reader fetch "<url>"` for the user-provided link.
3. Use the returned `content_type` and `text` fields in your response.
4. If auth is missing, tell the user to configure the CLI once. Do not ask them to paste secrets into the prompt unless they explicitly want that.

## Response shape

The CLI returns JSON like this:

```json
{
  "id": "1234567890123456789",
  "input": "https://x.com/example/status/1234567890123456789",
  "content_type": "post",
  "text": "Full extracted text",
  "display_text": "Displayed text from the base post object",
  "author_id": "2244994945",
  "created_at": "2024-01-01T00:00:00.000Z"
}
```

## Failure handling

- If the CLI reports missing auth, stop and ask the user to run the setup command once.
- If the API returns an error, surface the relevant error message and status code.
- If the URL does not match a supported X/Twitter pattern, say that clearly instead of guessing an ID.

## Security model

- Read credentials from environment variables or local OS secret storage at runtime.
- Never store secrets in the repository or ask the user to paste them into the prompt unless they explicitly want to do that.
- Send requests only to the official X API at `https://api.x.com`.
- Do not forward retrieved X content or credentials to third-party services.

## Notes

- Use the CLI rather than hand-writing curl commands in the prompt path. That keeps secrets out of prompt history.
- The official X API still uses the tweet resource for article and long-form text retrieval, so the same lookup path covers regular posts, note tweets, and article content.
