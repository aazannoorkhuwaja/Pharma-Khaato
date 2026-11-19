# Dependency security review — 2026-11-12

Release dependencies now pin PySide6-Essentials 6.12.0 and cryptography 50.0.2. Local verification used Qt 6.12.0 but cryptography 46.0.5; the release environment is **not** reproduced locally. The packaging inventory generator refuses versions outside requirements, so a stale workstation cannot quietly package the old cryptography build.

| Component/advisory | Evidence and decision |
|---|---|
| Old Qt 6.7.2 / CVE-2025-5455 | Removed the obsolete pin. The advisory's vulnerable branch and assertion-dependent data-URL handling are described by [Qt](https://www.qt.io/blog/security-advisory-recently-discovered-issue-in-qdecodedataurl-in-qtcore-impacts-qt). No claim of a demonstrated application exploit. |
| Qt 6.12.0 availability | Verified against [official PyPI files](https://pypi.org/project/PySide6-Essentials/) and [Qt's distribution directory](https://download.qt.io/official_releases/QtForPython/pyside6-essentials/). This version is available for supported Python release builds. Availability is not a vulnerability-free certification. |
| CVE-2026-114366 | [Qt's advisory](https://www.qt.io/blog/security-issue-cve-2026-114366?hsLang=en) includes 6.12.0 QWebSocket and identifies 6.12.1 as a fixed line. Application source does not use QWebSocket. Packaging explicitly excludes its Python module. Native artifact inspection remains required; this is a reachability inference, not a blanket exception. |
| CVE-2026-110944 | [Qt's advisory](https://www.qt.io/blog/security-advisory-cve-2026-110944) concerns QHttpServer. The shop server uses Python HTTPS with bounded workers, not Qt HTTP Server. Its Python module is excluded from packaging. Verify actual artifacts and newer patches before promotion. |
| Cryptography CVE-2026-69247 | [Upstream changelog](https://cryptography.io/en/latest/changelog/) records the PKCS7 decryption fix in 50.0.0 and later wheel updates in 50.0.2. Selected 50.0.2 rather than retaining the old `<47` cap. Application uses certificate generation and AES-GCM/scrypt, but release validation must still exercise the upgraded dependency. |

The release workflow runs `pip-audit --strict` and emits CycloneDX JSON before packaging. Scanner failures or unresolved findings block the build; no ignore list was added. This host cannot fetch PyPI packages or execute that scanner, so **there is no completed full dependency scan**. Qt native advisories must be reviewed separately because Python advisory feeds do not establish complete native-library coverage.

`release_inventory.py` collects the installed runtime dependency closure, versions, license metadata and available license texts. The PyInstaller specification includes that inventory in `third-party/`. Generate a second artifact file/hash inventory after packaging. Have the release owner review Qt/Python/OpenSSL and all other shipped native components against their actual license obligations; generated notices are evidence collection, not a legal sign-off.

## 2026-11-18 CI audit follow-up

[Installer run 44253215207](https://github.com/aazannoorkhuwaja/Pharma-Khaato/actions/runs/44253215207) blocked both builds. Its Linux and Windows CycloneDX artifacts reported two records for python-dotenv 1.0.1; the Linux artifact identifies both as PYSEC-2026-2270. The maintainer advisory [GHSA-mf9w-mj56-hr94 / CVE-2026-28684](https://github.com/theskumar/python-dotenv/security/advisories/GHSA-mf9w-mj56-hr94) describes symlink-following writes and fixes them in 1.2.2. The requirement is now pinned to [1.2.4](https://pypi.org/project/python-dotenv/1.2.4/), which is already used by local validation. The strict audit remains enabled, with no vulnerability exclusions. A new CI scan must confirm the resolved dependency set.

CI log review also found that the Windows compatibility step ran pytest and GUI smoke in one PowerShell block. A succeeding final command masked the pytest failure in the earlier run. Dependency installation, pytest and GUI smoke now have separate steps so any failure stops that job. This is why workflow green status alone is not release acceptance.
