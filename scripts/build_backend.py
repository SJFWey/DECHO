import subprocess
import sys
from pathlib import Path


def build_backend():
    """
    Builds the backend server into a standalone executable using PyInstaller.
    """
    project_root = Path(__file__).parent.parent
    server_entry = project_root / "server" / "main.py"

    if not server_entry.exists():
        print(f"Error: Could not find server entry point at {server_entry}")
        sys.exit(1)

    print(f"Building backend from {server_entry}...")

    # Define PyInstaller arguments
    # We use --onedir for faster startup and easier debugging initially,
    # but --onefile is often preferred for distribution.
    # For sidecars, --onedir is often fine and sometimes faster.
    # Let's stick to --onedir for now as it's the default.

    # We need to ensure we collect necessary data files if any.
    # For now, we'll just build the main script.

    cmd = [
        "pyinstaller",
        "--name=decho-server",
        "--clean",
        "--noconfirm",
        "--distpath=dist",
        "--workpath=build",
        "--onefile",
        # Add hidden imports if necessary (FastAPI/Uvicorn often need them)
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.lifespan",
        "--hidden-import=uvicorn.lifespan.on",
        "--hidden-import=engineio.async_drivers.aiohttp",
        # Add data folders
        "--add-data=config.yaml;.",
        # Point to the main entry file
        str(server_entry),
    ]

    # Run PyInstaller
    try:
        subprocess.run(cmd, check=True, cwd=project_root)
        print("Backend build completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error building backend: {e}")
        sys.exit(1)


if __name__ == "__main__":
    build_backend()
