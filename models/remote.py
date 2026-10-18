"""Route desktop facades to a configured shop without a second local store."""
from __future__ import annotations
from dataclasses import fields


class RemoteModel:
    def __init__(self, model_name, client):
        self.model_name = model_name
        self.client = client

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        if name == 'discount_threshold_pct':
            return self.client.call(self.model_name, name)
        def invoke(*args, **kwargs):
            if self.model_name == 'KhatooModel' and name in {'load_pending_payment','save_pending_payment','clear_pending_payment'}:
                from models.services import LOCAL_MODELS
                return getattr(LOCAL_MODELS['KhatooModel'](), name)(*args, **kwargs)
            if self.model_name == 'SettingsModel':
                from core.counter_preferences import KEYS, read, update
                if name == 'get' and args[0] in KEYS:
                    return read().get(args[0], args[1] if len(args)>1 else None)
                if name == 'get_many':
                    keys = args[0]
                    defaults = args[1] if len(args)>1 else kwargs.get('defaults') or {}
                    remote_keys = [key for key in keys if key not in KEYS]
                    values = self.client.call('SettingsModel','get_many',remote_keys,defaults) if remote_keys else {}
                    local = read()
                    values.update({key:local.get(key,defaults.get(key,'')) for key in keys if key in KEYS})
                    return values
                if name == 'set' and args[0] in KEYS:
                    return update({args[0]:args[1]})
                if name == 'update':
                    local = {key:value for key,value in args[0].items() if key in KEYS}
                    business = {key:value for key,value in args[0].items() if key not in KEYS}
                    if business and not self.client.call('SettingsModel','update',business,**kwargs):
                        return False
                    return update(local) if local else True
            if self.model_name == 'AppModel':
                if name in {'initialize_database', 'has_registered_employees'}:
                    status = self.client.public_status()
                    if not status.get('ready'):
                        raise ConnectionError('The main shop computer is not ready. Reconnect before selling.')
                    return status.get('configured') if name == 'has_registered_employees' else None
                if name == 'shutdown':
                    return self.client.logout()
                if name == 'ensure_daily_backup':
                    return True, 'Backups are managed on the main shop computer.'
            if self.model_name == 'AuthModel':
                if name == 'login':
                    return self.client.login(*args, **kwargs)
                if name in {'register_initial_admin', 'complete_initial_setup'}:
                    return False, 'Complete the owner setup on the main shop computer first.'
            if self.model_name == 'POSModel':
                if name == 'checkout_request':
                    from core.pos_service import CheckoutRequest
                    kwargs['terminal_id'] = self.client.terminal_id
                    return CheckoutRequest(**kwargs)
                if name == 'reprint_receipt':
                    from core.receipt_service import print_receipt_spooler
                    saved = self.client.call('POSModel', 'receipt_for_sale', *args, **kwargs)
                    ok = print_receipt_spooler('REPRINT\n' + saved['receipt_text'])
                    return ok, 'Receipt sent to the printer.' if ok else 'Sale is saved. Check this counter printer and retry.'
            request_id = kwargs.get('operation_id')
            if self.model_name == 'POSModel' and name == 'process_checkout' and args:
                request_id = getattr(args[0], 'checkout_token', None)
            result = self.client.call(self.model_name, name, *args, request_id=request_id, **kwargs)
            if self.model_name == 'POSModel' and name in {'process_checkout', 'lookup_checkout_result'} and result is not None:
                from core.pos_service import CheckoutResult
                accepted = {field.name for field in fields(CheckoutResult)}
                converted = CheckoutResult(**{key: value for key, value in result.items() if key in accepted})
                if name == 'process_checkout' and converted.success and not converted.duplicate:
                    from core.counter_preferences import read
                    if str(read().get('receipt_auto_print','0')) == '1':
                        from core.receipt_service import print_receipt_spooler
                        try:
                            saved = self.client.call('POSModel','receipt_for_sale',converted.purchase_id)
                            printed = print_receipt_spooler(saved['receipt_text'])
                        except Exception:
                            printed = False
                        converted.receipt_status = 'SENT_TO_PRINTER' if printed else 'PRINT_PENDING'
                return converted
            if isinstance(result,list) and result and isinstance(result[0],bool):
                return tuple(result)
            return result
        return invoke


def routed_model(local_type):
    class Routed(local_type):
        def __new__(cls, *args, **kwargs):
            from core.lan_config import enabled_counter_client
            client = enabled_counter_client()
            if client is not None:
                return RemoteModel(local_type.__name__, client)
            return super().__new__(cls)
    Routed.__name__ = local_type.__name__
    Routed.__qualname__ = local_type.__qualname__
    return Routed
