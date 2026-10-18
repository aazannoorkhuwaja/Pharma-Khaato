"""Scope effects to the workstation handling an authoritative request."""
from contextvars import ContextVar

remote_request = ContextVar('pharma_remote_request', default=False)
