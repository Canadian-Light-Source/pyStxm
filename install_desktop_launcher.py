#!/usr/bin/env python3
"""Install a KDE launcher for this checkout without committing local paths."""

import os
from pathlib import Path
import shutil
import subprocess
import sys


def desktop_value(value):
    """Escape a string for the Desktop Entry file format."""
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")


def exec_argument(value):
    """Quote one Exec argument, including Desktop Entry and Exec escaping."""
    value = value.replace("%", "%%")
    for character in ("\\", '"', "`", "$"):
        value = value.replace(character, "\\" + character)
    return desktop_value('"' + value + '"')


def main():
    repo_dir = Path(__file__).resolve().parent
    icon_path = repo_dir / "pyStxm.png"
    if not icon_path.is_file():
        sys.exit(f"Launcher icon not found: {icon_path}")
    conda_exe = os.environ.get("CONDA_EXE") or shutil.which("conda")
    if not conda_exe or not os.access(conda_exe, os.X_OK):
        sys.exit("Conda not found. Run this installer from a terminal where Conda is available.")
    for command in ("konsole", "xdg-user-dir"):
        if not shutil.which(command):
            sys.exit(f"Required command not found: {command}")

    desktop_dir = subprocess.check_output(["xdg-user-dir", "DESKTOP"], text=True).strip()
    if not desktop_dir:
        sys.exit("No desktop directory is configured.")
    destination = Path(desktop_dir) / "pyStxm.desktop"
    if not destination.parent.is_dir():
        sys.exit(f"Desktop directory does not exist: {destination.parent}")

    # Only the installed copy contains paths specific to this machine.
    launcher = (repo_dir / "pyStxm.desktop.in").read_text()
    replacements = {
        "@CONDA_EXE@": exec_argument(f"CONDA_EXE={Path(conda_exe).resolve()}"),
        "@RUN_SCRIPT@": exec_argument(str(repo_dir / "runpyStxm.sh")),
        "@REPO_DIR@": desktop_value(str(repo_dir)),
        "@ICON_PATH@": desktop_value(str(icon_path)),
    }
    for placeholder, value in replacements.items():
        launcher = launcher.replace(placeholder, value)
    destination.write_text(launcher)
    destination.chmod(0o755)
    print(f"Installed {destination}")


if __name__ == "__main__":
    main()
