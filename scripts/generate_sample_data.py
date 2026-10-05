"""
CLI Script: Generate Sample Industrial Benchmark Dataset
========================================================
Usage:
    python scripts/generate_sample_data.py --batches 500 --seed 42 --output data/synthetic/benchmark_sample
"""

import argparse
import sys
from pathlib import Path

# Add backend to python path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "backend"))

from app.services.synthetic_generator import SyntheticDataGenerator, GeneratorConfig


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic industrial dataset with ground-truth failure mechanisms.")
    parser.add_argument("--batches", type=int, default=500, help="Number of production batches to simulate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--output", type=str, default="data/synthetic/benchmark_sample", help="Target output directory")

    args = parser.parse_args()

    print(f"Generating synthetic industrial dataset:")
    print(f"  Batches: {args.batches}")
    print(f"  Seed: {args.seed}")
    print(f"  Output directory: {args.output}")

    config = GeneratorConfig(
        n_batches=args.batches,
        random_seed=args.seed,
    )
    generator = SyntheticDataGenerator(config=config)
    generator.save(output_dir=args.output)
    print(f"\nDataset successfully generated and saved to {args.output}!")


if __name__ == "__main__":
    main()
