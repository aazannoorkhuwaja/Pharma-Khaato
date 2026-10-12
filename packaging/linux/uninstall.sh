#!/usr/bin/env sh
set -eu

INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/pharma-khaato/app"
BIN_LINK="$HOME/.local/bin/pharma-khaato"
DESKTOP_FILE="${XDG_DATA_HOME:-$HOME/.local/share}/applications/pharma-khaato.desktop"

rm -rf "$INSTALL_DIR"
rm -f "$BIN_LINK" "$DESKTOP_FILE"
printf '%s\n' "Application binaries removed. User data/backups were intentionally preserved."
