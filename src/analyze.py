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
ANSWERED = ["ok", "parse_failed", "truncated", "refused"]


CALL_KEY = ["provider", "model", "condition", "meal", "run"]


def load(path: Path) -> pd.DataFrame:
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    return pd.DataFrame(rows)


def latest_per_call(df: pd.DataFrame) -> pd.DataFrame:
    """The runner appends a new row each time it retries a failed call, so
    keep only the most recent row for each call. An error that a later run
    answered then no longer counts as an error.

    Once a model rejects temperature, the runner records that once and never
    makes the rest of that condition's calls, so earlier errors there are
    dropped too: those calls were never going to be answered."""
    if df.empty:
        return df
    latest = df.sort_values("timestamp", kind="stable").drop_duplicates(CALL_KEY, keep="last")
    combo = ["provider", "model", "condition"]
    rejected = latest.loc[latest["status"] == "temperature_unsupported", combo].drop_duplicates()
    if rejected.empty:
        return latest
    flagged = latest.merge(rejected.assign(_rejected=True), on=combo, how="left")["_rejected"].eq(True).to_numpy()
    return latest[~(flagged & (latest["status"] == "error").to_numpy())]


def mark_refusals(df: pd.DataFrame) -> pd.DataFrame:
    """Rows the API ended as a refusal carry no score. The runner now records
    them as "refused"; rows collected before it did were filed as parse
    failures, so relabel those from their recorded stop reason."""
    if df.empty or "stop_reason" not in df:
        return df
    out = df.copy()
    out.loc[(out["status"] == "parse_failed") & (out["stop_reason"] == "refusal"), "status"] = "refused"
    return out


def refusals(df: pd.DataFrame) -> pd.DataFrame:
    """Refused calls per (model, condition, meal), for every meal with any."""
    answered = df[df["status"].isin(ANSWERED)]
    if answered.empty:
        return pd.DataFrame()
    refused_rows = answered[answered["status"] == "refused"]
    cat = "refusal_category" in refused_rows and refused_rows["refusal_category"].notna().any()
    if cat:
        reason = (refused_rows.groupby(["model", "condition", "meal"])["refusal_category"]
                  .agg(lambda s: ", ".join(sorted(s.dropna().unique())) or "unknown"))
    out = (answered.assign(_refused=answered["status"].eq("refused"))
           .groupby(["model", "condition", "meal", "category"])
           .agg(calls=("status", "size"), refused=("_refused", "sum"))
           .reset_index())
    out = out[out["refused"] > 0].reset_index(drop=True)
    if cat:
        out["refusal_category"] = out.apply(lambda r: reason.get((r["model"], r["condition"], r["meal"]), ""), axis=1)
    return out


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
            "refusals": int((g["status"] == "refused").sum()),
            "mean": s.mean(), "sd": s.std(ddof=1) if n > 1 else 0.0,
            "min": s.min(), "max": s.max(), "distinct_scores": s.nunique(),
            "modal_share": s.value_counts().iloc[0] / n,
            # Share of runs scoring above the threshold, with a 95% interval:
            # with 20 runs a single flip moves this by 0.05.
            "p_above": p_above, "p_above_lo": lo, "p_above_hi": hi,
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


def majority_vote_instability(p_above: float, k: int) -> float:
    """Chance that a majority vote of k independent runs lands on the minority
    side, given each run lands above the threshold with probability p_above.
    k is odd so a vote cannot tie; k = 1 is the single-run instability."""
    if k % 2 == 0:
        raise ValueError("k must be odd")
    q = sum(math.comb(k, j) * p_above**j * (1 - p_above) ** (k - j) for j in range(k // 2 + 1, k + 1))
    return min(q, 1 - q)


def voting_table(summary: pd.DataFrame, ks: tuple[int, ...] = (1, 3, 5, 9)) -> pd.DataFrame:
    """Mean instability per model, condition and category if each verdict were
    a majority vote of k runs. Uses each meal's observed p_above as the true
    rate and assumes runs are independent, so it is an estimate, not a measurement."""
    rows = []
    for (model, cond, cat), g in summary.groupby(["model", "condition", "category"]):
        row = {"model": model, "condition": cond, "category": cat}
        for k in ks:
            row[f"vote_of_{k}"] = g["p_above"].map(lambda p: majority_vote_instability(p, k)).mean()
        rows.append(row)
    out = pd.DataFrame(rows)
    if len(out):
        out["category"] = pd.Categorical(out["category"], CATEGORY_ORDER, ordered=True)
        out = out.sort_values(["model", "condition", "category"])
    return out


def majority_verdict(p_above: float) -> str:
    if p_above > 0.5:
        return "above"
    if p_above < 0.5:
        return "below"
    return "tie"


def generation_shift(summary: pd.DataFrame, pairs: list[list[str]]) -> pd.DataFrame:
    """Per meal, compare an older model with its replacement under the same
    condition. A changed majority verdict is a change that resampling cannot
    undo: it comes from where the scores centre, not from run-to-run noise."""
    rows = []
    for old, new in pairs:
        a = summary[summary["model"] == old]
        b = summary[summary["model"] == new]
        merged = a.merge(b, on=["condition", "meal", "category"], suffixes=("_old", "_new"))
        for _, r in merged.iterrows():
            v_old, v_new = majority_verdict(r["p_above_old"]), majority_verdict(r["p_above_new"])
            rows.append({
                "old": old, "new": new, "condition": r["condition"], "meal": r["meal"],
                "category": r["category"],
                "mean_old": r["mean_old"], "mean_new": r["mean_new"],
                "mean_change": r["mean_new"] - r["mean_old"],
                "instability_old": r["verdict_instability_old"],
                "instability_new": r["verdict_instability_new"],
                "verdict_old": v_old, "verdict_new": v_new,
                "verdict_changed": "tie" not in (v_old, v_new) and v_old != v_new,
            })
    return pd.DataFrame(rows)


def output_prefix(path: Path) -> str:
    """results/raw.jsonl -> "", results/monitor_raw.jsonl -> "monitor_",
    results/mock_raw.jsonl -> "mock_", so each task's outputs keep their own names."""
    stem = path.stem
    if stem.endswith("raw"):
        return stem.removesuffix("raw")
    return f"{stem}_"


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
    answered = df[df["status"].isin(ANSWERED)].copy()
    aggs = dict(calls=("status", "size"), input_tokens=("input_tokens", "sum"),
                output_tokens=("output_tokens", "sum"), mean_output_tokens=("output_tokens", "mean"))
    if "thinking_blocks" in answered:
        # Share of answers that came with hidden reasoning, among calls where it
        # was recorded (calls made before the field existed are left out).
        known = answered["thinking_blocks"].notna()
        answered["thought"] = (answered["thinking_blocks"] > 0).where(known)
        aggs["share_with_thinking"] = ("thought", "mean")
    return answered.groupby("model").agg(**aggs).round(2).reset_index()


def plot_strip(df: pd.DataFrame, meals_order: list[str], threshold: float, path: Path,
               labels: dict[str, str] | None = None) -> None:
    ok = df[df["score"].notna()]
    combos = list(ok.groupby(["model", "condition"]).groups)
    fig, axes = plt.subplots(len(combos), 1, figsize=(10, 3.2 * len(combos)), squeeze=False)
    for ax, (model, cond) in zip(axes[:, 0], combos):
        g = ok[(ok["model"] == model) & (ok["condition"] == cond)]
        refused = df[(df["model"] == model) & (df["condition"] == cond) & (df["status"] == "refused")]
        for i, meal in enumerate(meals_order):
            counts = g[g["meal"] == meal]["score"].astype(int).value_counts()
            if counts.empty and (refused["meal"] == meal).any():
                ax.text(i, threshold, "refused", ha="center", va="center", rotation=90, color="#777777", fontsize=8)
            for score, c in counts.items():
                ax.scatter(i, score, s=18 + 14 * c, color="#3b6ea5", alpha=0.75)
        ax.axhline(threshold, color="#b23b3b", linestyle="--", linewidth=1)
        # The same range on every panel, so a meal with no scores (all refused) keeps its slot.
        ax.set_xlim(-0.6, len(meals_order) - 0.4)
        ax.set_xticks(range(len(meals_order)))
        ax.set_xticklabels([(labels or {}).get(m, m) for m in meals_order], rotation=35, ha="right", fontsize=8)
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
    label = cfg["analysis"].get("verdict_label", "above the threshold")
    pairs = cfg["analysis"].get("generation_pairs", [])
    meals_order = [m["name"] for m in sorted(cfg["meals"], key=lambda m: CATEGORY_ORDER.index(m["category"]))]

    inp = Path(args.input)
    prefix = output_prefix(inp)
    df = mark_refusals(latest_per_call(load(inp)))

    status = df.groupby(["model", "condition", "status"]).size().rename("calls").reset_index()
    refused = refusals(df)
    summary = per_meal(df, threshold)
    cats = per_category(summary)
    corr = rank_corr(summary)
    votes = voting_table(summary)
    shift = generation_shift(summary, pairs)
    served = served_models(df)
    tokens = token_totals(df)

    res, figs = ROOT / "results", ROOT / "figures"
    figs.mkdir(exist_ok=True)
    summary.round(3).to_csv(res / f"{prefix}summary_per_meal.csv", index=False)
    if len(shift):
        shift.round(3).to_csv(res / f"{prefix}generation_shift.csv", index=False)
    with open(res / f"{prefix}summary.md", "w") as fh:
        fh.write(f"# Results summary\n\nThreshold: scores above {threshold} count as {label}.\n\n")
        fh.write("## Call outcomes\n\n"
                 "`truncated` means the answer hit max_tokens before giving a score; "
                 "`parse_failed` covers missing, decimal or range scores; "
                 "`refused` means the API ended the answer as a refusal, with no score.\n\n"
                 + status.to_markdown(index=False) + "\n\n")
        if len(refused):
            fh.write("## Refusals\n\n"
                     "Calls the model refused to score, per meal. Where every run was refused there is "
                     "no score, so that meal is missing from that model's per meal, category, vote and "
                     "generation shift tables below.\n\n"
                     + refused.to_markdown(index=False) + "\n\n")
        if len(served):
            fh.write("## Models as reported by the API\n\n" + served.to_markdown(index=False) + "\n\n")
        fh.write("## By category\n\n" + cats.round(3).to_markdown(index=False) + "\n\n")
        fh.write("## Variance vs distance from threshold (Spearman)\n\n"
                 "Negative means meals closer to the threshold vary more. On a bounded 0 to 100 scale, "
                 "meals scored near 0 or 100 have little room to vary, so part of any negative value "
                 "comes from the scale itself; the flip rates per meal are the stronger evidence.\n\n"
                 + (corr.to_markdown(index=False) if len(corr) else "_Not enough variation to compute._") + "\n\n")
        fh.write("## What a majority vote would fix\n\n"
                 "Mean chance that a verdict lands on the minority side if each verdict were a "
                 "majority vote of k runs instead of one. Estimated from each meal's observed share "
                 "of runs above the threshold, assuming runs are independent.\n\n"
                 + (votes.round(3).to_markdown(index=False) if len(votes) else "_No data._") + "\n\n")
        if pairs:
            changed = shift[shift["verdict_changed"]] if len(shift) else shift
            fh.write("## Generation shift\n\n"
                     "Each older model against its replacement, per meal and condition. "
                     "`verdict_changed` means the majority verdict moved to the other side of the threshold, "
                     "which more runs per verdict cannot undo. Full table in "
                     f"`{prefix}generation_shift.csv`.\n\n"
                     + (f"{len(changed)} of {len(shift)} meal comparisons changed verdict.\n\n"
                        + changed.round(2).to_markdown(index=False) if len(shift)
                        else "_No meals were scored by both models in a pair._") + "\n\n")
        fh.write("## Per meal\n\n"
                 "`p_above` is the share of runs above the threshold, with a 95% Wilson interval "
                 "(`p_above_lo` to `p_above_hi`).\n\n"
                 + summary.round(2).to_markdown(index=False) + "\n\n")
        if len(tokens):
            fh.write("## Tokens\n\n" + tokens.to_markdown(index=False) + "\n")
    labels = {m["name"]: m.get("label", m["name"]) for m in cfg["meals"]}
    plot_strip(df, meals_order, threshold, figs / f"{prefix}scores_by_meal.png", labels)
    plot_sd_vs_distance(summary, figs / f"{prefix}sd_vs_distance.png")
    print((res / f"{prefix}summary.md").read_text())


if __name__ == "__main__":
    main()
