"""Summarise score stability per meal, model and condition, and draw the figures.

Usage:
    python src/analyze.py                          # results/raw.jsonl
    python src/analyze.py --input results/mock_raw.jsonl
"""

from __future__ import annotations

import argparse
import json
import math
import tomllib
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CATEGORY_ORDER = ["clear_bad", "borderline", "clear_good"]
ANSWERED = ["ok", "parse_failed", "truncated"]


def load(path: Path) -> pd.DataFrame:
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    return pd.DataFrame(rows)


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion. Behaves sensibly at 0 and n,
    where the usual normal interval collapses to zero width."""
    if n == 0:
        return (math.nan, math.nan)
    p = successes / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def per_meal(df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    answered = df[df["status"].isin(ANSWERED)]
    groups = []
    for (prov, model, cond, meal, cat), g in answered.groupby(["provider", "model", "condition", "meal", "category"]):
        s = g["score"].dropna().astype(int)
        n = len(s)
        if n == 0:
            continue
        above = int((s > threshold).sum())
        p_above = above / n
        lo, hi = wilson_interval(above, n)
        groups.append({
            "provider": prov, "model": model, "condition": cond, "meal": meal, "category": cat,
            "n": n,
            "parse_failures": int((g["status"] == "parse_failed").sum()),
            "truncated": int((g["status"] == "truncated").sum()),
            "mean": s.mean(), "sd": s.std(ddof=1) if n > 1 else 0.0,
            "min": s.min(), "max": s.max(), "distinct_scores": s.nunique(),
            "modal_share": s.value_counts().iloc[0] / n,
            # Share of runs scoring above the threshold, with a 95% interval:
            # with 20 runs a single flip moves this by 0.05.
            "p_suitable": p_above, "p_suitable_lo": lo, "p_suitable_hi": hi,
            # Share of runs landing on the minority side of the threshold.
            # 0 means every run gave the same verdict; 0.5 is a coin flip.
            "verdict_instability": min(p_above, 1 - p_above),
            "distance_from_threshold": abs(s.mean() - threshold),
        })
    return pd.DataFrame(groups)


def per_category(summary: pd.DataFrame) -> pd.DataFrame:
    out = (summary.groupby(["model", "condition", "category"])
           .agg(meals=("meal", "count"), mean_sd=("sd", "mean"),
                mean_instability=("verdict_instability", "mean"),
                meals_with_any_flip=("verdict_instability", lambda x: int((x > 0).sum())))
           .reset_index())
    out["category"] = pd.Categorical(out["category"], CATEGORY_ORDER, ordered=True)
    return out.sort_values(["model", "condition", "category"])


def rank_corr(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (model, cond), g in summary.groupby(["model", "condition"]):
        if len(g) > 2 and g["sd"].nunique() > 1:
            rho = g["distance_from_threshold"].rank().corr(g["sd"].rank())
            rows.append({"model": model, "condition": cond, "meals": len(g),
                         "spearman_distance_vs_sd": round(rho, 3)})
    return pd.DataFrame(rows)


def served_models(df: pd.DataFrame) -> pd.DataFrame:
    """Which model the API reports actually answered, per configured model ID."""
    if "served_model" not in df:
        return pd.DataFrame()
    answered = df[df["status"].isin(ANSWERED)]
    return (answered.groupby(["model", "served_model"], dropna=False).size()
            .rename("calls").reset_index())


def token_totals(df: pd.DataFrame) -> pd.DataFrame:
    if "output_tokens" not in df:
        return pd.DataFrame()
    answered = df[df["status"].isin(ANSWERED)]
    return (answered.groupby("model")
            .agg(calls=("status", "size"), input_tokens=("input_tokens", "sum"),
                 output_tokens=("output_tokens", "sum"), mean_output_tokens=("output_tokens", "mean"))
            .round(1).reset_index())


def plot_strip(df: pd.DataFrame, meals_order: list[str], threshold: float, path: Path) -> None:
    ok = df[df["score"].notna()]
    combos = list(ok.groupby(["model", "condition"]).groups)
    fig, axes = plt.subplots(len(combos), 1, figsize=(10, 3.2 * len(combos)), squeeze=False)
    for ax, (model, cond) in zip(axes[:, 0], combos):
        g = ok[(ok["model"] == model) & (ok["condition"] == cond)]
        for i, meal in enumerate(meals_order):
            counts = g[g["meal"] == meal]["score"].astype(int).value_counts()
            for score, c in counts.items():
                ax.scatter(i, score, s=18 + 14 * c, color="#3b6ea5", alpha=0.75)
        ax.axhline(threshold, color="#b23b3b", linestyle="--", linewidth=1)
        ax.set_xticks(range(len(meals_order)))
        ax.set_xticklabels(meals_order, rotation=35, ha="right", fontsize=8)
        ax.set_ylim(-3, 103)
        ax.set_ylabel("score")
        ax.set_title(f"{model}  |  {cond}  (marker size = number of runs)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_sd_vs_distance(summary: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4.5))
    markers = {"clear_bad": "v", "borderline": "o", "clear_good": "^"}
    for (model, cond), g in summary.groupby(["model", "condition"]):
        for cat, gc in g.groupby("category"):
            ax.scatter(gc["distance_from_threshold"], gc["sd"], marker=markers.get(cat, "o"),
                       alpha=0.75, label=f"{model} {cond} {cat}")
    ax.set_xlabel("distance of mean score from threshold")
    ax.set_ylabel("standard deviation across runs")
    ax.set_title("Is variance concentrated near the decision threshold?")
    ax.legend(fontsize=6, loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(ROOT / "results/raw.jsonl"))
    ap.add_argument("--config", default=str(ROOT / "experiment.toml"))
    args = ap.parse_args()

    cfg = tomllib.loads(Path(args.config).read_text())
    threshold = cfg["analysis"]["threshold"]
    meals_order = [m["name"] for m in sorted(cfg["meals"], key=lambda m: CATEGORY_ORDER.index(m["category"]))]

    inp = Path(args.input)
    prefix = "mock_" if inp.name.startswith("mock") else ""
    df = load(inp)

    status = df.groupby(["model", "condition", "status"]).size().rename("calls").reset_index()
    summary = per_meal(df, threshold)
    cats = per_category(summary)
    corr = rank_corr(summary)
    served = served_models(df)
    tokens = token_totals(df)

    res, figs = ROOT / "results", ROOT / "figures"
    figs.mkdir(exist_ok=True)
    summary.round(3).to_csv(res / f"{prefix}summary_per_meal.csv", index=False)
    with open(res / f"{prefix}summary.md", "w") as fh:
        fh.write(f"# Results summary\n\nThreshold: scores above {threshold} count as suitable.\n\n")
        fh.write("## Call outcomes\n\n"
                 "`truncated` means the answer hit max_tokens before giving a score; "
                 "`parse_failed` covers missing, decimal or range scores.\n\n"
                 + status.to_markdown(index=False) + "\n\n")
        if len(served):
            fh.write("## Models as reported by the API\n\n" + served.to_markdown(index=False) + "\n\n")
        fh.write("## By category\n\n" + cats.round(3).to_markdown(index=False) + "\n\n")
        fh.write("## Variance vs distance from threshold (Spearman)\n\n"
                 "Negative means meals closer to the threshold vary more. On a bounded 0 to 100 scale, "
                 "meals scored near 0 or 100 have little room to vary, so part of any negative value "
                 "comes from the scale itself; the flip rates per meal are the stronger evidence.\n\n"
                 + (corr.to_markdown(index=False) if len(corr) else "_Not enough variation to compute._") + "\n\n")
        fh.write("## Per meal\n\n"
                 "`p_suitable` is the share of runs above the threshold, with a 95% Wilson interval "
                 "(`p_suitable_lo` to `p_suitable_hi`).\n\n"
                 + summary.round(2).to_markdown(index=False) + "\n\n")
        if len(tokens):
            fh.write("## Tokens\n\n" + tokens.to_markdown(index=False) + "\n")
    plot_strip(df, meals_order, threshold, figs / f"{prefix}scores_by_meal.png")
    plot_sd_vs_distance(summary, figs / f"{prefix}sd_vs_distance.png")
    print((res / f"{prefix}summary.md").read_text())


if __name__ == "__main__":
    main()
