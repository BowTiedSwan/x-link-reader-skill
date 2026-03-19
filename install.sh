#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_NAME="x-link-reader"
SKILL_DIR="$HOME/.agents/skills/$SKILL_NAME"
BIN_DIR="$HOME/.local/bin"
CLI_SOURCE="$ROOT_DIR/scripts/x_link_reader.py"
CLI_TARGET="$BIN_DIR/x-link-reader"

mkdir -p "$SKILL_DIR" "$SKILL_DIR/references" "$SKILL_DIR/evals" "$BIN_DIR"

cp "$ROOT_DIR/SKILL.md" "$SKILL_DIR/SKILL.md"
cp "$ROOT_DIR/references/x-api.md" "$SKILL_DIR/references/x-api.md"
cp "$ROOT_DIR/evals/evals.json" "$SKILL_DIR/evals/evals.json"
cp "$CLI_SOURCE" "$CLI_TARGET"
chmod +x "$CLI_TARGET"

printf "Installed skill to %s\n" "$SKILL_DIR"
printf "Installed CLI to %s\n" "$CLI_TARGET"

case ":$PATH:" in
  *":$BIN_DIR:"*)
    printf "%s is already on PATH\n" "$BIN_DIR"
    ;;
  *)
    printf "Add %s to your PATH if needed.\n" "$BIN_DIR"
    ;;
esac

printf "Next steps:\n"
printf "  1. x-link-reader auth set-bearer\n"
printf "  2. x-link-reader auth status\n"
printf "  3. x-link-reader fetch \"https://x.com/<user>/status/<id>\"\n"
