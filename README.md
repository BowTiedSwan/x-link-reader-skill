# x-link-reader skill

`x-link-reader` is an OpenCode/Claude-style skill plus a small local CLI for reading X links through the official X API.

It is built around one principle: do not pass X credentials in prompts every time you want to read a link.

The CLI handles:

- X URL parsing
- official X API lookup via `GET https://api.x.com/2/tweets/{id}`
- full-text extraction for regular posts, long-form posts, and article links
- local credential storage via environment variables or macOS Keychain

## Why a CLI instead of raw curl in prompts

- Secrets stay out of prompt history.
- The skill gets a stable interface: `x-link-reader fetch <url>`.
- The repo can evolve without changing every skill invocation.

## Install

From a local clone:

```bash
git clone git@github.com:bowtiedswan/x-link-reader-skill.git
cd x-link-reader-skill
./install.sh
```

This installs:

- the skill into `~/.agents/skills/x-link-reader`
- the CLI into `~/.local/bin/x-link-reader`

Make sure `~/.local/bin` is on your `PATH`.

If it is not already available, add it with:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

## OpenClaw / ClawHub notes

This repo now includes OpenClaw-oriented metadata in `SKILL.md` for:

- required environment variables: `X_API_BEARER_TOKEN`, `X_API_KEY`, `X_API_SECRET`
- required binary: `python3`
- supported OS targets: `darwin`, `linux`
- primary credential: `X_API_BEARER_TOKEN`

For OpenClaw-style runtimes, prefer injecting credentials through environment variables instead of relying on local Keychain access. That is the most portable and review-friendly setup for marketplace-style skill installs.

## Configure auth

Preferred: store a bearer token once.

```bash
x-link-reader auth set-bearer
```

This prompts for a bearer token and stores it in the macOS Keychain under the `x-link-reader` service, so the token does not live in the repo, skill files, or prompt history.

Alternative: store API key and API secret and let the CLI mint a bearer token.

```bash
x-link-reader auth set-client --api-key "YOUR_X_API_KEY"
```

This stores the API key and API secret in the macOS Keychain and lets the CLI mint a bearer token when needed.

Environment variables also work:

```bash
export X_API_BEARER_TOKEN="..."
# or
export X_API_KEY="..."
export X_API_SECRET="..."
```

If you use environment variables, keep them in a private shell file such as `~/.zshrc.local` or `~/.config/x-link-reader/env`, and lock that file down:

```bash
chmod 600 ~/.zshrc.local
```

Do not store X credentials in this repo, in committed `.env` files, in git config, or in prompt text.

For OpenClaw/ClawHub packaging, treat environment variables as the canonical secret path and Keychain as a local macOS convenience only.

Check which auth source the CLI can see:

```bash
x-link-reader auth status
```

Delete stored Keychain values with:

```bash
x-link-reader auth clear
```

## Usage

```bash
x-link-reader auth status
x-link-reader parse "https://x.com/someone/status/1234567890123456789"
x-link-reader fetch "https://x.com/someone/status/1234567890123456789"
x-link-reader fetch "https://x.com/i/article/1234567890123456789" --text-only
```

### How the skill is used

After `./install.sh`, the skill is installed at `~/.agents/skills/x-link-reader/SKILL.md`. When an OpenCode or Claude-style agent sees a prompt with an `x.com` or `twitter.com` link and the user wants the real text, the skill instructs the agent to call the local CLI instead of asking for credentials in the prompt.

Typical flow:

1. Share an X or Twitter link in the prompt.
2. The skill invokes `x-link-reader fetch "<url>"`.
3. The CLI extracts the numeric ID.
4. The CLI calls the official X API endpoint `GET /2/tweets/{id}`.
5. The CLI returns article text, note tweet text, or regular post text, whichever is available.

Example prompt:

```text
Read this X link and summarize it for me: https://x.com/someone/status/1234567890123456789
```

Example direct CLI invocation:

```bash
x-link-reader fetch "https://x.com/someone/status/1234567890123456789"
```

## Extraction logic

The CLI requests `tweet.fields=note_tweet,article,entities,author_id,created_at` and returns text in this order:

1. `data.article.text`
2. `data.note_tweet.text`
3. `data.text`

Both X article URL shapes are accepted:

- `https://x.com/i/article/<id>`
- `https://x.com/i/articles/<id>`

## Repo contents

- `SKILL.md`: skill definition and usage instructions
- `scripts/x_link_reader.py`: standalone CLI implementation
- `references/x-api.md`: concise API notes and request details
- `evals/evals.json`: realistic trigger/use test prompts for skill work
- `install.sh`: local installer for the skill and CLI

## Security model

- The skill uses the local `x-link-reader` command instead of embedding raw secrets in prompts.
- Credentials are loaded from macOS Keychain when stored there, or from environment variables when you prefer that setup.
- No credential file is checked into the repository.
- Rotating credentials only requires rerunning `x-link-reader auth set-bearer`, `x-link-reader auth set-client`, or updating your private environment file.
- All API calls go only to `https://api.x.com`.
- This repo does not forward retrieved X content or credentials to third-party services.

## OpenClaw publish caveats

This repo is closer to OpenClaw/ClawHub-ready now, but it does not yet include any owner-specific registry metadata such as `_meta.json` values that depend on a real marketplace account. If ClawHub requires registry-side metadata during publish, add those values at publish time rather than hardcoding guessed fields into the repo.

## GitHub publishing

This repo is intended to live publicly under the `bowtiedswan` account.
