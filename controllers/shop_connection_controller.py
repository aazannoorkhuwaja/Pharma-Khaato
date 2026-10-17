"""Connection configuration boundary for the desktop's setup dialog."""


class ShopConnectionController:
    @staticmethod
    def standalone():
        from core.lan_config import use_standalone
        return use_standalone()

    @staticmethod
    def host(address, port):
        from core.lan_config import save_host_config
        return save_host_config(address, port)

    @staticmethod
    def connect(address, certificate, terminal):
        from core.lan_config import save_counter_config
        from core.lan_client import LanClient
        if not LanClient(address, certificate, terminal, timeout=8).public_status().get('configured'):
            raise ValueError('Create the owner account on the main computer before connecting this counter.')
        return save_counter_config(address, certificate, terminal)
