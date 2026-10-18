# Prepare an official release

A release provides downloads that work without Python or a source checkout. A green source test alone is not an installer or a shop acceptance result.

## Build and review

1. Merge the reviewed release changes into `main` after every check passes.
2. Open **Actions → Build Windows and Linux installers → Run workflow** on `main`. This creates private-to-the-run downloadable **Windows-installer** and **Linux-installers** artifacts, without publishing or tagging anything.
3. Share these builds with the pharmacy tester. Follow [TRY_IT.md](TRY_IT.md), then record the computer, package checksum, date, printer/scanner models and acceptance results in [REAL_WORLD_READINESS.md](REAL_WORLD_READINESS.md). Test upgrading an existing shop from its previous version as well as a fresh install. Keep a verified external backup.
4. Fix problems on a review branch and repeat the affected checks. Never approve a release with red checks or mark hardware checks complete from cloud tests.

## Signing Windows downloads

The Windows build can sign its app executable **before** packaging the installer, then sign the installer **before** its final checksum and install test. The release file `Windows-SIGNING.txt` reports whether signing was configured.

For public Windows distribution, obtain a trusted Windows code-signing certificate. A repository owner can configure the GitHub Actions secrets `WINDOWS_CERT_BASE64` (the certificate's PFX content encoded as base64) and `WINDOWS_CERT_PASSWORD` using GitHub's secure settings. Never paste these values into an issue, chat, source file or release notes. Certificate/provider requirements vary; hardware-backed certificates may require a different signing service integration.

Without configured signing, workflow artifacts are unsigned pilot builds and the generated release remains a draft. Signing does not guarantee that Windows SmartScreen has already established reputation. Never instruct testers to turn off antivirus or operating-system protection.

## Make the draft

When source and pharmacy acceptance are complete, prepare the matching plain-language notes at `docs/releases/<version>.md`. Version values in `config.py`, `installer.iss` and the release notes must agree. Do not reuse a version already published.

From the exact accepted commit, an authorised maintainer creates and pushes its tag:

```bash
git tag -a v2.4.0 <accepted-full-commit-sha> -m "Pharma Khaato 2.4.0"
git push origin v2.4.0
```

The workflow builds native Windows and Linux packages, runs source/runtime and installed-app checks, verifies that every expected download and checksum exists, and creates a **draft** GitHub Release. Downloads from both platforms come from the same workflow run and source revision. `release.json` records the exact commit and asset hashes; `SHA256SUMS` gives a combined checksum list. A failed platform prevents draft creation. A rerun can replace draft assets but refuses to overwrite a published release.

The workflow's token has read access by default; only the draft job receives release-write access. Drafts and prereleases are ignored by the app's update checker.

## Publish

Review the complete draft at **GitHub → Releases**, download and inspect the packages, confirm signing and shop acceptance, then publish it as stable. Review and publication remain explicit owner actions. After publication, test an older installed app's **About → Check for Updates** on each operating system. It must show the release notes and correct release page; it must keep working without internet.

The first stable version has no older production installation to notify. Customers can use the README's **Download** link once the stable release exists. Future versions follow the same process; uploading a tag alone does not deliver an update.

## Supported builds

- Windows 10 version 1809+ / Windows 11, x64 Intel/AMD. Per-user Setup; administrator access is not normally required.
- Ubuntu 22.04/24.04 x86_64 and compatible desktops. Linux builds use Ubuntu 22.04 as the glibc baseline. The `.deb` is the normal software-installer option; `.tar.gz` includes per-user install/uninstall helpers.
- No ARM, macOS or universal single executable is shipped. Linux tar users need the desktop libraries listed in the Debian control metadata; packages include the Python/Qt application runtime.

Cloud checks do not establish behaviour on every Linux distribution or physical pharmacy device. See [DEPLOYMENT.md](DEPLOYMENT.md) for native build commands and storage paths.
