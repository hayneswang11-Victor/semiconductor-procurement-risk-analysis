from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
scripts=[
    "00_generate_synthetic_data.py",
    "01_validate_data.py",
    "02_compute_metrics.py",
    "03_run_scenarios.py",
    "04_monte_carlo.py",
    "05_eda_ip_extension.py"
]
for script in scripts:
    print("\n"+"="*70)
    print("RUNNING:",script)
    print("="*70)
    subprocess.run([sys.executable,str(ROOT/"src"/script)],check=True)
print("\nPipeline completed successfully.")
