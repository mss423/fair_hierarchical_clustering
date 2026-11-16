"""Command-line entry points; no network access is needed by any command."""

import argparse
import json


def main():
    parser = argparse.ArgumentParser(prog="fair-hc")
    commands = parser.add_subparsers(dest="command", required=True)
    bench = commands.add_parser("benchmark", help="Run a sequential reproducible study")
    bench.add_argument("--config", required=True)
    bench.add_argument("--output", required=True)
    bench.add_argument("--data-dir", default="data/raw")
    bench.add_argument("--resume", action="store_true")
    bench.add_argument("--memory-gib", type=float, default=8.0)
    bench.add_argument("--time-limit", type=float)
    plot = commands.add_parser("plot", help="Plot saved results without rerunning algorithms")
    plot.add_argument("--results", required=True)
    plot.add_argument("--output", required=True)
    demo = commands.add_parser("demo", help="Generate a self-contained offline trace walkthrough")
    demo.add_argument("--output", default="docs/demo.html")
    args = parser.parse_args()
    if args.command == "benchmark":
        from .benchmark import run_benchmark

        try:
            result = run_benchmark(
                args.config,
                args.output,
                data_dir=args.data_dir,
                resume=args.resume,
                memory_gib=args.memory_gib,
                time_limit=args.time_limit,
            )
        except (ValueError, FileNotFoundError) as exc:
            parser.error(str(exc))
        print(json.dumps(result.get("status_counts", {}), indent=2))
        if not result.get("complete", False):
            raise SystemExit(2)
    elif args.command == "plot":
        from .plotting import plot_results

        plot_results(args.results, args.output)
    else:
        from .demo import create_demo

        create_demo(args.output)


if __name__ == "__main__":
    main()
