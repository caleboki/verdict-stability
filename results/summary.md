# Results summary

Threshold: scores above 49.5 count as suitable.

## Call outcomes

`truncated` means the answer hit max_tokens before giving a score; `parse_failed` covers missing, decimal or range scores; `refused` means the API ended the answer as a refusal, with no score.

| model                     | condition   | status                  |   calls |
|:--------------------------|:------------|:------------------------|--------:|
| claude-haiku-4-5-20251001 | default     | ok                      |     240 |
| claude-haiku-4-5-20251001 | t0          | ok                      |     240 |
| claude-haiku-5-5          | default     | ok                      |     240 |
| claude-haiku-5-5          | t0          | temperature_unsupported |       1 |
| claude-sonnet-4-6         | default     | ok                      |     240 |
| claude-sonnet-4-6         | t0          | ok                      |     240 |
| claude-sonnet-5-5         | default     | ok                      |     240 |
| claude-sonnet-5-5         | t0          | temperature_unsupported |       1 |

## Models as reported by the API

| model                     | served_model              |   calls |
|:--------------------------|:--------------------------|--------:|
| claude-haiku-4-5-20251001 | claude-haiku-4-5-20251001 |     480 |
| claude-haiku-5-5          | claude-haiku-5-5          |     240 |
| claude-sonnet-4-6         | claude-sonnet-4-6         |     480 |
| claude-sonnet-5-5         | claude-sonnet-5-5         |     240 |

## By category

| model                     | condition   | category   |   meals |   mean_sd |   mean_instability |   meals_with_any_flip |
|:--------------------------|:------------|:-----------|--------:|----------:|-------------------:|----------------------:|
| claude-haiku-4-5-20251001 | default     | clear_bad  |       3 |     2.307 |              0     |                     0 |
| claude-haiku-4-5-20251001 | default     | borderline |       6 |     5.533 |              0.033 |                     1 |
| claude-haiku-4-5-20251001 | default     | clear_good |       3 |     2.233 |              0     |                     0 |
| claude-haiku-4-5-20251001 | t0          | clear_bad  |       3 |     0     |              0     |                     0 |
| claude-haiku-4-5-20251001 | t0          | borderline |       6 |     0     |              0     |                     0 |
| claude-haiku-4-5-20251001 | t0          | clear_good |       3 |     0     |              0     |                     0 |
| claude-haiku-5-5          | default     | clear_bad  |       3 |     0.902 |              0     |                     0 |
| claude-haiku-5-5          | default     | borderline |       6 |     4.364 |              0.133 |                     2 |
| claude-haiku-5-5          | default     | clear_good |       3 |     1.713 |              0     |                     0 |
| claude-sonnet-4-6         | default     | clear_bad  |       3 |     0.494 |              0     |                     0 |
| claude-sonnet-4-6         | default     | borderline |       6 |     5.566 |              0.075 |                     2 |
| claude-sonnet-4-6         | default     | clear_good |       3 |     0.887 |              0     |                     0 |
| claude-sonnet-4-6         | t0          | clear_bad  |       3 |     0.399 |              0     |                     0 |
| claude-sonnet-4-6         | t0          | borderline |       6 |     4.23  |              0.025 |                     1 |
| claude-sonnet-4-6         | t0          | clear_good |       3 |     0.615 |              0     |                     0 |
| claude-sonnet-5-5         | default     | clear_bad  |       3 |     1.235 |              0     |                     0 |
| claude-sonnet-5-5         | default     | borderline |       6 |     2.352 |              0.075 |                     1 |
| claude-sonnet-5-5         | default     | clear_good |       3 |     1.087 |              0     |                     0 |

## Variance vs distance from threshold (Spearman)

Negative means meals closer to the threshold vary more. On a bounded 0 to 100 scale, meals scored near 0 or 100 have little room to vary, so part of any negative value comes from the scale itself; the flip rates per meal are the stronger evidence.

| model                     | condition   |   meals |   spearman_distance_vs_sd |
|:--------------------------|:------------|--------:|--------------------------:|
| claude-haiku-4-5-20251001 | default     |      12 |                    -0.853 |
| claude-haiku-5-5          | default     |      12 |                    -0.951 |
| claude-sonnet-4-6         | default     |      12 |                    -0.944 |
| claude-sonnet-4-6         | t0          |      12 |                    -0.923 |
| claude-sonnet-5-5         | default     |      12 |                    -0.855 |

## What a majority vote would fix

Mean chance that a verdict lands on the minority side if each verdict were a majority vote of k runs instead of one. Estimated from each meal's observed share of runs above the threshold, assuming runs are independent.

| model                     | condition   | category   |   vote_of_1 |   vote_of_3 |   vote_of_5 |   vote_of_9 |
|:--------------------------|:------------|:-----------|------------:|------------:|------------:|------------:|
| claude-haiku-4-5-20251001 | default     | clear_bad  |       0     |       0     |       0     |       0     |
| claude-haiku-4-5-20251001 | default     | borderline |       0.033 |       0.017 |       0.01  |       0.003 |
| claude-haiku-4-5-20251001 | default     | clear_good |       0     |       0     |       0     |       0     |
| claude-haiku-4-5-20251001 | t0          | clear_bad  |       0     |       0     |       0     |       0     |
| claude-haiku-4-5-20251001 | t0          | borderline |       0     |       0     |       0     |       0     |
| claude-haiku-4-5-20251001 | t0          | clear_good |       0     |       0     |       0     |       0     |
| claude-haiku-5-5          | default     | clear_bad  |       0     |       0     |       0     |       0     |
| claude-haiku-5-5          | default     | borderline |       0.133 |       0.117 |       0.106 |       0.089 |
| claude-haiku-5-5          | default     | clear_good |       0     |       0     |       0     |       0     |
| claude-sonnet-4-6         | default     | clear_bad  |       0     |       0     |       0     |       0     |
| claude-sonnet-4-6         | default     | borderline |       0.075 |       0.046 |       0.032 |       0.017 |
| claude-sonnet-4-6         | default     | clear_good |       0     |       0     |       0     |       0     |
| claude-sonnet-4-6         | t0          | clear_bad  |       0     |       0     |       0     |       0     |
| claude-sonnet-4-6         | t0          | borderline |       0.025 |       0.01  |       0.004 |       0.001 |
| claude-sonnet-4-6         | t0          | clear_good |       0     |       0     |       0     |       0     |
| claude-sonnet-5-5         | default     | clear_bad  |       0     |       0     |       0     |       0     |
| claude-sonnet-5-5         | default     | borderline |       0.075 |       0.071 |       0.068 |       0.063 |
| claude-sonnet-5-5         | default     | clear_good |       0     |       0     |       0     |       0     |

## Generation shift

Each older model against its replacement, per meal and condition. `verdict_changed` means the majority verdict moved to the other side of the threshold, which more runs per verdict cannot undo. Full table in `generation_shift.csv`.

6 of 24 meal comparisons changed verdict.

| old                       | new               | condition   | meal                               | category   |   mean_old |   mean_new |   mean_change |   instability_old |   instability_new | verdict_old   | verdict_new   | verdict_changed   |
|:--------------------------|:------------------|:------------|:-----------------------------------|:-----------|-----------:|-----------:|--------------:|------------------:|------------------:|:--------------|:--------------|:------------------|
| claude-sonnet-4-6         | claude-sonnet-5-5 | default     | a turkey sandwich with mayonnaise  | borderline |       32.9 |      68.1  |         35.2  |               0   |                 0 | below         | above         | True              |
| claude-sonnet-4-6         | claude-sonnet-5-5 | default     | avocado toast on whole wheat bread | borderline |       34.7 |      70.85 |         36.15 |               0   |                 0 | below         | above         | True              |
| claude-sonnet-4-6         | claude-sonnet-5-5 | default     | scrambled eggs on toast            | borderline |       45.6 |      67.45 |         21.85 |               0.3 |                 0 | below         | above         | True              |
| claude-sonnet-4-6         | claude-sonnet-5-5 | default     | spaghetti bolognese                | borderline |       27.6 |      56.85 |         29.25 |               0   |                 0 | below         | above         | True              |
| claude-haiku-4-5-20251001 | claude-haiku-5-5  | default     | avocado toast on whole wheat bread | borderline |       29.4 |      80.05 |         50.65 |               0   |                 0 | below         | above         | True              |
| claude-haiku-4-5-20251001 | claude-haiku-5-5  | default     | scrambled eggs on toast            | borderline |       31.4 |      68.25 |         36.85 |               0   |                 0 | below         | above         | True              |

## Per meal

`p_above` is the share of runs above the threshold, with a 95% Wilson interval (`p_above_lo` to `p_above_hi`).

| provider   | model                     | condition   | meal                                                  | category   |   n |   parse_failures |   truncated |   refusals |   mean |   sd |   min |   max |   distinct_scores |   modal_share |   p_above |   p_above_lo |   p_above_hi |   verdict_instability |   distance_from_threshold |
|:-----------|:--------------------------|:------------|:------------------------------------------------------|:-----------|----:|-----------------:|------------:|-----------:|-------:|-----:|------:|------:|------------------:|--------------:|----------:|-------------:|-------------:|----------------------:|--------------------------:|
| anthropic  | claude-haiku-4-5-20251001 | default     | a chicken Caesar salad                                | borderline |  20 |                0 |           0 |          0 |  35.5  | 5.06 |    28 |    45 |                 4 |          0.55 |      0    |         0    |         0.16 |                  0    |                     14    |
| anthropic  | claude-haiku-4-5-20251001 | default     | a double bacon cheeseburger with fries                | clear_bad  |  20 |                0 |           0 |          0 |   7.25 | 1.33 |     5 |     8 |                 2 |          0.75 |      0    |         0    |         0.16 |                  0    |                     42.25 |
| anthropic  | claude-haiku-4-5-20251001 | default     | a turkey sandwich with mayonnaise                     | borderline |  20 |                0 |           0 |          0 |  27.55 | 4.43 |    18 |    35 |                 4 |          0.45 |      0    |         0    |         0.16 |                  0    |                     21.95 |
| anthropic  | claude-haiku-4-5-20251001 | default     | avocado toast on whole wheat bread                    | borderline |  20 |                0 |           0 |          0 |  29.4  | 6.89 |    15 |    42 |                 6 |          0.35 |      0    |         0    |         0.16 |                  0    |                     20.1  |
| anthropic  | claude-haiku-4-5-20251001 | default     | deep fried fish and chips                             | clear_bad  |  20 |                0 |           0 |          0 |   7.9  | 2    |     5 |    15 |                 3 |          0.8  |      0    |         0    |         0.16 |                  0    |                     41.6  |
| anthropic  | claude-haiku-4-5-20251001 | default     | fried chicken                                         | clear_bad  |  20 |                0 |           0 |          0 |  11.5  | 3.59 |     8 |    15 |                 2 |          0.5  |      0    |         0    |         0.16 |                  0    |                     38    |
| anthropic  | claude-haiku-4-5-20251001 | default     | grilled salmon with white rice                        | borderline |  20 |                0 |           0 |          0 |  54.9  | 7.26 |    42 |    68 |                 7 |          0.25 |      0.8  |         0.58 |         0.92 |                  0.2  |                      5.4  |
| anthropic  | claude-haiku-4-5-20251001 | default     | grilled skinless chicken breast with steamed broccoli | clear_good |  20 |                0 |           0 |          0 |  85.45 | 2.96 |    82 |    88 |                 3 |          0.55 |      1    |         0.84 |         1    |                  0    |                     35.95 |
| anthropic  | claude-haiku-4-5-20251001 | default     | oatmeal made with skim milk and topped with berries   | clear_good |  20 |                0 |           0 |          0 |  80.6  | 1.96 |    78 |    82 |                 2 |          0.65 |      1    |         0.84 |         1    |                  0    |                     31.1  |
| anthropic  | claude-haiku-4-5-20251001 | default     | scrambled eggs on toast                               | borderline |  20 |                0 |           0 |          0 |  31.4  | 5.09 |    25 |    42 |                 5 |          0.4  |      0    |         0    |         0.16 |                  0    |                     18.1  |
| anthropic  | claude-haiku-4-5-20251001 | default     | spaghetti bolognese                                   | borderline |  20 |                0 |           0 |          0 |  24.2  | 4.46 |    18 |    35 |                 5 |          0.45 |      0    |         0    |         0.16 |                  0    |                     25.3  |
| anthropic  | claude-haiku-4-5-20251001 | default     | steamed vegetables with plain brown rice              | clear_good |  20 |                0 |           0 |          0 |  81    | 1.78 |    78 |    82 |                 2 |          0.75 |      1    |         0.84 |         1    |                  0    |                     31.5  |
| anthropic  | claude-haiku-4-5-20251001 | t0          | a chicken Caesar salad                                | borderline |  20 |                0 |           0 |          0 |  42    | 0    |    42 |    42 |                 1 |          1    |      0    |         0    |         0.16 |                  0    |                      7.5  |
| anthropic  | claude-haiku-4-5-20251001 | t0          | a double bacon cheeseburger with fries                | clear_bad  |  20 |                0 |           0 |          0 |   8    | 0    |     8 |     8 |                 1 |          1    |      0    |         0    |         0.16 |                  0    |                     41.5  |
| anthropic  | claude-haiku-4-5-20251001 | t0          | a turkey sandwich with mayonnaise                     | borderline |  20 |                0 |           0 |          0 |  42    | 0    |    42 |    42 |                 1 |          1    |      0    |         0    |         0.16 |                  0    |                      7.5  |
| anthropic  | claude-haiku-4-5-20251001 | t0          | avocado toast on whole wheat bread                    | borderline |  20 |                0 |           0 |          0 |  28    | 0    |    28 |    28 |                 1 |          1    |      0    |         0    |         0.16 |                  0    |                     21.5  |
| anthropic  | claude-haiku-4-5-20251001 | t0          | deep fried fish and chips                             | clear_bad  |  20 |                0 |           0 |          0 |   8    | 0    |     8 |     8 |                 1 |          1    |      0    |         0    |         0.16 |                  0    |                     41.5  |
| anthropic  | claude-haiku-4-5-20251001 | t0          | fried chicken                                         | clear_bad  |  20 |                0 |           0 |          0 |   8    | 0    |     8 |     8 |                 1 |          1    |      0    |         0    |         0.16 |                  0    |                     41.5  |
| anthropic  | claude-haiku-4-5-20251001 | t0          | grilled salmon with white rice                        | borderline |  20 |                0 |           0 |          0 |  42    | 0    |    42 |    42 |                 1 |          1    |      0    |         0    |         0.16 |                  0    |                      7.5  |
| anthropic  | claude-haiku-4-5-20251001 | t0          | grilled skinless chicken breast with steamed broccoli | clear_good |  20 |                0 |           0 |          0 |  82    | 0    |    82 |    82 |                 1 |          1    |      1    |         0.84 |         1    |                  0    |                     32.5  |
| anthropic  | claude-haiku-4-5-20251001 | t0          | oatmeal made with skim milk and topped with berries   | clear_good |  20 |                0 |           0 |          0 |  82    | 0    |    82 |    82 |                 1 |          1    |      1    |         0.84 |         1    |                  0    |                     32.5  |
| anthropic  | claude-haiku-4-5-20251001 | t0          | scrambled eggs on toast                               | borderline |  20 |                0 |           0 |          0 |  35    | 0    |    35 |    35 |                 1 |          1    |      0    |         0    |         0.16 |                  0    |                     14.5  |
| anthropic  | claude-haiku-4-5-20251001 | t0          | spaghetti bolognese                                   | borderline |  20 |                0 |           0 |          0 |  25    | 0    |    25 |    25 |                 1 |          1    |      0    |         0    |         0.16 |                  0    |                     24.5  |
| anthropic  | claude-haiku-4-5-20251001 | t0          | steamed vegetables with plain brown rice              | clear_good |  20 |                0 |           0 |          0 |  82    | 0    |    82 |    82 |                 1 |          1    |      1    |         0.84 |         1    |                  0    |                     32.5  |
| anthropic  | claude-haiku-5-5          | default     | a chicken Caesar salad                                | borderline |  20 |                0 |           0 |          0 |  29    | 3.84 |    20 |    35 |                 4 |          0.55 |      0    |         0    |         0.16 |                  0    |                     20.5  |
| anthropic  | claude-haiku-5-5          | default     | a double bacon cheeseburger with fries                | clear_bad  |  20 |                0 |           0 |          0 |   5.05 | 0.76 |     4 |     8 |                 3 |          0.85 |      0    |         0    |         0.16 |                  0    |                     44.45 |
| anthropic  | claude-haiku-5-5          | default     | a turkey sandwich with mayonnaise                     | borderline |  20 |                0 |           0 |          0 |  46.5  | 6.51 |    35 |    60 |                 6 |          0.3  |      0.4  |         0.22 |         0.61 |                  0.4  |                      3    |
| anthropic  | claude-haiku-5-5          | default     | avocado toast on whole wheat bread                    | borderline |  20 |                0 |           0 |          0 |  80.05 | 1.96 |    78 |    85 |                 4 |          0.35 |      1    |         0.84 |         1    |                  0    |                     30.55 |
| anthropic  | claude-haiku-5-5          | default     | deep fried fish and chips                             | clear_bad  |  20 |                0 |           0 |          0 |   6.95 | 1.64 |     5 |    10 |                 4 |          0.4  |      0    |         0    |         0.16 |                  0    |                     42.55 |
| anthropic  | claude-haiku-5-5          | default     | fried chicken                                         | clear_bad  |  20 |                0 |           0 |          0 |   5.1  | 0.31 |     5 |     6 |                 2 |          0.9  |      0    |         0    |         0.16 |                  0    |                     44.4  |
| anthropic  | claude-haiku-5-5          | default     | grilled salmon with white rice                        | borderline |  20 |                0 |           0 |          0 |  75.85 | 2.98 |    70 |    80 |                 5 |          0.4  |      1    |         0.84 |         1    |                  0    |                     26.35 |
| anthropic  | claude-haiku-5-5          | default     | grilled skinless chicken breast with steamed broccoli | clear_good |  20 |                0 |           0 |          0 |  90.6  | 1.14 |    88 |    92 |                 3 |          0.6  |      1    |         0.84 |         1    |                  0    |                     41.1  |
| anthropic  | claude-haiku-5-5          | default     | oatmeal made with skim milk and topped with berries   | clear_good |  20 |                0 |           0 |          0 |  89.8  | 1.11 |    88 |    92 |                 3 |          0.7  |      1    |         0.84 |         1    |                  0    |                     40.3  |
| anthropic  | claude-haiku-5-5          | default     | scrambled eggs on toast                               | borderline |  20 |                0 |           0 |          0 |  68.25 | 4.74 |    60 |    75 |                 7 |          0.3  |      1    |         0.84 |         1    |                  0    |                     18.75 |
| anthropic  | claude-haiku-5-5          | default     | spaghetti bolognese                                   | borderline |  20 |                0 |           0 |          0 |  47    | 6.16 |    40 |    55 |                 4 |          0.3  |      0.4  |         0.22 |         0.61 |                  0.4  |                      2.5  |
| anthropic  | claude-haiku-5-5          | default     | steamed vegetables with plain brown rice              | clear_good |  20 |                0 |           0 |          0 |  89.5  | 2.89 |    78 |    92 |                 4 |          0.7  |      1    |         0.84 |         1    |                  0    |                     40    |
| anthropic  | claude-sonnet-4-6         | default     | a chicken Caesar salad                                | borderline |  20 |                0 |           0 |          0 |  34.35 | 3.99 |    30 |    45 |                 4 |          0.4  |      0    |         0    |         0.16 |                  0    |                     15.15 |
| anthropic  | claude-sonnet-4-6         | default     | a double bacon cheeseburger with fries                | clear_bad  |  20 |                0 |           0 |          0 |   2.05 | 0.22 |     2 |     3 |                 2 |          0.95 |      0    |         0    |         0.16 |                  0    |                     47.45 |
| anthropic  | claude-sonnet-4-6         | default     | a turkey sandwich with mayonnaise                     | borderline |  20 |                0 |           0 |          0 |  32.9  | 3.45 |    28 |    38 |                 4 |          0.5  |      0    |         0    |         0.16 |                  0    |                     16.6  |
| anthropic  | claude-sonnet-4-6         | default     | avocado toast on whole wheat bread                    | borderline |  20 |                0 |           0 |          0 |  34.7  | 4.33 |    25 |    42 |                 6 |          0.45 |      0    |         0    |         0.16 |                  0    |                     14.8  |
| anthropic  | claude-sonnet-4-6         | default     | deep fried fish and chips                             | clear_bad  |  20 |                0 |           0 |          0 |   3.15 | 0.67 |     2 |     4 |                 3 |          0.55 |      0    |         0    |         0.16 |                  0    |                     46.35 |
| anthropic  | claude-sonnet-4-6         | default     | fried chicken                                         | clear_bad  |  20 |                0 |           0 |          0 |   4.15 | 0.59 |     3 |     5 |                 3 |          0.65 |      0    |         0    |         0.16 |                  0    |                     45.35 |
| anthropic  | claude-sonnet-4-6         | default     | grilled salmon with white rice                        | borderline |  20 |                0 |           0 |          0 |  58.05 | 8.86 |    35 |    68 |                 9 |          0.25 |      0.85 |         0.64 |         0.95 |                  0.15 |                      8.55 |
| anthropic  | claude-sonnet-4-6         | default     | grilled skinless chicken breast with steamed broccoli | clear_good |  20 |                0 |           0 |          0 |  92.1  | 0.31 |    92 |    93 |                 2 |          0.9  |      1    |         0.84 |         1    |                  0    |                     42.6  |
| anthropic  | claude-sonnet-4-6         | default     | oatmeal made with skim milk and topped with berries   | clear_good |  20 |                0 |           0 |          0 |  90.5  | 0.89 |    90 |    92 |                 2 |          0.75 |      1    |         0.84 |         1    |                  0    |                     41    |
| anthropic  | claude-sonnet-4-6         | default     | scrambled eggs on toast                               | borderline |  20 |                0 |           0 |          0 |  45.6  | 8.53 |    30 |    65 |                 8 |          0.35 |      0.3  |         0.15 |         0.52 |                  0.3  |                      3.9  |
| anthropic  | claude-sonnet-4-6         | default     | spaghetti bolognese                                   | borderline |  20 |                0 |           0 |          0 |  27.6  | 4.24 |    18 |    35 |                 5 |          0.45 |      0    |         0    |         0.16 |                  0    |                     21.9  |
| anthropic  | claude-sonnet-4-6         | default     | steamed vegetables with plain brown rice              | clear_good |  20 |                0 |           0 |          0 |  89.4  | 1.47 |    88 |    92 |                 3 |          0.45 |      1    |         0.84 |         1    |                  0    |                     39.9  |
| anthropic  | claude-sonnet-4-6         | t0          | a chicken Caesar salad                                | borderline |  20 |                0 |           0 |          0 |  34.55 | 3.14 |    28 |    42 |                 5 |          0.65 |      0    |         0    |         0.16 |                  0    |                     14.95 |
| anthropic  | claude-sonnet-4-6         | t0          | a double bacon cheeseburger with fries                | clear_bad  |  20 |                0 |           0 |          0 |   2.05 | 0.22 |     2 |     3 |                 2 |          0.95 |      0    |         0    |         0.16 |                  0    |                     47.45 |
| anthropic  | claude-sonnet-4-6         | t0          | a turkey sandwich with mayonnaise                     | borderline |  20 |                0 |           0 |          0 |  32.55 | 3.27 |    25 |    35 |                 4 |          0.6  |      0    |         0    |         0.16 |                  0    |                     16.95 |
| anthropic  | claude-sonnet-4-6         | t0          | avocado toast on whole wheat bread                    | borderline |  20 |                0 |           0 |          0 |  33.4  | 3.79 |    28 |    45 |                 4 |          0.55 |      0    |         0    |         0.16 |                  0    |                     16.1  |
| anthropic  | claude-sonnet-4-6         | t0          | deep fried fish and chips                             | clear_bad  |  20 |                0 |           0 |          0 |   3.3  | 0.47 |     3 |     4 |                 2 |          0.7  |      0    |         0    |         0.16 |                  0    |                     46.2  |
| anthropic  | claude-sonnet-4-6         | t0          | fried chicken                                         | clear_bad  |  20 |                0 |           0 |          0 |   4.6  | 0.5  |     4 |     5 |                 2 |          0.6  |      0    |         0    |         0.16 |                  0    |                     44.9  |
| anthropic  | claude-sonnet-4-6         | t0          | grilled salmon with white rice                        | borderline |  20 |                0 |           0 |          0 |  61.15 | 4.69 |    52 |    72 |                 7 |          0.5  |      1    |         0.84 |         1    |                  0    |                     11.65 |
| anthropic  | claude-sonnet-4-6         | t0          | grilled skinless chicken breast with steamed broccoli | clear_good |  20 |                0 |           0 |          0 |  92.05 | 0.22 |    92 |    93 |                 2 |          0.95 |      1    |         0.84 |         1    |                  0    |                     42.55 |
| anthropic  | claude-sonnet-4-6         | t0          | oatmeal made with skim milk and topped with berries   | clear_good |  20 |                0 |           0 |          0 |  90.3  | 0.73 |    90 |    92 |                 2 |          0.85 |      1    |         0.84 |         1    |                  0    |                     40.8  |
| anthropic  | claude-sonnet-4-6         | t0          | scrambled eggs on toast                               | borderline |  20 |                0 |           0 |          0 |  44.7  | 6.98 |    30 |    65 |                 7 |          0.45 |      0.15 |         0.05 |         0.36 |                  0.15 |                      4.8  |
| anthropic  | claude-sonnet-4-6         | t0          | spaghetti bolognese                                   | borderline |  20 |                0 |           0 |          0 |  26.75 | 3.51 |    20 |    35 |                 5 |          0.4  |      0    |         0    |         0.16 |                  0    |                     22.75 |
| anthropic  | claude-sonnet-4-6         | t0          | steamed vegetables with plain brown rice              | clear_good |  20 |                0 |           0 |          0 |  90.5  | 0.89 |    90 |    92 |                 2 |          0.75 |      1    |         0.84 |         1    |                  0    |                     41    |
| anthropic  | claude-sonnet-5-5         | default     | a chicken Caesar salad                                | borderline |  20 |                0 |           0 |          0 |  47.85 | 3.53 |    45 |    55 |                 4 |          0.55 |      0.45 |         0.26 |         0.66 |                  0.45 |                      1.65 |
| anthropic  | claude-sonnet-5-5         | default     | a double bacon cheeseburger with fries                | clear_bad  |  20 |                0 |           0 |          0 |   6.8  | 1.28 |     5 |     8 |                 3 |          0.5  |      0    |         0    |         0.16 |                  0    |                     42.7  |
| anthropic  | claude-sonnet-5-5         | default     | a turkey sandwich with mayonnaise                     | borderline |  20 |                0 |           0 |          0 |  68.1  | 2.05 |    65 |    72 |                 4 |          0.55 |      1    |         0.84 |         1    |                  0    |                     18.6  |
| anthropic  | claude-sonnet-5-5         | default     | avocado toast on whole wheat bread                    | borderline |  20 |                0 |           0 |          0 |  70.85 | 2.08 |    68 |    75 |                 4 |          0.6  |      1    |         0.84 |         1    |                  0    |                     21.35 |
| anthropic  | claude-sonnet-5-5         | default     | deep fried fish and chips                             | clear_bad  |  20 |                0 |           0 |          0 |  10.4  | 1.54 |     8 |    12 |                 3 |          0.4  |      0    |         0    |         0.16 |                  0    |                     39.1  |
| anthropic  | claude-sonnet-5-5         | default     | fried chicken                                         | clear_bad  |  20 |                0 |           0 |          0 |  11.5  | 0.89 |    10 |    12 |                 2 |          0.75 |      0    |         0    |         0.16 |                  0    |                     38    |
| anthropic  | claude-sonnet-5-5         | default     | grilled salmon with white rice                        | borderline |  20 |                0 |           0 |          0 |  78.35 | 1.66 |    75 |    80 |                 5 |          0.4  |      1    |         0.84 |         1    |                  0    |                     28.85 |
| anthropic  | claude-sonnet-5-5         | default     | grilled skinless chicken breast with steamed broccoli | clear_good |  20 |                0 |           0 |          0 |  90.5  | 0.89 |    90 |    92 |                 2 |          0.75 |      1    |         0.84 |         1    |                  0    |                     41    |
| anthropic  | claude-sonnet-5-5         | default     | oatmeal made with skim milk and topped with berries   | clear_good |  20 |                0 |           0 |          0 |  92.1  | 0.64 |    90 |    93 |                 3 |          0.75 |      1    |         0.84 |         1    |                  0    |                     42.6  |
| anthropic  | claude-sonnet-5-5         | default     | scrambled eggs on toast                               | borderline |  20 |                0 |           0 |          0 |  67.45 | 1.64 |    62 |    70 |                 5 |          0.75 |      1    |         0.84 |         1    |                  0    |                     17.95 |
| anthropic  | claude-sonnet-5-5         | default     | spaghetti bolognese                                   | borderline |  20 |                0 |           0 |          0 |  56.85 | 3.15 |    50 |    62 |                 5 |          0.55 |      1    |         0.84 |         1    |                  0    |                      7.35 |
| anthropic  | claude-sonnet-5-5         | default     | steamed vegetables with plain brown rice              | clear_good |  20 |                0 |           0 |          0 |  85.05 | 1.73 |    82 |    88 |                 5 |          0.55 |      1    |         0.84 |         1    |                  0    |                     35.55 |

## Tokens

| model                     |   calls |   input_tokens |   output_tokens |   mean_output_tokens |   share_with_thinking |
|:--------------------------|--------:|---------------:|----------------:|---------------------:|----------------------:|
| claude-haiku-4-5-20251001 |     480 |          35320 |          111102 |               231.46 |                     0 |
| claude-haiku-5-5          |     240 |          23060 |          107092 |               446.22 |                     1 |
| claude-sonnet-4-6         |     480 |          35320 |          143415 |               298.78 |                     0 |
| claude-sonnet-5-5         |     240 |          23060 |          115743 |               482.26 |                     0 |
