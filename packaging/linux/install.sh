#!/usr/bin/env sh
set -eu

BASE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/pharma-khaato/app"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"

mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$DESKTOP_DIR"
rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp -R "$BASE_DIR/app/." "$INSTALL_DIR/"
ln -sf "$INSTALL_DIR/pharma_khaato" "$BIN_DIR/pharma-khaato"
sed "s|^Exec=.*|Exec=$BIN_DIR/pharma-khaato|" "$BASE_DIR/pharma-khaato.desktop" > "$DESKTOP_DIR/pharma-khaato.desktop"
chmod +x "$INSTALL_DIR/pharma_khaato" "$BIN_DIR/pharma-khaato"

printf '%s\n' "Installed Pharma-Khaato. Ensure $BIN_DIR is on PATH, or launch from your desktop menu."
