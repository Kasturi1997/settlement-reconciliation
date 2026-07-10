from pathlib import Path

from src.build_static_dashboard import build_static_dashboard
from src.generate_synthetic_data import build_synthetic_raw_data
from src.reconciliation_engine import run_reconciliation


def main() -> None:
    project_root = Path(__file__).resolve().parent
    raw_dir = project_root / "data" / "raw"
    processed_dir = project_root / "data" / "processed"
    dashboard_path = project_root / "dashboard" / "static_dashboard.html"

    print("Step 1/3: generating synthetic raw data...")
    raw_frames = build_synthetic_raw_data(raw_dir)
    print(f"Created {sum(len(frame) for frame in raw_frames.values()):,} raw records across {len(raw_frames)} files.")

    print("Step 2/3: running settlement reconciliation...")
    outputs = run_reconciliation(raw_dir=raw_dir, processed_dir=processed_dir)
    print(
        "Reconciled "
        f"{len(outputs['reconciliation_results']):,} merchant settlement rows and found "
        f"{len(outputs['exceptions']):,} exceptions."
    )

    print("Step 3/3: building static dashboard...")
    build_static_dashboard(processed_dir=processed_dir, dashboard_path=dashboard_path)
    print(f"Dashboard written to {dashboard_path}")


if __name__ == "__main__":
    main()
