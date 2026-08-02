from __future__ import annotations

import argparse
import asyncio
import json
import tempfile
from pathlib import Path

from .agents import AgentLoop
from .memory import MemoryStore
from .models import SearchRequest


async def run_dataset(path: Path, minimum: float = 60) -> dict:
    cases = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    scores, failures = [], []
    with tempfile.NamedTemporaryFile(suffix=".db") as database:
        store = MemoryStore(database.name)
        agent = AgentLoop(store)
        async def sink(_): pass
        for index, case in enumerate(cases, 1):
            response = await agent.run(SearchRequest(**case["request"]), sink)
            score = response.evaluation.overall if response.evaluation else 0
            scores.append(score)
            expected = set(case.get("expected_product_ids", []))
            actual = {item.product.id for item in response.recommendations}
            if score < minimum or not expected.issubset(actual):
                failures.append({"case": index, "score": score, "missing": sorted(expected - actual)})
    return {"cases": len(cases), "average": round(sum(scores) / max(1, len(scores)), 1), "minimum": minimum, "passed": not failures, "failures": failures}


def main():
    parser = argparse.ArgumentParser(description="Run deterministic Best Gift Search quality gates")
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--minimum", type=float, default=60)
    args = parser.parse_args()
    result = asyncio.run(run_dataset(args.dataset, args.minimum))
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
