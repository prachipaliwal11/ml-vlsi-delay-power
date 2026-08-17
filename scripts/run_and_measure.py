import csv
import subprocess
import os
import sys
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed

# Add new manifests here as new gate types come online. Measurement and
# dataset.csv assembly happen in extract_metrics.py, not here -- this
# script's only job is running deck(s) through ngspice in parallel.
GATE_MANIFESTS = {
    "inverter": "data/manifest_inverter.csv",
    "nand2": "data/manifest_nand2.csv",
    "nor2": "data/manifest_nor2.csv",
    "xor2": "data/manifest_xor2.csv",
}


def run_one(deck_file):
    result = subprocess.run(["ngspice", "-b", deck_file], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  FAILED: {deck_file}")
        return False
    print(f"  done: {deck_file}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run SPICE decks through ngspice in parallel.")
    parser.add_argument(
        "--gates", nargs="+", choices=list(GATE_MANIFESTS.keys()), default=None,
        help="Which gate type(s) to run (default: all). E.g. --gates nand2",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-run decks even if their output file already exists (default: skip already-run decks).",
    )
    args = parser.parse_args()

    gate_types = args.gates if args.gates else list(GATE_MANIFESTS.keys())

    deck_files = []
    skipped_existing = 0
    for gate in gate_types:
        manifest_path = GATE_MANIFESTS[gate]
        if not os.path.exists(manifest_path):
            print(f"Skipping {gate}: {manifest_path} not found")
            continue
        with open(manifest_path) as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            if not args.force and os.path.exists(row["output_file"]):
                skipped_existing += 1
                continue
            deck_files.append(row["deck_file"])

    if skipped_existing:
        print(f"Skipping {skipped_existing} decks with existing output (use --force to re-run them).")

    if not deck_files:
        print("No decks to run. Either everything's already simulated, or run the generator scripts first.")
        sys.exit(0)

    max_workers = max(1, os.cpu_count() - 1)
    print(f"Running {len(deck_files)} decks with {max_workers} parallel workers...")

    success, fail = 0, 0
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(run_one, d): d for d in deck_files}
        for future in as_completed(futures):
            if future.result():
                success += 1
            else:
                fail += 1

    print(f"\nDone: {success} succeeded, {fail} failed.")
    print("Now run extract_metrics.py to compute delay/power and build data/dataset.csv")