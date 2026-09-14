"""Restore the exact project package backup after the 3.2.9 live regression."""
import shutil
import subprocess
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[2]
    site = root / ".venv/Lib/site-packages"
    backup = root / ".third-eyes/package-update-3.2.9"
    python = root / ".venv/Scripts/python.exe"
    names = ("vnstock_data", "vnstock_data-3.2.8.dist-info")
    for name in names:
        if not (backup / name).is_dir():
            raise RuntimeError(f"Missing rollback backup: {name}")
    current = subprocess.check_output([str(python), "-c",
                                      "from importlib.metadata import version; print(version('vnstock_data'))"], text=True).strip()
    if current != "3.2.9":
        raise RuntimeError("Rollback only applies to the tested 3.2.9 installation")
    subprocess.run([str(python), "-m", "pip", "uninstall", "-y", "vnstock_data"], check=True)
    for name in names:
        shutil.copytree(backup / name, site / name, dirs_exist_ok=True)
    subprocess.run([str(python), "-m", "pip", "check"], check=True)
    print("Restored project vnstock_data 3.2.8 from pre-upgrade backup", flush=True)


if __name__ == "__main__":
    main()
