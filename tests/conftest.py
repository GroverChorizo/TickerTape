import os
import sys
import threading
from pathlib import Path
import faulthandler
import shutil
import pytest
import uuid

# Ensure tests import from local src directory and repo tools
ROOT = Path(__file__).resolve().parents[1]
SRC = str(ROOT / "src")
ROOT_STR = str(ROOT)
# Insert root first so packages in repo (e.g., tools) can be imported during tests
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)
if SRC not in sys.path:
    sys.path.insert(0, SRC)

_TEST_TIMEOUT_S = float(os.environ.get("PYTEST_TEST_TIMEOUT_S", "30"))
_SESSION_TIMEOUT_S = float(os.environ.get("PYTEST_SESSION_TIMEOUT_S", "300"))
_session_timer: threading.Timer | None = None
_LOCAL_TMP_ROOT = Path(__file__).resolve().parents[1] / "_pytest_local_tmp"
_LOCAL_TMP_ROOT.mkdir(parents=True, exist_ok=True)
_CACHE_PATH = _LOCAL_TMP_ROOT / "cache.json"
os.environ.setdefault("TICKERTAPE_CACHE_PATH", str(_CACHE_PATH))
os.environ["TICKERTAPE_DISABLE_CACHE"] = "0"
os.environ.setdefault("TICKERTAPE_FORCE_SECRETS_CREATE", "1")
_ORIG_MKDIR = Path.mkdir


def _should_ignore_mkdir_exists(path: Path) -> bool:
    try:
        if not str(path).startswith(str(_LOCAL_TMP_ROOT)):
            return False
        return path.name == "parquet" and path.parent.name == "data"
    except Exception:
        return False


def _patched_mkdir(self, mode=0o777, parents=False, exist_ok=False):
    try:
        return _ORIG_MKDIR(self, mode=mode, parents=parents, exist_ok=exist_ok)
    except FileExistsError:
        if _should_ignore_mkdir_exists(self):
            return None
        raise


Path.mkdir = _patched_mkdir


def _hard_exit(kind: str, nodeid: str, timeout_s: float) -> None:
    try:
        faulthandler.dump_traceback(file=sys.stderr, all_threads=True)
    except Exception:
        pass
    try:
        sys.stderr.write(
            f"\nPYTEST {kind} TIMEOUT after {timeout_s:.0f}s: {nodeid}\n"
        )
        sys.stderr.flush()
    except Exception:
        pass
    os._exit(2)


def pytest_sessionstart(session):
    global _session_timer
    if _SESSION_TIMEOUT_S <= 0:
        return
    _session_timer = threading.Timer(
        _SESSION_TIMEOUT_S, _hard_exit, args=("SESSION", "pytest", _SESSION_TIMEOUT_S)
    )
    _session_timer.daemon = True
    _session_timer.start()


def pytest_sessionfinish(session, exitstatus):
    global _session_timer
    if _session_timer:
        _session_timer.cancel()
        _session_timer = None


def pytest_runtest_call(item):
    if _TEST_TIMEOUT_S <= 0:
        item.runtest()
        return
    _clear_cache_file()
    _clear_tmp_path_data_dir(item)
    timer = threading.Timer(
        _TEST_TIMEOUT_S, _hard_exit, args=("TEST", item.nodeid, _TEST_TIMEOUT_S)
    )
    timer.daemon = True
    timer.start()
    try:
        item.runtest()
    finally:
        timer.cancel()


@pytest.fixture
def tmp_path():
    _clear_tmp_root()
    path = None
    keep_tmp = os.environ.get("TICKERTAPE_KEEP_TMP") == "1"
    for _ in range(10):
        candidate = _new_case_dir()
        if (candidate / "data").exists():
            shutil.rmtree(candidate, ignore_errors=True)
            continue
        path = candidate
        break
    if path is None:
        path = _new_case_dir()
    try:
        yield path
    finally:
        if not keep_tmp:
            shutil.rmtree(path, ignore_errors=True)


class _TmpPathFactory:
    def __init__(self, root: Path):
        self._root = root

    def mktemp(self, basename: str, numbered: bool = True) -> Path:
        _clear_tmp_root()
        base = "".join(ch for ch in basename if ch.isalnum() or ch in ("-", "_")) or "tmp"
        if numbered:
            name = f"{base}_{uuid.uuid4().hex}"
            path = self._root / name
            path.mkdir(parents=True, exist_ok=True)
            return path
        path = self._root / base
        path.mkdir(parents=True, exist_ok=True)
        return path


@pytest.fixture
def tmp_path_factory():
    return _TmpPathFactory(_LOCAL_TMP_ROOT)


def _clear_tmp_root() -> None:
    try:
        entries = list(_LOCAL_TMP_ROOT.iterdir())
    except Exception:
        return
    for child in entries:
        try:
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink(missing_ok=True)
        except Exception:
            continue


def _new_case_dir() -> Path:
    for _ in range(20):
        candidate = _LOCAL_TMP_ROOT / f"case_{uuid.uuid4().hex}"
        try:
            candidate.mkdir(parents=True, exist_ok=False)
            return candidate
        except FileExistsError:
            continue
        except Exception:
            continue
    # Fall back: last resort, reuse a random path
    fallback = _LOCAL_TMP_ROOT / f"case_{uuid.uuid4().hex}"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _clear_cache_file() -> None:
    try:
        _CACHE_PATH.unlink(missing_ok=True)
    except Exception:
        return


def _clear_tmp_path_data_dir(item) -> None:
    try:
        tmp_path = item.funcargs.get("tmp_path")
    except Exception:
        return
    if not isinstance(tmp_path, Path):
        return
    data_dir = tmp_path / "data"
    if data_dir.exists():
        try:
            shutil.rmtree(data_dir, ignore_errors=True)
        except Exception:
            return
    cache_file = tmp_path / "cache.json"
    if cache_file.exists():
        try:
            cache_file.unlink(missing_ok=True)
        except Exception:
            return
