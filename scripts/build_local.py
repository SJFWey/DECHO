import subprocess
import sys
import shutil
from pathlib import Path


def build_local():
    project_root = Path(__file__).parent.parent
    server_entry = project_root / "server" / "main.py"
    web_out = project_root / "web" / "out"

    if not web_out.exists():
        print("Error: web/out not found. Please run 'npm run build' in web/ first.")
        sys.exit(1)

    print("Building backend...")

    cmd = [
        "pyinstaller",
        "--name=decho-app",
        "--clean",
        "--noconfirm",
        "--distpath=dist_local",
        "--workpath=build_local",
        "--onedir",
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.lifespan",
        "--hidden-import=uvicorn.lifespan.on",
        str(server_entry),
    ]

    subprocess.run(cmd, check=True)

    # Post-build: Copy resources
    dist_dir = project_root / "dist_local" / "decho-app"

    print("Copying web assets...")
    dest_web = dist_dir / "web"
    if dest_web.exists():
        shutil.rmtree(dest_web)
    shutil.copytree(web_out, dest_web)

    print("Copying models...")
    models_dir = project_root / "models"
    dest_models = dist_dir / "models"
    if models_dir.exists():
        if dest_models.exists():
            shutil.rmtree(dest_models)
        shutil.copytree(models_dir, dest_models)
    else:
        print("Warning: models directory not found.")

    print(f"Build complete. Run {dist_dir / 'decho-app.exe'}")


if __name__ == "__main__":
    build_local()
