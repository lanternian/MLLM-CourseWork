from .cli import main
from .planner import PlanningError


if __name__ == "__main__":
    try:
        main()
    except PlanningError as exc:
        raise SystemExit(str(exc)) from exc
