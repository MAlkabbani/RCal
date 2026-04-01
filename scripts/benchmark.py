#!/usr/bin/env python3
import argparse
import time

from rcal.main import calculate_taxes

SCENARIOS: tuple[tuple[float, float], ...] = (
    (0.0, 5.00),
    (100.0, 5.00),
    (883.0, 5.23),
    (2500.0, 5.45),
    (5000.0, 5.75),
    (10000.0, 5.75),
)


def run_benchmark(iterations: int) -> None:
    for revenue_usd, exchange_rate in SCENARIOS:
        calculate_taxes(revenue_usd, exchange_rate)

    started_at = time.perf_counter()
    completed_runs = 0

    for _ in range(iterations):
        for revenue_usd, exchange_rate in SCENARIOS:
            calculate_taxes(
                revenue_usd,
                exchange_rate,
                num_dependents=2,
                pgbl_contribution=500.0,
                alimony=250.0,
            )
            completed_runs += 1

    elapsed = time.perf_counter() - started_at
    avg_ms = (elapsed / completed_runs) * 1000 if completed_runs else 0.0
    runs_per_second = completed_runs / elapsed if elapsed else 0.0

    print("======================================")
    print("       RCal Performance Benchmark     ")
    print("======================================")
    print(f"Scenarios: {len(SCENARIOS)}")
    print(f"Iterations per scenario: {iterations}")
    print(f"Completed calculations: {completed_runs}")
    print(f"Elapsed time: {elapsed:.4f}s")
    print(f"Average per calculation: {avg_ms:.4f} ms")
    print(f"Throughput: {runs_per_second:,.2f} calculations/s")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=5000)
    args = parser.parse_args()
    run_benchmark(args.iterations)


if __name__ == "__main__":
    main()
