"""Use the installed official sponsor client to update only the project venv."""
import json
import logging
import shutil
import subprocess
from pathlib import Path

from vnstock_installer import config
from vnstock_installer.api import VnstockAPIClient


def main():
    root = Path(__file__).resolve().parents[2]
    python = root / ".venv/Scripts/python.exe"
    target = root / ".third-eyes/package-update-3.2.9"
    target.mkdir(parents=True, exist_ok=True)
    logging.disable(logging.CRITICAL)
    # Existing credential stays in memory; never print keys or signed URLs.
    key = json.loads(config.API_KEY_FILE.read_text(encoding="utf-8"))["api_key"]
    config.base_url = "https://vnstocks.com"
    client = VnstockAPIClient(key, python_executable=str(python))
    ok, catalog = client.list_available_packages()
    if not ok:
        raise RuntimeError("Official package catalog unavailable")
    package = next(p for p in catalog["packages"] if p["name"] == "vnstock_data")
    print("Official vnstock_data version:", package["version"], flush=True)
    if package["version"] != "3.2.9":
        raise RuntimeError("Catalog version changed; review before installing")
    site = root / ".venv/Lib/site-packages"
    for name in ("vnstock_data", "vnstock_data-3.2.8.dist-info"):
        source = site / name
        backup = target / name
        if source.exists() and not backup.exists():
            shutil.copytree(source, backup)
    ok, archive = client.download_package("vnstock_data")
    if not ok:
        raise RuntimeError("Official package download failed")
    local = target / "vnstock_data-3.2.9.tar.gz"
    shutil.copyfile(archive, local)
    subprocess.run([str(python), "-m", "pip", "install", "--no-deps", str(local)], check=True)
    subprocess.run([str(python), "-c", "from importlib.metadata import version; print('Installed vnstock_data:', version('vnstock_data'))"], check=True)


if __name__ == "__main__":
    main()
