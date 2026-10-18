"""Collect repeated, independent scores for each meal from each model.

Usage:
    python src/run_experiment.py                 # real providers with API keys set
    python src/run_experiment.py --mock          # offline pipeline test
    python src/run_experiment.py --runs 3        # quick smoke test

Results are appended to a JSONL file, one line per call. Re-running resumes:
any (provider, model, condition, meal, run) with a final answer is skipped,
and calls that ended in an error are tried again.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import tomllib
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from parse import parse_score  # noqa: E402
from providers import PROVIDERS, TRUNCATION_REASONS, TemperatureUnsupported, has_credentials, is_retryable  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONDITION_TEMPERATURE = {"default": None, "t0": 0.0}
MAX_ATTEMPTS = 4

# Statuses that are a final answer for that call. "error" is not: those calls
# are retried on the next run instead of silently shrinking the sample.
FINAL_STATUSES = {"ok", "parse_failed", "truncated", "refused", "temperature_unsupported"}

# Stop reasons meaning the model declined to answer, so no score was ever given.
REFUSAL_REASONS = {"refusal"}


def load_config(path: Path) -> dict:
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def read_progress(path: Path) -> tuple[set[tuple], set[tuple]]:
    """Return the calls already answered and the (provider, model, condition)
    combinations already known to reject temperature."""
    done, unsupported = set(), set()
    if path.exists():
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r["status"] in FINAL_STATUSES:
                done.add((r["provider"], r["model"], r["condition"], r["meal"], r["run"]))
            if r["status"] == "temperature_unsupported":
                unsupported.add((r["provider"], r["model"], r["condition"]))
    return done, unsupported


def classify(score: int | None, stop_reason: str | None) -> str:
    if score is not None:
        return "ok"
    if stop_reason in REFUSAL_REASONS:
        return "refused"
    return "truncated" if stop_reason in TRUNCATION_REASONS else "parse_failed"


def one_call(provider: str, model: str, condition: str, meal: dict, run: int, prompt: str, max_tokens: int) -> dict:
    fn, _ = PROVIDERS[provider]
    record = {
        "provider": provider, "model": model, "condition": condition,
        "meal": meal["name"], "category": meal["category"], "run": run,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    temperature = CONDITION_TEMPERATURE[condition]
    for attempt in range(1, MAX_ATTEMPTS + 1):
        started = time.monotonic()
        try:
            reply = fn(model, prompt, temperature, max_tokens)
        except TemperatureUnsupported as exc:
            record.update(status="temperature_unsupported", error=str(exc)[:500], score=None, attempts=attempt)
            return record
        except Exception as exc:
            record.update(status="error", error=f"{type(exc).__name__}: {str(exc)[:500]}", score=None, attempts=attempt)
            if not is_retryable(exc) or attempt == MAX_ATTEMPTS:
                return record
            time.sleep(2 ** attempt)
            continue
        score = parse_score(reply.text)
        record.pop("error", None)
        record.update(
            status=classify(score, reply.stop_reason), text=reply.text, score=score,
            served_model=reply.served_model, stop_reason=reply.stop_reason,
            input_tokens=reply.input_tokens, output_tokens=reply.output_tokens,
            thinking_blocks=reply.thinking_blocks, refusal_category=reply.refusal_category,
            latency_s=round(time.monotonic() - started, 3), attempts=attempt,
        )
        return record
    return record


def print_run_summary(records: list[dict]) -> None:
    if not records:
        return
    print("\nThis run:")
    for (model, status), n in sorted(Counter((r["model"], r["status"]) for r in records).items()):
        print(f"  {model:40} {status:24} {n}")
    tokens: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for r in records:
        tokens[r["model"]][0] += r.get("input_tokens") or 0
        tokens[r["model"]][1] += r.get("output_tokens") or 0
    print("\nTokens this run (multiply by each model's price to estimate the full run):")
    for model, (tin, tout) in sorted(tokens.items()):
        print(f"  {model:40} input {tin:>9,}  output {tout:>9,}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "experiment.toml"))
    ap.add_argument("--mock", action="store_true", help="use the offline mock provider only")
    ap.add_argument("--runs", type=int, help="override runs_per_condition")
    args = ap.parse_args()

    cfg = load_config(Path(args.config))
    runs = args.runs or cfg["run"]["runs_per_condition"]
    configured = Path(cfg["run"]["output"])
    out = ROOT / (configured.with_name(f"mock_{configured.name}") if args.mock else configured)
    out.parent.mkdir(parents=True, exist_ok=True)

    providers = {"mock": ["mock-model"]} if args.mock else {
        name: spec["models"] for name, spec in cfg["providers"].items() if spec.get("models")
    }
    for name in list(providers):
        if not has_credentials(name):
            print(f"Skipping {name}: no API key in the environment")
            providers.pop(name)
    if not providers:
        sys.exit("No providers to run. Set API keys and model IDs in experiment.toml, or use --mock.")

    done, unsupported = read_progress(out)
    jobs = [
        (p, m, c, meal, r)
        for p, models in providers.items() for m in models
        for c in cfg["run"]["conditions"] for meal in cfg["meals"] for r in range(runs)
        if (p, m, c, meal["name"], r) not in done and (p, m, c) not in unsupported
    ]
    for p, m, c in sorted(unsupported):
        print(f"  {m} rejected temperature for condition {c} on an earlier run; skipping it")
    print(f"{len(jobs)} calls to make ({len(done)} already recorded) -> {out.relative_to(ROOT)}")

    written: list[dict] = []
    with open(out, "a") as fh, ThreadPoolExecutor(max_workers=cfg["run"]["max_workers"] * len(providers)) as pool:
        futures = {
            pool.submit(one_call, p, m, c, meal, r, cfg["prompt"]["template"].format(meal=meal["name"], item=meal["name"]), cfg["run"]["max_tokens"]): (p, m, c)
            for p, m, c, meal, r in jobs
        }
        for i, fut in enumerate(as_completed(futures), 1):
            rec = fut.result()
            key = futures[fut]
            if rec["status"] == "temperature_unsupported":
                if key in unsupported:
                    continue
                unsupported.add(key)
                print(f"  {key[1]} rejects temperature for condition {key[2]}; recorded once")
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            written.append(rec)
            if i % 50 == 0 or i == len(futures):
                print(f"  {i}/{len(futures)} done")
    print_run_summary(written)


if __name__ == "__main__":
    main()
