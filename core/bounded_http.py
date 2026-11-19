"""Bound concurrent connections and TLS/header/body time on the shop host."""
from http.server import ThreadingHTTPServer
import socket
import ssl
import threading


class BoundedTLSHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 32

    def __init__(self, address, handler, context, *, max_connections=32, timeout=10, per_peer_connections=4):
        self._peer_limit = max(1, int(per_peer_connections))
        self._peers = {}
        self._peer_lock = threading.Lock()
        self.context = context
        self.timeout_seconds = timeout
        self._slots = threading.BoundedSemaphore(max_connections)
        super().__init__(address, handler)

    def process_request(self, request, client_address):
        peer = client_address[0]
        with self._peer_lock:
            if self._peers.get(peer, 0) >= self._peer_limit:
                self.shutdown_request(request)
                return
            if not self._slots.acquire(blocking=False):
                self.shutdown_request(request)
                return
            self._peers[peer] = self._peers.get(peer, 0) + 1
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._release_peer(peer)
            raise

    def process_request_thread(self, request, client_address):
        connection = request
        # A total connection deadline also bounds a peer trickling one byte
        # before each socket inactivity timeout. Close wakes blocked reads.
        deadline = None
        try:
            request.settimeout(self.timeout_seconds)
            connection = self.context.wrap_socket(request, server_side=True, do_handshake_on_connect=False)
            deadline = threading.Timer(self.timeout_seconds, self._expire, args=(connection,))
            deadline.daemon = True
            deadline.start()
            connection.do_handshake()
            self.finish_request(connection, client_address)
        except (OSError, ssl.SSLError):
            pass  # Expected on disconnect, bad TLS or expired deadline; no credentials logged.
        except Exception:
            self.handle_error(connection, client_address)
        finally:
            if deadline is not None:
                deadline.cancel()
            self.shutdown_request(connection)
            if hasattr(self, '_peer_lock'):
                self._release_peer(client_address[0])
            else:
                self._slots.release()  # Isolated test harness without an accept loop.

    def _release_peer(self, peer):
        with self._peer_lock:
            count = self._peers.get(peer, 0) - 1
            if count > 0:
                self._peers[peer] = count
            else:
                self._peers.pop(peer, None)
            self._slots.release()

    @staticmethod
    def _expire(connection):
        try:
            connection.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
