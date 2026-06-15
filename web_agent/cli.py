from __future__ import annotations

import argparse
from pathlib import Path

from .agent import WebAgent
from .config import Settings
from .evaluation import load_scenarios, run_evaluation
from .planner import PlanningError, QwenVLPlanner


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    settings = Settings.from_file(args.settings) if args.settings else Settings.from_env()

    if args.command == "run":
        planner = QwenVLPlanner(settings)
        result = WebAgent(settings, planner).run(args.task, args.url)
        print(result.model_dump_json(indent=2))
        return

    scenarios = load_scenarios(Path(args.config))
    total = sum(args.repeats or scenario.repeats for scenario in scenarios)
    if args.dry_run:
        print(f"scenarios={len(scenarios)} total_runs={total}")
        for scenario in scenarios:
            print(f"- {scenario.id}: {scenario.task}")
        return

    planner = QwenVLPlanner(settings)
    summary = run_evaluation(
        scenarios=scenarios,
        agent_factory=lambda: WebAgent(settings, planner),
        output_dir=Path(args.output),
        repeats_override=args.repeats,
    )
    print(
        f"Evaluation complete: {summary['successes']}/{summary['total_runs']} "
        f"({summary['success_rate']:.2%})"
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Multimodal web agent")
    parser.add_argument("--settings", default="config.yaml", help="Path to config file")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run one natural-language task")
    run_parser.add_argument("--task", required=True)
    run_parser.add_argument("--url", required=True)

    eval_parser = subparsers.add_parser("eval", help="Run configured real-site demos")
    eval_parser.add_argument("--config", default="demos/scenarios.yaml")
    eval_parser.add_argument("--output", default="artifacts/evaluation")
    eval_parser.add_argument("--repeats", type=int)
    eval_parser.add_argument("--dry-run", action="store_true")
    return parser


if __name__ == "__main__":
    try:
        main()
    except PlanningError as exc:
        raise SystemExit(str(exc)) from exc

