#!/usr/bin/env bash
# Instala a skill "watch" no Claude Code (nível usuário: ~/.claude/skills/watch)
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}/watch"
mkdir -p "$(dirname "$DEST")"
rm -rf "$DEST"
cp -r "$DIR/skills/watch" "$DEST"
echo "Skill instalada em $DEST"

command -v ffmpeg >/dev/null || echo "⚠ ffmpeg não encontrado: instale (brew install ffmpeg / apt install ffmpeg / winget install ffmpeg)"
python3 -m pip install --user -q yt-dlp faster-whisper && echo "yt-dlp e faster-whisper instalados"
