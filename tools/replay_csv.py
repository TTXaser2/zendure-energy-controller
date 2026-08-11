#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Lightweight CLI entry point for Zendure Energy Controller V12.8.4 CSV analysis.

import argparse
try:
    from replay_core import AnalysisLimits, analyze_files
    from replay_report import text_report
except ImportError:  # allows python -m tools.replay_csv
    from tools.replay_core import AnalysisLimits, analyze_files
    from tools.replay_report import text_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Analysiert aktuelle ZEC-MEASUREMENT-V4-Dateien sowie historische V3-Dateien read-only.")
    parser.add_argument("csv_files", nargs="+", help="Eine oder mehrere V4-Dateien; historische V3-Dateien werden nur read-only unterstützt")
    parser.add_argument("--min-soc", type=int, default=15)
    parser.add_argument("--max-soc", type=int, default=99)
    parser.add_argument("--max-files", type=int, default=10)
    parser.add_argument("--max-mb", type=int, default=50)
    parser.add_argument("--max-rows", type=int, default=500000)
    args = parser.parse_args()
    limits = AnalysisLimits(max_files=args.max_files, max_total_bytes=args.max_mb * 1024 * 1024, max_rows=args.max_rows)
    result = analyze_files(args.csv_files, min_soc_percent=args.min_soc, max_soc_percent=args.max_soc, limits=limits)
    print(text_report(result))


if __name__ == "__main__":
    main()
