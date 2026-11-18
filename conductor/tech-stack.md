# Technology
PySide6 provides the desktop interface. SQLite stores shop records and migration history. LAN counters submit operations to the shop computer. Background reads and checkout work use Qt workers. The supported Python and operating-system combinations are defined in the [CI workflows](../.github/workflows/).

Keep historical migration files intact. Preserve retry behavior for operation identifiers created by previous versions.
