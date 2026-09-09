from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"


def run_script(filename: str) -> None:
    script_path = SCRIPTS_DIR / filename

    print(f"Running {filename}...")
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=ROOT,
    )

    if result.returncode != 0:
        raise SystemExit(f"{filename} failed with exit code {result.returncode}")


def main() -> None:
    run_script("fetch_data.py")
    run_script("build_warehouse.py")

    print("")
    print("Project setup completed successfully.")


if __name__ == "__main__":
    main()
