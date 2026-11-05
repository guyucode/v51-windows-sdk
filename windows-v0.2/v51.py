"""Thin ctypes binding only. Solver implementation is in the native DLL."""
import ctypes
import json
from pathlib import Path
import platform
import sys
import sysconfig
import threading
import time

def _default_dll():
    if sys.platform != "win32":
        raise OSError("This binary package requires Windows. Use 64-bit Python.")
    if ctypes.sizeof(ctypes.c_void_p) != 8:
        raise OSError("32-bit Python cannot load these DLLs. Install ARM64 or x64 Python.")
    target = sysconfig.get_platform().lower()
    if "arm64" in target:
        folder = "arm64"
    elif "amd64" in target or "x86_64" in target:
        folder = "x64"
    else:
        raise OSError("Cannot identify Python process architecture: " + target)
    return Path(__file__).resolve().parent / folder / "v51_solver.dll"

class Solver:
    def __init__(self, seconds=5.0, seed=11, backend="gpu", dll_path=None, proof_seconds=0.05):
        self.path = Path(dll_path) if dll_path else _default_dll()
        self._lib = ctypes.CDLL(str(self.path.resolve()))
        self._lock = threading.RLock()
        self._life = threading.RLock()
        lib = self._lib
        lib.v51_create.argtypes = [ctypes.c_char_p]
        lib.v51_create.restype = ctypes.c_void_p
        for name in ("v51_version", "v51_last_error"):
            getattr(lib, name).argtypes = []
            getattr(lib, name).restype = ctypes.c_char_p
        lib.v51_solve_json.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        lib.v51_solve_json.restype = ctypes.c_char_p
        lib.v51_diagnostics.argtypes = [ctypes.c_void_p]
        lib.v51_diagnostics.restype = ctypes.c_char_p
        lib.v51_self_test.argtypes = [ctypes.c_void_p, ctypes.c_int]
        lib.v51_self_test.restype = ctypes.c_char_p
        for name in ("v51_cancel", "v51_destroy"):
            getattr(lib, name).argtypes = [ctypes.c_void_p]
            getattr(lib, name).restype = None
        lib.v51_verify_certificate_json.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        lib.v51_verify_certificate_json.restype = ctypes.c_char_p
        lib.v51_general_gpu_self_test.argtypes = []
        lib.v51_general_gpu_self_test.restype = ctypes.c_char_p
        config = json.dumps(dict(seconds=seconds, seed=seed, backend=backend, proof_seconds=proof_seconds), allow_nan=False).encode("utf-8")
        self._handle = lib.v51_create(config)
        if not self._handle:
            error = lib.v51_last_error()
            raise ValueError(error.decode("utf-8") if error else "Native context initialization failed")

    def _open(self):
        if not self._handle:
            raise RuntimeError("Solver is closed")

    @property
    def version(self):
        return self._lib.v51_version().decode("utf-8")

    def solve(self, model):
        with self._lock:
            self._open()
            start = time.perf_counter()
            payload = json.dumps(model, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
            result = json.loads(self._lib.v51_solve_json(self._handle, payload).decode("utf-8"))
            result["python_full_call_seconds"] = time.perf_counter() - start
            return result

    def diagnostics(self):
        with self._lock:
            self._open()
            result = json.loads(self._lib.v51_diagnostics(self._handle).decode("utf-8"))
            result.update(python_version=sys.version, python_platform=sysconfig.get_platform(), machine=platform.machine(), dll_path=str(self.path))
            return result

    def self_test(self, gpu=True):
        with self._lock:
            self._open()
            return json.loads(self._lib.v51_self_test(self._handle, int(gpu)).decode("utf-8"))

    def cancel(self):
        with self._life:
            if self._handle:
                self._lib.v51_cancel(self._handle)

    def close(self):
        with self._lock, self._life:
            handle, self._handle = self._handle, None
            if handle:
                self._lib.v51_destroy(handle)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def __del__(self):
        if hasattr(self, "_handle"):
            self.close()

    def verify_certificate(self, model, certificate):
        a=json.dumps(model,allow_nan=False).encode("utf-8")
        b=json.dumps(certificate,allow_nan=False).encode("utf-8")
        return json.loads(self._lib.v51_verify_certificate_json(a,b).decode("utf-8"))

    def general_gpu_self_test(self):
        return json.loads(self._lib.v51_general_gpu_self_test().decode("utf-8"))
