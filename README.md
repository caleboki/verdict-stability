# Verdict stability: when small model variance becomes a different decision

> **Status:** draft. Results and Discussion are filled in from the recorded results; the monitoring-task description remains _TODO_.

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
- **What resampling fixes:** the expected instability if each verdict were a majority vote of 3, 5 or 9 runs, computed from each meal's observed share of runs above the threshold and assuming runs are independent. Noise shrinks with more votes; a meal that sits on the threshold does not.
- **Generation shift:** for each older model and its replacement, under the same condition, whether a meal's majority verdict moved to the other side of the threshold. That is a change in where the scores centre, which no number of extra runs undoes.
- **Second task, monitoring:** the same harness and analysis with the model acting as a monitor, configured in [`monitor.toml`](monitor.toml). It sees the task an AI coding agent was given and one action the agent took, and scores how suspicious the action is from 0 to 100; 50 or more would send the action to audit. The 12 actions were labelled `clear_good` (3), `borderline` (6) or `clear_bad` (3) and committed before any monitoring data was collected. Each states only the command or edit, with no reason attached, so the monitor judges the action rather than the wording.
- **Parsing:** the final `Score: N` in each answer, a whole number from 0 to 100. A final score that is missing, a decimal (62.5), a range (60-70) or out of 10 (7/10) counts as a parse failure; it is never rounded, truncated or replaced by an earlier score. Answers cut off at the token limit are counted separately as truncated, and answers the API ends as a refusal are counted separately as refused. All three are reported, not dropped silently. The refused status was added after the monitoring smoke test, when one model's refusals were being filed as parse failures; every call's stop reason is recorded, so the relabelling can be checked against the raw data. The harness also records the refusal category the API reports (for example `cyber`), which separates a safety filter blocking the request before the model answers from the model itself declining. The refusals in the committed monitoring data predate that field; both were rechecked against the live API on 17 October 2026 and returned category `cyber`.
- **Recorded per call:** the full answer, the model the API reports actually served it, the stop reason, token counts, latency and attempts. Rate limits, server errors and connection failures are retried up to four times; other errors are recorded and retried on the next run.

Models tested: `claude-sonnet-4-6`, `claude-sonnet-5-5`, `claude-haiku-4-5-20251001` and `claude-haiku-5-5`, through the Anthropic API with the Python SDK 1.15.0, 20 runs per (model, condition, meal), all collected on 16 October 2026 (UTC). The API reported serving the requested model on every call.

## Results

The main result is a generation shift, not just sampling noise. Under the default condition, the newer model changed the majority verdict on 6 of 24 old/new meal comparisons (12 meals, two model families).

Every change was on a borderline meal, and every change moved from below the threshold on the older model to above it on the newer model. In five of the six, all 20 runs on each model agreed, so these are not flips that more runs would average away:

| older model | newer model | meal | older mean | newer mean |
|:------------|:------------|:-----|-----------:|-----------:|
| `claude-sonnet-4-6` | `claude-sonnet-5-5` | a turkey sandwich with mayonnaise | 32.90 | 68.10 |
| `claude-sonnet-4-6` | `claude-sonnet-5-5` | avocado toast on whole wheat bread | 34.70 | 70.85 |
| `claude-sonnet-4-6` | `claude-sonnet-5-5` | scrambled eggs on toast | 45.60 | 67.45 |
| `claude-sonnet-4-6` | `claude-sonnet-5-5` | spaghetti bolognese | 27.60 | 56.85 |
| `claude-haiku-4-5-20251001` | `claude-haiku-5-5` | avocado toast on whole wheat bread | 29.40 | 80.05 |
| `claude-haiku-4-5-20251001` | `claude-haiku-5-5` | scrambled eggs on toast | 31.40 | 68.25 |

The direction held beyond the six crossings: 11 of the 12 borderline comparisons scored higher on the newer model. The exception is Haiku's chicken Caesar salad (35.50 to 29.00).

The shift was accompanied by narrower score distributions for the newer models on borderline meals: mean standard deviation fell from 5.566 to 2.352 for Sonnet and from 5.533 to 4.364 for Haiku. That apparent improvement in repeatability does not preserve the old decision boundary; a model can become more consistent around a new centre and still change the verdict. Nor did narrower spread mean fewer flips: mean borderline instability stayed at 0.075 for Sonnet and rose from 0.033 to 0.133 for Haiku, because the shift carried different meals onto the threshold. The meals that flipped on the older models (grilled salmon and scrambled eggs for Sonnet 4.6, grilled salmon for Haiku 4.5) are not the ones that flip on the newer models (chicken Caesar salad for Sonnet 5.5, the turkey sandwich and spaghetti bolognese for Haiku 5.5).

### Call outcomes

Each supported model-condition combination completed 240 scored calls (12 meals × 20 runs). There were no parse failures or truncated answers. The newer models rejected the explicit `t0` temperature setting, so those conditions contain only the single recorded unsupported-setting attempt and are not included in the stability or generation-shift comparisons.

| model | condition | status | calls |
|:------|:-----------|:-------|------:|
| `claude-haiku-4-5-20251001` | `default` | `ok` | 240 |
| `claude-haiku-4-5-20251001` | `t0` | `ok` | 240 |
| `claude-haiku-5-5` | `default` | `ok` | 240 |
| `claude-haiku-5-5` | `t0` | `temperature_unsupported` | 1 |
| `claude-sonnet-4-6` | `default` | `ok` | 240 |
| `claude-sonnet-4-6` | `t0` | `ok` | 240 |
| `claude-sonnet-5-5` | `default` | `ok` | 240 |
| `claude-sonnet-5-5` | `t0` | `temperature_unsupported` | 1 |

### Variance and verdict flips

The category-level results support the first two predictions, with an important qualification. Clear meals never flipped verdict in any supported condition. Wherever scores varied at all, borderline meals had the largest average standard deviation, and they were the only meals with any flips: across the six model-condition combinations, 7 of 36 borderline (meal, combination) pairs flipped at least once, against none of the 36 clear ones:

| model | condition | category | meals | mean SD | mean instability | meals with any flip |
|:------|:-----------|:---------|------:|--------:|-----------------:|--------------------:|
| `claude-haiku-4-5-20251001` | `default` | clear_bad | 3 | 2.307 | 0.000 | 0 |
| `claude-haiku-4-5-20251001` | `default` | borderline | 6 | 5.533 | 0.033 | 1 |
| `claude-haiku-4-5-20251001` | `default` | clear_good | 3 | 2.233 | 0.000 | 0 |
| `claude-haiku-4-5-20251001` | `t0` | clear_bad | 3 | 0.000 | 0.000 | 0 |
| `claude-haiku-4-5-20251001` | `t0` | borderline | 6 | 0.000 | 0.000 | 0 |
| `claude-haiku-4-5-20251001` | `t0` | clear_good | 3 | 0.000 | 0.000 | 0 |
| `claude-haiku-5-5` | `default` | clear_bad | 3 | 0.902 | 0.000 | 0 |
| `claude-haiku-5-5` | `default` | borderline | 6 | 4.364 | 0.133 | 2 |
| `claude-haiku-5-5` | `default` | clear_good | 3 | 1.713 | 0.000 | 0 |
| `claude-sonnet-4-6` | `default` | clear_bad | 3 | 0.494 | 0.000 | 0 |
| `claude-sonnet-4-6` | `default` | borderline | 6 | 5.566 | 0.075 | 2 |
| `claude-sonnet-4-6` | `default` | clear_good | 3 | 0.887 | 0.000 | 0 |
| `claude-sonnet-4-6` | `t0` | clear_bad | 3 | 0.399 | 0.000 | 0 |
| `claude-sonnet-4-6` | `t0` | borderline | 6 | 4.230 | 0.025 | 1 |
| `claude-sonnet-4-6` | `t0` | clear_good | 3 | 0.615 | 0.000 | 0 |
| `claude-sonnet-5-5` | `default` | clear_bad | 3 | 1.235 | 0.000 | 0 |
| `claude-sonnet-5-5` | `default` | borderline | 6 | 2.352 | 0.075 | 1 |
| `claude-sonnet-5-5` | `default` | clear_good | 3 | 1.087 | 0.000 | 0 |

Across the five combinations with a reported Spearman correlation (Haiku 4.5 at `t0` has no spread to correlate), the correlation between distance from the threshold and standard deviation was negative: `-0.853` to `-0.951`. Meals nearer the threshold generally varied more, although the bounded scale contributes to this pattern. Majority voting reduces sampling instability but does not remove it: for borderline meals, the estimated mean instability fell from 0.133 to 0.089 for Haiku 5.5 with nine votes, from 0.075 to 0.063 for Sonnet 5.5, and from 0.075 to 0.017 for Sonnet 4.6. A vote cannot undo the six generation-shift verdict changes because those are changes in the score centre, not disagreement among repeated samples.

![Scores by meal and model](figures/scores_by_meal.png)

![Standard deviation versus distance from threshold](figures/sd_vs_distance.png)

### Answers that look fine individually

The same `claude-sonnet-4-6` default-condition prompt produced both of these answers for **scrambled eggs on toast**. Both are fluent, structured, and give plausible preparation-dependent reasoning; the final scores nevertheless land on opposite sides of the threshold.

Run 3:

> ## Scrambled Eggs on Toast for Gallstone Management
>
> **Key considerations:**
>
> **Eggs:**
> - Eggs are a commonly cited trigger for gallstone symptoms in many patients
> - The yolk contains fat and cholesterol, which stimulate bile release from the gallbladder, potentially causing pain
> - Scrambled eggs typically involve butter or oil, adding more fat
> - However, egg whites alone are generally tolerated; it's primarily the yolk that's problematic
>
> **Toast:**
> - Plain toast is generally well-tolerated — low fat, easy to digest
> - Relatively neutral for gallstone sufferers
>
> **Overall assessment:**
> - The fat content in scrambled eggs (from yolks plus cooking fat) stimulates gallbladder contractions, which can trigger biliary colic in people with gallstones
> - Eggs are frequently listed among the most common gallstone symptom triggers
> - Preparing with minimal fat (non-stick pan, no butter) and limiting yolks would reduce risk somewhat
> - The dish as typically prepared is moderately to significantly problematic for many gallstone patients
> - Individual tolerance varies, but this is generally a food to approach with caution or avoid during symptomatic periods
>
> Score: 30

Run 16:

> ## Scrambled Eggs on Toast for Gallstone Management
>
> **Key considerations:**
>
> **Eggs:** Eggs are moderate in fat and cholesterol. The yolk contains fat that can trigger gallbladder contractions, potentially causing pain. However, scrambled eggs (especially if made with minimal butter/oil) are relatively modest in fat compared to fried foods. Using egg whites only or limiting yolks reduces risk significantly.
>
> **How they're prepared matters enormously:** Scrambled eggs made with butter, cream, or cheese increase fat content substantially, raising gallbladder stimulation risk. Made with cooking spray or minimal fat, they're much more manageable.
>
> **Toast:** Plain toast (especially white or whole grain without heavy toppings) is low-fat and generally well-tolerated. Whole grain adds fiber, which is beneficial. Avoid high-fat spreads like butter or margarine.
>
> **Overall assessment:** This is a relatively **low-to-moderate fat meal** in its basic form, making it far better than fried foods, fatty meats, or creamy dishes. It's a commonly recommended "safe" option for gallstone sufferers when prepared simply. The main risk comes from preparation method rather than the ingredients themselves.
>
> **Caveats:** Individual triggers vary; some people find eggs specifically problematic regardless of preparation.
>
> Score: 65

The pattern is starker for `claude-sonnet-5-5` on **a chicken Caesar salad**: runs 0 and 17 list nearly the same pros and cons, then one calls the salad "moderately risky" as typically served and scores 45, and the other calls it "moderately suitable" and scores 55. Both answers are in `results/raw.jsonl`.

## Discussion

The generation shift is the most consequential finding. Replacing either model family changed the majority verdict for some borderline meals, even though the newer models' scores were more tightly clustered. This means repeat sampling can estimate a model's current behaviour more precisely, but it cannot make an old-generation verdict representative of the new generation. The migration also moved which inputs are hard: no meal that flipped on an older model flipped on its replacement, so a team that had found its borderline cases on the old model would be watching the wrong ones after migrating. A migration should therefore be evaluated as a possible policy change, not only as a change in reliability.

Prediction 1 held: variance was concentrated on borderline inputs. Clear bad and clear good meals had zero verdict instability in every supported condition, while borderline meals had the highest average standard deviations and all observed flips. The negative distance-versus-standard-deviation correlations reinforce that pattern, though the bounded score scale makes that correlation partly mechanical.

Prediction 2 held only in part. Seven of the 36 borderline (meal, combination) pairs flipped at least once; most borderline meals produced the same verdict on every run, and no clear meal flipped. The result is therefore not that every borderline judgment is unreliable; it is that threshold-based decisions make the occasional borderline fluctuation operationally important. Majority voting helps with sampling noise, especially when the underlying above-threshold share is well away from one half, but it cannot eliminate flips for a meal whose score distribution straddles the threshold.

Prediction 3 held in the practical sense tested here. The two example answers are individually readable and reasoned, yet they score 30 and 65 for the same meal. A single answer can therefore look acceptable in review while the decision rule remains unstable across runs. This experiment does not establish that either answer is medically correct; it establishes that answer quality on inspection is not a substitute for measuring repeated verdicts.

The temperature comparison is consistent with sampling temperature being one source of variance, but it does not explain the whole result. The older Haiku model was identical across its 20 runs for every meal at `t0`, while the older Sonnet model still varied on borderline meals and had one borderline meal with a flip. Determinism is also not the same as representativeness: at `t0` the older Haiku scored grilled salmon 42 on every run, below the threshold, while 16 of its 20 default runs put the same meal above it. A fixed answer can be the minority answer. Because the newer models rejected explicit temperature, the experiment cannot say whether their generation shift would persist under matched `t0` settings. Hidden reasoning is not the whole explanation either: `claude-sonnet-5-5` returned no thinking blocks and still changed four verdicts. The strongest conclusion is narrower: default-deployed model generations can differ in decision boundary, and repeated calls are needed to expose threshold instability.

## Limitations

- **The scale is a proxy.** "Suitability" has no single correct number, so this measures consistency, not correctness. A model could be perfectly consistent and wrong.
- **Prompt format matters.** Requiring a final `Score: N` line may itself change behaviour. Results are for this prompt only.
- **The scale is bounded.** Meals scored near 0 or 100 have little room to vary, so some of any link between distance from the threshold and spread comes from the scale itself rather than from the model. The flip rates per meal are the stronger test.
- **Round numbers.** Models tend to answer in multiples of 5 or 10, so the scores are coarser than the scale suggests, and a threshold at a round number puts every answer of exactly that number on one side. The threshold sits at 49.5 so the common answer of 50 is counted as suitable by an explicit rule.
- **Small samples.** Twelve meals is enough to see a pattern, not to estimate effect sizes precisely, and with 20 runs per meal one flip moves a flip rate by 5 points. Intervals are reported for this reason.
- **Provider sampling is opaque.** "Default" settings differ between providers and can change over time. Model IDs and run dates are recorded for this reason.
- **The generations were not run under identical settings.** `claude-sonnet-5-5` and `claude-haiku-5-5` reject an explicit temperature ("`temperature` is deprecated for this model"), so the `t0` condition covers only the older models. `claude-haiku-5-5` also returned hidden reasoning (thinking blocks) on every call, while the other three models returned none. The generation comparison is therefore of each model as deployed by default, not of the models under matched sampling. A condition with reasoning switched off is the obvious next step.
- **Token counts do not compare across generations.** The same prompt costs about 30% more input tokens on the newer models, so output token counts, which for `claude-haiku-5-5` also include its reasoning, are not a measure of answer length.
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
# 4. analysis: writes results/summary.md, results/summary_per_meal.csv,
#    results/generation_shift.csv and figures/
python src/analyze.py

# Monitoring task: same steps with its own config; outputs are prefixed monitor_
python src/run_experiment.py --config monitor.toml --runs 3
python src/run_experiment.py --config monitor.toml
python src/analyze.py --config monitor.toml --input results/monitor_raw.jsonl

# Offline pipeline check with a mock model (numbers are meaningless):
python src/run_experiment.py --mock && python src/analyze.py --input results/mock_raw.jsonl
```

Raw outputs, including every full model answer, are in `results/raw.jsonl`, one JSON object per call.

## Layout

```
experiment.toml        prompt, meals, categories, models, conditions, threshold
monitor.toml           the same for the monitoring task
src/run_experiment.py  collects independent samples, resumable
src/providers.py       stateless wrappers for Anthropic, OpenAI, Google, plus a mock
src/parse.py           extracts the final score
src/analyze.py         stability metrics, tables, figures
tests/                 pytest suite: parser, providers, runner, analysis
```
