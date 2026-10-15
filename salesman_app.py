"""
Pharma-Khaato — Legacy Adapter & Backward-Compatibility Wrapper module.
Delegates main UI execution to the modular PySide6 application entry point (ui.app.application.run_app).
"""

import sys
import os

# Add parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.app.application import run_app

# Backward-compatibility function wrappers delegating to core services
from core.auth_service import login_user
from core.pos_service import confirm_sale

def db_login(username, password):
    return login_user(username, password)

def db_confirm_sale(customer_id, employee_id, cart=None, total=0.0, discount=0.0, payment_method="Cash"):
    return confirm_sale(customer_id, employee_id, cart or [], total=total, discount=discount, payment_method=payment_method)

if __name__ == "__main__":
    sys.exit(run_app() or 0)
