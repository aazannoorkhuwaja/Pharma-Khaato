This directory intentionally contains no native modules. The frozen Qt desktop
uses its bundled GLib/GIO with built-in backends, rather than loading unrelated
host dconf/gvfs plugins linked against a different GLib ABI. Do not copy system
.so files here. File dialogs, accessibility and printing still need acceptance
on each supported desktop; this is not a replacement for those tests.
