#!/usr/bin/env sh
# Install application files only; the shop's data folder is never replaced.
set -eu
BASE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
APP_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/pharma-khaato"
INSTALL_DIR="$APP_ROOT/app"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
[ -x "$BASE_DIR/app/pharma_khaato" ] || { echo 'Application files are missing. Extract the entire download first.' >&2; exit 1; }
mkdir -p "$APP_ROOT" "$BIN_DIR" "$DESKTOP_DIR"
# Copy first so a failed copy leaves the existing installation usable.
STAGE=$(mktemp -d "$APP_ROOT/.install-XXXXXXXX")
trap 'rm -rf "$STAGE"' EXIT HUP INT TERM
cp -R "$BASE_DIR/app/." "$STAGE/"
chmod +x "$STAGE/pharma_khaato"
# Keep the previous application until its replacement is in place.
PREVIOUS="$APP_ROOT/.previous-app"
if [ -e "$PREVIOUS" ]; then
    echo 'An interrupted installation needs attention: .previous-app exists. Keep it until you have recovered the app.' >&2
    exit 1
fi
if [ -d "$INSTALL_DIR" ]; then mv "$INSTALL_DIR" "$PREVIOUS"; fi
if ! mv "$STAGE" "$INSTALL_DIR"; then
    if [ -d "$PREVIOUS" ]; then mv "$PREVIOUS" "$INSTALL_DIR"; fi
    exit 1
fi
rm -rf "$PREVIOUS"
ln -sf "$INSTALL_DIR/pharma_khaato" "$BIN_DIR/pharma-khaato"
# Desktop Exec has its own escaping rules, separate from shell quoting.
DESKTOP_EXEC=$(printf '%s' "$BIN_DIR/pharma-khaato" | sed 's/\\/\\\\\\\\/g; s/"/\\\\"/g; s/\$/\\\\$/g; s/`/\\\\`/g')
sed '/^Exec=/d' "$BASE_DIR/pharma-khaato.desktop" > "$DESKTOP_DIR/pharma-khaato.desktop"
printf 'Exec="%s"\n' "$DESKTOP_EXEC" >> "$DESKTOP_DIR/pharma-khaato.desktop"
printf '%s\n' 'Installed. Open Pharma Khaato from your applications menu.'
