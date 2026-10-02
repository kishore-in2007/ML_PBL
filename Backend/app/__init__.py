from pathlib import Path
import site
import sys


def _prepend_local_venv_site_packages():
    backend_root = Path(__file__).resolve().parents[1]
    candidates = [
        backend_root / "venv" / "Lib" / "site-packages",
        backend_root / ".venv" / "Lib" / "site-packages",
    ]
    for path in candidates:
        if path.exists():
            path_text = str(path)
            if path_text not in sys.path:
                sys.path.insert(0, path_text)
                try:
                    site.addsitedir(path_text)
                except Exception:
                    pass


_prepend_local_venv_site_packages()
