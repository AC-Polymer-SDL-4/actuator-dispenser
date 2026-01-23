import os
import re
import time
import argparse
import pandas as pd

"""
Parse legacy mass_log.txt entries from tests/testing_act.py and convert them
into a structured calibration CSV compatible with volume_time_analysis.py.

Expected line format (free text, one per run):
  Retraction time: 0.4s, Volume dispensed: 0.25g, Actuator power: 65520

Assumptions:
 - 1 g ≈ 1 mL for water (density ~1 g/mL)
 - Calibration type assumed 'time'
 - No well index recorded; we set -1
 - Replicates inferred by order within the file per unique time bucket
"""


LINE_RE = re.compile(
    r"Retraction time:\s*([0-9.]+)s,\s*Volume dispensed:\s*([0-9.]+)g,\s*Actuator power:\s*(\d+)",
    re.IGNORECASE,
)


def parse_mass_log(path: str):
    rows = []
    with open(path, "r") as f:
        for line in f:
            m = LINE_RE.search(line)
            if not m:
                continue
            time_s = float(m.group(1))
            vol_ml = float(m.group(2))  # assume water density
            speed = int(m.group(3))
            rows.append({
                "calibration_type": "time",
                "replicate": None,  # assign later
                "well_index": -1,
                "target_time_s": time_s,
                "target_volume_ml": None,
                "measured_volume_ml": vol_ml,
                "air_time_s": None,
                "buffer_time_s": None,
                "speed": speed,
                "timestamp": None,
            })
    return rows


def assign_replicates(rows):
    # Group by target_time_s and assign incrementing replicate numbers
    by_time = {}
    for r in rows:
        t = r["target_time_s"]
        by_time.setdefault(t, 0)
        by_time[t] += 1
        r["replicate"] = by_time[t]
        r["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    return rows


def main():
    ap = argparse.ArgumentParser(description="Convert mass_log.txt to calibration CSV")
    ap.add_argument("--input", default="mass_log.txt", help="Path to mass_log.txt")
    ap.add_argument("--outdir", default=os.path.join("output", "calibration", f"imported_mass_log_{time.strftime('%Y%m%d_%H%M%S')}"),
                    help="Output directory for calibration CSV")
    args = ap.parse_args()

    if not os.path.exists(args.input):
        print(f"No input file found at: {args.input}")
        return 1

    rows = parse_mass_log(args.input)
    if not rows:
        print("No parseable lines found. Ensure mass_log.txt contains lines in expected format.")
        return 1

    rows = assign_replicates(rows)

    os.makedirs(args.outdir, exist_ok=True)
    out_csv = os.path.join(args.outdir, "calibration_measurements.csv")
    df = pd.DataFrame(rows)
    df.to_csv(out_csv, index=False)
    print(f"Wrote {len(rows)} rows → {out_csv}")
    print("You can now run: tests/calibration/volume_time_analysis.py to plot.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
