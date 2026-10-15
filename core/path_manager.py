import os
import sys
import platform

class PathManager:
    """
    Central Path Manager abstraction.
    Ensures application data (database, logs, backups, receipts, exports) is stored in
    OS-appropriate user writable directories, keeping executable directories immutable.
    """
    _APP_NAME = "Pharma-Khaato"
    _BASE_DATA_DIR = None

    @classmethod
    def get_base_data_dir(cls):
        if cls._BASE_DATA_DIR:
            return cls._BASE_DATA_DIR

        # Check if overridden by environment variable (e.g. for testing)
        env_override = os.getenv("PHARMA_KHAATO_DATA_DIR")
        if env_override:
            cls._BASE_DATA_DIR = os.path.abspath(env_override)
        else:
            # System OS Writable Data Directory Selection
            system = platform.system()
            if system == "Windows":
                app_data = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or os.path.expanduser("~")
                target_dir = os.path.join(app_data, cls._APP_NAME)
            elif system == "Darwin":
                target_dir = os.path.expanduser(f"~/Library/Application Support/{cls._APP_NAME}")
            else:
                # Linux/Unix: Use XDG_DATA_HOME or ~/.local/share/pharma-khaato
                xdg_data = os.getenv("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
                target_dir = os.path.join(xdg_data, "pharma-khaato")

            # If explicitly configured for local workspace dev mode via environment
            if os.getenv("PHARMA_KHAATO_DEV_WORKSPACE") == "1":
                target_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

            cls._BASE_DATA_DIR = target_dir

        cls.ensure_directories()
        return cls._BASE_DATA_DIR

    @classmethod
    def ensure_directories(cls):
        base = cls.get_base_data_dir()
        for sub in ["data", "logs", "backups", "receipts", "exports", "config"]:
            d = os.path.join(base, sub)
            os.makedirs(d, exist_ok=True)

    @classmethod
    def get_db_path(cls):
        base = cls.get_base_data_dir()
        # Look in data/ directory
        data_dir_db = os.path.join(base, "data", "pharmacy_db.sqlite")
        root_db = os.path.join(base, "pharmacy_db.sqlite")
        if os.path.exists(root_db) and not os.path.exists(data_dir_db):
            return root_db
        return data_dir_db

    @classmethod
    def get_logs_dir(cls):
        return os.path.join(cls.get_base_data_dir(), "logs")

    @classmethod
    def get_backups_dir(cls):
        return os.path.join(cls.get_base_data_dir(), "backups")

    @classmethod
    def get_receipts_dir(cls):
        return os.path.join(cls.get_base_data_dir(), "receipts")

    @classmethod
    def get_exports_dir(cls):
        return os.path.join(cls.get_base_data_dir(), "exports")

    @classmethod
    def get_config_dir(cls):
        return os.path.join(cls.get_base_data_dir(), "config")
