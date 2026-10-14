from PySide6.QtCore import QObject, Signal, Runnable, QThreadPool, Slot

class WorkerSignals(QObject):
    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)

class AsyncWorker(Runnable):
    """
    QRunnable wrapper for executing backend tasks (search, checkout, reports, backups)
    asynchronously on background threads without stalling the PySide6 main GUI event loop.
    """
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        try:
            res = self.fn(*self.args, **self.kwargs)
            self.signals.result.emit(res)
        except Exception as e:
            import sys, traceback
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        finally:
            self.signals.finished.emit()

def run_async(fn, callback=None, error_callback=None, *args, **kwargs):
    """
    Convenience helper to dispatch any python function onto the global Qt thread pool.
    """
    worker = AsyncWorker(fn, *args, **kwargs)
    if callback:
        worker.signals.result.connect(callback)
    if error_callback:
        worker.signals.error.connect(error_callback)
    QThreadPool.globalInstance().start(worker)
    return worker
