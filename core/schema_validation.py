"""Validate declared migration structure without opening the live shop store."""
import sqlite3
import hashlib
import re
from pathlib import Path
from contextlib import closing
from core.migration_manager import MigrationManager


def validate_declared_schema(connection, applied):
    folder = Path(__file__).resolve().parent.parent / 'migrations'
    catalog = MigrationManager._migration_catalog(str(folder))
    known = [Path(p).name for p in catalog]
    recorded = set(applied)
    applied = MigrationManager.canonical_history(recorded, known)
    if applied and applied != set(known[:max(known.index(v) for v in applied) + 1]):
        raise ValueError('The backup has incomplete migration history.')
    if "checksum" in {r[1] for r in connection.execute("PRAGMA table_info(schema_migrations)")}:
        for version, checksum in connection.execute("SELECT version,checksum FROM schema_migrations"):
            if version in recorded - applied:
                if checksum:
                    raise ValueError(f"Unrecognized historical migration checksum: {version}.")
                continue
            if checksum and checksum != hashlib.sha256((folder / version).read_bytes()).hexdigest():
                raise ValueError(f"Migration checksum differs: {version}.")
    with closing(sqlite3.connect(':memory:')) as expected:
        from core.financial_storage import register
        register(expected)
        expected.executescript((folder.parent / 'schema_sqlite.sql').read_text(encoding='utf-8'))
        for path in catalog:
            if Path(path).name not in applied:
                continue
            for statement in MigrationManager._split_statements(Path(path).read_text(encoding='utf-8')):
                try:
                    expected.execute(statement)
                except sqlite3.OperationalError as exc:
                    # The shipped baseline includes additive columns also present
                    # in historical migrations, exactly as fresh initialization does.
                    if 'duplicate column name:' not in str(exc).lower():
                        raise
        for kind, name, sql in expected.execute(
                "SELECT type,name,sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'"):
            actual = connection.execute('SELECT type,sql FROM sqlite_master WHERE name=?', (name,)).fetchone()
            if not actual or actual[0] != kind:
                raise ValueError(f'Required database {kind} is missing: {name}.')
            if kind == 'table':
                # Names come exclusively from bundled migrations, never user SQL.
                columns = {r[1]: r[2:] for r in expected.execute(f'PRAGMA table_info("{name}")')}
                present = {r[1]: r[2:] for r in connection.execute(f'PRAGMA table_info("{name}")')}
                for column, definition in columns.items():
                    if column not in present or present[column] != definition:
                        # Observed legacy stores carrying the redundant 014
                        # index history allowed unattributed audit events. This
                        # field is descriptive, never an authorization source.
                        # Preserve those events rather than invent an actor or
                        # weakening constraints on financial/identity tables.
                        legacy_audit_actor = (
                            '014_ui_performance_indexes.sql' in recorded
                            and name == 'Audit_Log' and column == 'user_id'
                            and definition == ('TEXT', 1, None, 0)
                            and present.get(column) == ('TEXT', 0, None, 0)
                        )
                        if legacy_audit_actor:
                            continue
                        raise ValueError(f'Required column is missing or incompatible: {name}.{column}.')
                expected_fks = _foreign_keys(expected, name)
                actual_fks = _foreign_keys(connection, name)
                if '014_ui_performance_indexes.sql' in recorded and name == 'Hold_Sales':
                    # Legacy releases linked held sales to their employee. Keep
                    # this exact historical constraint; never ignore missing or
                    # changed constraints on purchase/financial relationships.
                    legacy_employee_fk = ((0, 'Employee', 'employee_id', 'Employee_id', 'NO ACTION', 'CASCADE', 'NONE'),)
                    if actual_fks == expected_fks | {legacy_employee_fk}:
                        actual_fks = expected_fks
                if expected_fks != actual_fks:
                    raise ValueError(f'Foreign keys differ: {name}.')
                for index in expected.execute(f'PRAGMA index_list("{name}")'):
                    if index[2]:
                        expected_columns = tuple(r[2] for r in expected.execute(f'PRAGMA index_info("{index[1]}")'))
                        actual_unique = [tuple(r[2] for r in connection.execute(f'PRAGMA index_info("{i[1]}")'))
                                         for i in connection.execute(f'PRAGMA index_list("{name}")') if i[2]]
                        if expected_columns not in actual_unique:
                            raise ValueError(f'Unique constraint differs: {name}.')
                if not _checks(sql).issubset(_checks(actual[1])):
                    raise ValueError(f'Check constraints differ: {name}.')
            elif kind in {'index', 'trigger'}:
                if ' '.join(sql.split()).lower() != ' '.join(actual[1].split()).lower():
                    raise ValueError(f'Database {kind} definition differs: {name}.')


def _foreign_keys(connection, name):
    """Compare relationships, not SQLite's incidental constraint numbering."""
    groups = {}
    for identifier, *definition in connection.execute(f'PRAGMA foreign_key_list("{name}")'):
        groups.setdefault(identifier, []).append(tuple(definition))
    return {tuple(sorted(rows)) for rows in groups.values()}


def _checks(sql):
    """Extract balanced CHECK expressions for the bundled schema comparison."""
    normalized = re.sub(r"\s+", "", sql.lower())
    result = set()
    for match in re.finditer(r'check\(', normalized):
        depth = 1
        end = match.end()
        while end < len(normalized) and depth:
            depth += (normalized[end] == '(') - (normalized[end] == ')')
            end += 1
        result.add(normalized[match.start():end])
    return result
