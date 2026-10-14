# Python / PySide6 Compatibility

Pharma-Khaato v2.3.1 retains the cross-version runtime fix introduced in v2.2.1.
The requirements select a PySide6 release compatible with the Python interpreter:

- Python 3.10–3.12: PySide6 6.7.2
- Python 3.13: PySide6 6.9.3
- Python 3.14+: PySide6 6.10.1–<6.13

This prevents the universal Windows/Linux test launcher from failing on newer Python installations while preserving a stable Qt line on older supported interpreters.
