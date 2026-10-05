"""
CLI Script: Run Research Benchmark and Generate Results Table
============================================================
Usage:
    python scripts/run_research_benchmark.py --trials 5 --batches 300
"""

import argparse
import sys
from pathlib import Path

# Add backend and research to python path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "backend"))
sys.path.insert(0, str(repo_root))

from research.experiments.run_experiments import run_comprehensive_benchmark


def main():
    parser = argparse.ArgumentParser(description="Run research benchmark evaluation across models and ablations.")
    parser.add_argument("--trials", type=int, default=5, help="Number of random seeds / trials")
    parser.add_argument("--batches", type=int, default=300, help="Number of batches per trial")

    args = parser.parse_args()

    results = run_comprehensive_benchmark(n_trials=args.trials, n_batches=args.batches)
    print("\nBenchmark Execution Complete. Review research/results/tables/benchmark_results.md for published tables.")


if __name__ == "__main__":
    main()
