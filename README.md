# Verdict stability: when small model variance becomes a different decision

> **Status:** draft. Sections marked _TODO_ are filled in from real results. Nothing in this README states a finding until the data is in.

## Question

Language models are not deterministic, and everyone knows it. The more useful question is **when that variance changes a decision**.

If a model scores something on a scale and a threshold turns the score into a verdict (suitable / not suitable, pass / fail, safe / unsafe), then variance only matters where it straddles the threshold. This experiment tests three predictions, fixed before any data was collected:

1. **Variance is concentrated on borderline inputs.** Clear cases score consistently; borderline cases spread.
2. **That spread produces verdict flips.** For borderline inputs, independent runs land on opposite sides of the threshold.
3. **Each answer looks fine on its own.** Individual responses read as confident and well reasoned, so reviewing single samples would not reveal the problem.

If these hold, two practical consequences follow. Spot checking a model on easy cases overstates how reliable it is. And any model used as a grader or judge that assigns numerical scores inherits the same failure, which averages over many items can hide.

### Motivation

I ran into this in production: a model's ingredient lists for the same meal varied from run to run, and a scoring rule with a hard cutoff turned that variation into score swings of up to 25 points. This repository tests the simpler case, a model scoring directly, with frontier models and a task anyone can reproduce.

It also compares two generations of the same model families (an earlier Claude Sonnet and Haiku next to their current replacements), which is the question a team faces before migrating: does verdict stability improve, stay the same or get worse?

## Method

- **Task:** "On a scale of 0 to 100, how suitable is _{meal}_ for someone managing gallstones?" The model explains briefly, then ends with `Score: N`, where N is a whole number. Exact wording is in [`experiment.toml`](experiment.toml).
- **Inputs:** 12 meals, labelled **before** data collection as `clear_bad` (3), `clear_good` (3) or `borderline` (6). The labels are predictions under test, not fitted afterwards.
- **Repetition:** each (model, condition, meal) is sampled _N_ times as independent, single turn calls with no conversation history, so no run can see an earlier answer.
- **Conditions:** `default` (provider default sampling, no temperature sent) and `t0` (temperature 0). If a model rejects an explicit temperature, that is recorded rather than silently changed.
- **Scale and threshold:** 0 to 100, with scores of 50 or more counting as "suitable" and 49 or less as "not suitable". A 0 to 100 scale gives the spread room to show; on a 1 to 10 scale most answers would bunch on a few integers and a flip would mostly mean a 5 against a 6.
- **Metrics per meal:** mean, standard deviation, range, number of distinct scores, modal share, the share of runs above the threshold with a 95% Wilson interval, and **verdict instability**, the share of runs on the minority side of the threshold (0 = every run agreed, 0.5 = coin flip). Across meals, the Spearman correlation between distance from threshold and standard deviation tests prediction 1.
- **Parsing:** the final `Score: N` in each answer, a whole number from 0 to 100. A final score that is missing, a decimal (62.5), a range (60-70) or out of 10 (7/10) counts as a parse failure; it is never rounded, truncated or replaced by an earlier score. Answers cut off at the token limit are counted separately as truncated. Both are reported, not dropped silently.
- **Recorded per call:** the full answer, the model the API reports actually served it, the stop reason, token counts, latency and attempts. Rate limits, server errors and connection failures are retried up to four times; other errors are recorded and retried on the next run.

Models tested: _TODO, exact model IDs and dates run._

## Results

_TODO after running. Include:_

- _the call outcomes table (including any parse failures or unsupported temperature settings)_
- _the by category table from `results/summary.md`_
- _`figures/scores_by_meal.png` and `figures/sd_vs_distance.png`_
- _one or two pairs of verbatim answers for the same meal that reach opposite verdicts, to illustrate prediction 3_

## Discussion

_TODO. Say plainly which predictions held and which did not. A prediction that fails is a result; report it as one._

## Limitations

- **The scale is a proxy.** "Suitability" has no single correct number, so this measures consistency, not correctness. A model could be perfectly consistent and wrong.
- **Prompt format matters.** Requiring a final `Score: N` line may itself change behaviour. Results are for this prompt only.
- **The scale is bounded.** Meals scored near 0 or 100 have little room to vary, so some of any link between distance from the threshold and spread comes from the scale itself rather than from the model. The flip rates per meal are the stronger test.
- **Round numbers.** Models tend to answer in multiples of 5 or 10, so the scores are coarser than the scale suggests, and a threshold at a round number puts every answer of exactly that number on one side. The threshold sits at 49.5 so the common answer of 50 is counted as suitable by an explicit rule.
- **Small samples.** Twelve meals is enough to see a pattern, not to estimate effect sizes precisely, and with 20 runs per meal one flip moves a flip rate by 5 points. Intervals are reported for this reason.
- **Provider sampling is opaque.** "Default" settings differ between providers and can change over time, and some models apply reasoning that may affect variance. Model IDs and run dates are recorded for this reason.
- **Not medical advice.** The health domain is used only because it produces natural borderline cases. Nothing here is guidance for anyone managing gallstones.

## Reproduce

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # add the API keys you have, then: export $(cat .env | xargs)

# 1. edit model IDs in experiment.toml
# 2. smoke test: 3 runs per condition
python src/run_experiment.py --runs 3
# 3. full run (resumes automatically if interrupted)
python src/run_experiment.py
# 4. analysis: writes results/summary.md, results/summary_per_meal.csv and figures/
python src/analyze.py

# Offline pipeline check with a mock model (numbers are meaningless):
python src/run_experiment.py --mock && python src/analyze.py --input results/mock_raw.jsonl
```

Raw outputs, including every full model answer, are in `results/raw.jsonl`, one JSON object per call.

## Layout

```
experiment.toml        prompt, meals, categories, models, conditions, threshold
src/run_experiment.py  collects independent samples, resumable
src/providers.py       stateless wrappers for Anthropic, OpenAI, Google, plus a mock
src/parse.py           extracts the final score
src/analyze.py         stability metrics, tables, figures
tests/test_parse.py    parser tests (pytest)
```
