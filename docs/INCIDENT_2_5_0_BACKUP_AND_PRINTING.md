# Installed 2.5.0 backup and printing incident

Investigated 2026-11-15 on Linux. The Debian package upgraded successfully. The `_apt` access notice did not prevent installation. This investigation changes repository source and creates a separate recovery copy; it does not replace the installed executable, modify the live pharmacy database, or claim that an updated installer has shipped.

## Confirmed causes and corrections

| Symptom | Evidence | Source correction |
|---|---|---|
| Every automatic backup says a different application version is required | The installed package includes `015_ui_performance_indexes.sql`; the database records both that name and the older `014_ui_performance_indexes.sql`. A disposable reproduction failed with the same message. | Recognize only this redundant historical alias when the canonical replacement is also present. Preserve migration history. Unknown versions, unsupported checksums and altered indexes remain rejected. |
| Stricter roadmap validation rejects the historical store | Read-only inspection found a nullable `Audit_Log.user_id` and an additional employee foreign key on `Hold_Sales`. These differ from fresh-store definitions. | Support these exact historical variants only with the recognized historical history marker. Do not fabricate audit identities or relax financial-table constraints. Foreign-key comparison now uses the actual relationship, not SQLite's incidental constraint number. |
| `g_task_set_static_name` / `g_assertion_message_cmpint` missing | A child process using the installed bundle's GIO/GLib reproduced both errors when loading the host's gvfs/dconf modules. Using an isolated module directory removed both errors. | A Linux frozen-runtime hook selects the bundled module directory and removes additional host-module search paths before Qt loads. Source runs retain their normal desktop environment. |
| `QPainter::begin(): Returned false` followed by printing success | Rendering a receipt to an invalid PDF destination reproduced the exact warning and a false success result. `QTextDocument.print_()` has no success return value. | Explicitly check painter startup, page transitions, completion and printer error/aborted state. A failed submission returns false so the saved sale can be reprinted. Never infer physical paper delivery from spool submission. |

The documented [GIO module search behavior](https://docs.gtk.org/gio/overview.html) explains the native-library mismatch mechanism. Qt documents [QPrinter paint-job startup](https://doc.qt.io/qt-6/qprinter.html) and the [void document-printing convenience API](https://doc.qt.io/QT-6/qtextdocument.html). The fixes are based on local reproductions, not merely on these descriptions.

The stale device-pixel-ratio and ATK bridge messages were not reproduced or declared fixed. Physical printer success and accessibility behavior remain target-machine checks. Do not disable accessibility globally to silence the ATK message.

## Verification

- Focused integrated regression run: **83 passed, 1 deselected**, 55.15 seconds. The deselected recovery-screen test requires the currently unavailable pytest-qt `qapp` fixture. Other Qt printing tests create a real offscreen application directly.
- All eight legacy-history regressions pass, including rejection of unknown versions, unrecognized alias checksums and altered indexes, and preservation of original migration rows.
- Source functional smoke passed owner setup/login, checkout/retry, receipts, fresh and legacy-history backups, TLS certificate generation and all eight major screens. This ran the local source version (2.4.2 metadata), not a rebuilt 2.5.0 binary.
- Long 58 mm and 80 mm receipts produced complete multipage PDFs. Independent `pdftotext` extraction found all 200 fixture lines in each format. This is not a physical printer test.
- The existing shop passed the corrected structural/integrity/foreign-key validator in read-only mode.
- `git diff --check` passed.

The packaged functional smoke now creates and validates fresh and legacy-history backups, so future frozen builds must exercise bundled migration discovery rather than testing only checkout/startup.

## Recovery copy and release boundary

An owner-private SQLite online backup was created in `~/Pharma-Khaato-Recovery/`, with a SHA-256 sidecar and explanatory README. The source connection was opened read-only. This is sensitive business data: retain the directory privately and keep a protected off-device copy. This copy is not encrypted and does not contain a complete host/counter configuration or TLS/recovery-key bundle. It must not be mistaken for automatic-backup recovery having been repaired in the installed application.

The installed version remains 2.5.0 and will continue running its old code until a corrected package is built, tested and installed. PyInstaller is unavailable in this environment and package-index access failed; release dependencies also differ from the local runtime. Do not bypass build/audit checks or transplant migration files into `/opt` to hide the error. In particular, adding another `014_*.sql` file would create an ambiguous migration catalog.

Before distributing the fix, build against the intended release branch/version, run the packaged functional smoke and installer tests, verify this historical compatibility fixture, and test native file dialogs/accessibility/printing on supported Linux desktops. Preserve the independently tested source changes on `fix/audit-integrity`; the broader roadmap working tree is not an already-published release.
