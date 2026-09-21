"""Run the complete IOM209 individual analysis pipeline."""

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
SCRIPTS = [
    "01_build_energy_mapping.py",
    "02_build_external_factors.py",
    "03_build_model_dataset.py",
    "04_run_models.py",
]


def main() -> None:
    for script in SCRIPTS:
        path = ROOT / "scripts" / script
        print(f"\n=== Running {script} ===", flush=True)
        subprocess.run([sys.executable, str(path)], check=True)


if __name__ == "__main__":
    main()
