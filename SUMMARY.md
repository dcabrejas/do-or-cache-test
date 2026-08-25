# OpenRouter Cache Locality Test — Summary


## Coding workload (3 sessions)

| session | scenario | gap_before_s | ttft_ms | total_ms | provider | cache_hit_rate | total_cost | error |
|---|---|---|---|---|---|---|---|---|
| 1 | baseline | 0 | 2374 | 2888 | Azure | 0.9924 | 0.0010581 |  |
| 0 | baseline | 0 | 2635 | 3244 | Azure | 0.0 | 0.0020613 |  |
| 2 | baseline | 0 | 2676 | 3390 | Azure | 0.0 | 0.0020493 |  |
| 0 | baseline | 45 | 2322 | 5967 | Azure | 0.0 | 0.00226515 |  |
| 2 | baseline | 45 | 1692 | 7418 | Azure | 0.9925 | 0.00124875 |  |
| 1 | baseline | 45 | 2409 | 5112 | Azure | 0.9925 | 0.00122955 |  |
| 0 | baseline | 45 | 2728 | 3120 | Azure | 0.9924 | 0.0010299 |  |
| 2 | baseline | 45 | 1565 | 1819 | Azure | 0.9924 | 0.0010347 |  |
| 1 | baseline | 45 | 1731 | 1949 | Azure | 0.9924 | 0.0010323 |  |
| 0 | baseline | 45 | 1847 | 2570 | Azure | 0.9923 | 0.00105705 |  |
| 2 | baseline | 45 | 4608 | 6455 | Azure | 0.9923 | 0.00111405 |  |
| 1 | baseline | 45 | 2542 | 11445 | Azure | 0.9923 | 0.00150405 |  |
| 0 | idle_6min | 360 | 2044 | 2253 | Azure | 0.9922 | 0.00103035 |  |
| 2 | idle_6min | 360 | 1585 | 1867 | Azure | 0.9922 | 0.00103695 |  |
| 1 | idle_6min | 360 | 1778 | 2034 | Azure | 0.9922 | 0.00103095 |  |
| 0 | idle_11min | 669 | 2275 | 2276 | Azure | 0.9922 | 0.001017 |  |
| 2 | idle_11min | 669 | 1692 | 1745 | Azure | 0.9922 | 0.0010164 |  |
| 1 | idle_11min | 670 | 1394 | 1528 | Azure | 0.9922 | 0.0010164 |  |

**Per-session comparison (baseline = last warm request before idle gap):**

| session | baseline_hit | 6min_hit | 11min_hit | baseline_provider | 6min_provider | 11min_provider | 6min_missing_data | 11min_missing_data |
|---|---|---|---|---|---|---|---|---|
| 0 | 0.4962 | 0.9922 | 0.9922 | Azure | Azure | Azure | False | False |
| 1 | 0.9924 | 0.9922 | 0.9922 | Azure | Azure | Azure | False | False |
| 2 | 0.7443 | 0.9922 | 0.9922 | Azure | Azure | Azure | False | False |

**Coding rollup:** degradation seen in 0/3 sessions with valid data at ~6min idle, and 0/3 sessions with valid data at ~11min idle (sessions with missing/failed generation-stats lookups excluded from these counts, not counted as degraded).

**Verdict (Coding):** No degradation observed at ~6min or ~11min across any session — cache/provider affinity held steady.


## Legal Research workload (3 sessions)

| session | scenario | gap_before_s | ttft_ms | total_ms | provider | cache_hit_rate | total_cost | error |
|---|---|---|---|---|---|---|---|---|
| 2 | baseline | 0 | 1355 | 2148 | OpenAI | 0.9905 | 0.0009861 |  |
| 1 | baseline | 0 | 1290 | 1898 | OpenAI | 0.9905 | 0.0009795 |  |
| 0 | baseline | 0 | 1184 | 2148 | OpenAI | 0.9905 | 0.0009843 |  |
| 2 | baseline | 45 | 695 | 2796 | OpenAI | 0.9906 | 0.00106995 |  |
| 1 | baseline | 45 | 742 | 3008 | OpenAI | 0.9906 | 0.00108195 |  |
| 0 | baseline | 45 | 698 | 2964 | OpenAI | 0.9906 | 0.00108195 |  |
| 0 | baseline | 45 | 817 | 1193 | OpenAI | 0.9905 | 0.0009663 |  |
| 2 | baseline | 45 | 804 | 1022 | OpenAI | 0.9905 | 0.0009567 |  |
| 1 | baseline | 45 | 749 | 1103 | OpenAI | 0.9905 | 0.0009615 |  |
| 2 | baseline | 45 | 754 | 2582 | OpenAI | 0.9904 | 0.00103905 |  |
| 0 | baseline | 45 | 1013 | 3428 | OpenAI | 0.9904 | 0.00106065 |  |
| 1 | baseline | 45 | 856 | 18612 | OpenAI | 0.9904 | 0.00163245 |  |
| 0 | idle_6min | 360 | 1264 | 2091 | OpenAI | 0.9902 | 0.00095895 |  |
| 2 | idle_6min | 360 | 2620 | 2949 | OpenAI | 0.9902 | 0.00096195 |  |
| 1 | idle_6min | 360 | 3370 | 4516 | OpenAI | 0.9902 | 0.00096195 |  |
| 2 | idle_11min | 670 | 949 | 986 | OpenAI | 0.9903 | 0.0009408 |  |
| 0 | idle_11min | 666 | 1517 | 1557 | OpenAI | 0.9903 | 0.0009408 |  |
| 1 | idle_11min | 675 | 749 | 785 | OpenAI | 0.9903 | 0.0009414 |  |

**Per-session comparison (baseline = last warm request before idle gap):**

| session | baseline_hit | 6min_hit | 11min_hit | baseline_provider | 6min_provider | 11min_provider | 6min_missing_data | 11min_missing_data |
|---|---|---|---|---|---|---|---|---|
| 0 | 0.9905 | 0.9902 | 0.9903 | OpenAI | OpenAI | OpenAI | False | False |
| 1 | 0.9905 | 0.9902 | 0.9903 | OpenAI | OpenAI | OpenAI | False | False |
| 2 | 0.9905 | 0.9902 | 0.9903 | OpenAI | OpenAI | OpenAI | False | False |

**Legal Research rollup:** degradation seen in 0/3 sessions with valid data at ~6min idle, and 0/3 sessions with valid data at ~11min idle (sessions with missing/failed generation-stats lookups excluded from these counts, not counted as degraded).

**Verdict (Legal Research):** No degradation observed at ~6min or ~11min across any session — cache/provider affinity held steady.
