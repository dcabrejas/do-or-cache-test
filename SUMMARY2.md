# OpenRouter Cache Locality — Test 2

Extends test 1 with a contested provider pool, idle gaps beyond 11 minutes, and mixed context lengths.


## Provider pools

| model | providers available | cache-capable |
|---|---|---|
| llama-3.3-70b | 12 | 5 |
| gpt-4o-mini | 2 | 2 |

## llama-3.3-70b

| gap | session | scenario | ctx | provider | caches? | cached tok | hit | TTFT ms | cost | error |
|---|---|---|---|---|---|---|---|---|---|---|
| 20 | 1 | baseline | long | Parasail | yes | 4112 | 0.2977 | 2924 | 0.00261632 |  |
| 15 | 1 | baseline | long | Parasail | yes | 13792 | 0.9986 | 2926 | 0.00155152 |  |
| 15 | 0 | baseline | long | Crusoe | yes | 0 | 0.0 | 1374 | 0.003498 |  |
| 20 | 0 | baseline | long | DeepInfra | no | 0 | 0.0 | 2514 | 0.0014003 |  |
| 15 | 0 | baseline | short | Parasail | yes | 0 | 0.0 | 1726 | 0.00094322 |  |
| 15 | 1 | baseline | short | Parasail | yes | 4128 | 0.9945 | 766 | 0.00048914 |  |
| 20 | 1 | baseline | short | Parasail | yes | 4112 | 0.9906 | 937 | 0.0004909 |  |
| 20 | 0 | baseline | short | Parasail | yes | 4128 | 0.9945 | 638 | 0.00048914 |  |
| 15 | 1 | baseline | long | Parasail | yes | 4112 | 0.2977 | 2624 | 0.00260432 |  |
| 20 | 1 | baseline | long | Parasail | yes | 13792 | 0.9986 | 2484 | 0.00154652 |  |
| 15 | 0 | baseline | long | Parasail | yes | 8768 | 0.6348 | 2377 | 0.00209166 |  |
| 20 | 0 | baseline | long |  |  |  |  | 1792 |  |  |
| 15 | 0 | baseline | short | Parasail | yes | 4128 | 0.9937 | 812 | 0.0004898 |  |
| 15 | 1 | baseline | short | Parasail | yes | 4128 | 0.9937 | 1095 | 0.0004898 |  |
| 20 | 1 | baseline | short | Parasail | yes | 4112 | 0.9899 | 1127 | 0.00049156 |  |
| 20 | 0 | baseline | short | Parasail | yes | 4128 | 0.9937 | 1486 | 0.0004898 |  |
| 15 | 1 | idle_15min | long | DeepInfra | no | 0 | 0.0 | 3017 | 0.00139932 |  |
| 15 | 0 | idle_15min | long | DeepInfra | no | 0 | 0.0 | 5315 | 0.001399 |  |
| 15 | 0 | idle_15min | short | Parasail | yes | 0 | 0.0 | 1900 | 0.00091638 |  |
| 15 | 1 | idle_15min | short | Crusoe | yes | 0 | 0.0 | 10337 | 0.00104225 |  |
| 20 | 1 | idle_20min | long | Crusoe | yes | 0 | 0.0 | 1486 | 0.003495 |  |
| 20 | 1 | idle_20min | short | AkashML | yes | 16 | 0.0038 | 1218 | 0.0008366 |  |
| 20 | 0 | idle_20min | long | AkashML | yes | 16 | 0.0012 | 3601 | 0.00278648 |  |
| 20 | 0 | idle_20min | short | AkashML | yes | 4144 | 0.9919 | 830 | 0.0004238 |  |

**llama-3.3-70b — baseline vs idle, per session**

| gap | session | ctx | baseline hit | idle hit | baseline provider | idle provider | switched? |
|---|---|---|---|---|---|---|---|
| 15 | 0 | long | 0.3174 | 0.0 | Parasail | DeepInfra | **YES** |
| 15 | 0 | short | 0.4969 | 0.0 | Parasail | Parasail | no |
| 15 | 1 | long | 0.6482 | 0.0 | Parasail | DeepInfra | **YES** |
| 15 | 1 | short | 0.9941 | 0.0 | Parasail | Crusoe | **YES** |
| 20 | 0 | long | 0.0 | 0.0012 | None | AkashML | n/a (missing data) |
| 20 | 0 | short | 0.9941 | 0.9919 | Parasail | AkashML | **YES** |
| 20 | 1 | long | 0.6482 | 0.0 | Parasail | Crusoe | **YES** |
| 20 | 1 | short | 0.9903 | 0.0038 | Parasail | AkashML | **YES** |

**llama-3.3-70b rollup:** 6/7 comparisons changed provider after the idle gap; 6/7 showed a cache-hit drop >20%. (Comparisons with missing provider data are excluded, not counted as degraded.)


## gpt-4o-mini

| gap | session | scenario | ctx | provider | caches? | cached tok | hit | TTFT ms | cost | error |
|---|---|---|---|---|---|---|---|---|---|---|
| 15 | 0 | baseline | long | OpenAI | yes | 0 | 0.0 | 871 | 0.0020481 |  |
| 20 | 0 | baseline | long | OpenAI | yes | 1920 | 0.1431 | 982 | 0.0019017 |  |
| 15 | 1 | baseline | long | Azure | yes | 3968 | 0.2958 | 1875 | 0.0017505 |  |
| 20 | 1 | baseline | long | Azure | yes | 0 | 0.0 | 2419 | 0.0020481 |  |
| 20 | 0 | baseline | short | Azure | yes | 0 | 0.0 | 1680 | 0.00064035 |  |
| 15 | 1 | baseline | short | Azure | yes | 3968 | 0.9849 | 1964 | 0.00034275 |  |
| 15 | 0 | baseline | short | Azure | yes | 3968 | 0.9849 | 1560 | 0.00034275 |  |
| 20 | 1 | baseline | short | Azure | yes | 3968 | 0.9849 | 1483 | 0.00034275 |  |
| 15 | 0 | baseline | long | Azure | yes | 13312 | 0.9924 | 1789 | 0.0010335 |  |
| 15 | 1 | baseline | long | Azure | yes | 13312 | 0.9924 | 1706 | 0.0010353 |  |
| 20 | 0 | baseline | long | Azure | yes | 3968 | 0.2958 | 2178 | 0.0017415 |  |
| 20 | 1 | baseline | long |  |  |  |  | 1653 |  |  |
| 20 | 0 | baseline | short | Azure | yes | 3968 | 0.9844 | 1692 | 0.00034305 |  |
| 15 | 0 | baseline | short | Azure | yes | 3968 | 0.9844 | 1886 | 0.00034305 |  |
| 15 | 1 | baseline | short | Azure | yes | 3968 | 0.9844 | 1726 | 0.00034305 |  |
| 20 | 1 | baseline | short | Azure | yes | 3968 | 0.9844 | 1750 | 0.00034305 |  |
| 15 | 0 | idle_15min | long | Azure | yes | 13312 | 0.9922 | 1485 | 0.00102915 |  |
| 15 | 1 | idle_15min | long | Azure | yes | 13312 | 0.9922 | 1981 | 0.00103695 |  |
| 15 | 0 | idle_15min | short | Azure | yes | 3968 | 0.9841 | 1610 | 0.0003102 |  |
| 15 | 1 | idle_15min | short | Azure | yes | 3968 | 0.9841 | 1204 | 0.0003096 |  |
| 20 | 0 | idle_20min | long | Azure | yes | 13312 | 0.9922 | 2778 | 0.00102915 |  |
| 20 | 0 | idle_20min | short | Azure | yes | 3968 | 0.9841 | 1194 | 0.0003096 |  |
| 20 | 1 | idle_20min | long | Azure | yes | 13312 | 0.9922 | 1705 | 0.00103635 |  |
| 20 | 1 | idle_20min | short | Azure | yes | 3968 | 0.9841 | 1421 | 0.0003084 |  |

**gpt-4o-mini — baseline vs idle, per session**

| gap | session | ctx | baseline hit | idle hit | baseline provider | idle provider | switched? |
|---|---|---|---|---|---|---|---|
| 15 | 0 | long | 0.4962 | 0.9922 | Azure | Azure | no |
| 15 | 0 | short | 0.9847 | 0.9841 | Azure | Azure | no |
| 15 | 1 | long | 0.6441 | 0.9922 | Azure | Azure | no |
| 15 | 1 | short | 0.9847 | 0.9841 | Azure | Azure | no |
| 20 | 0 | long | 0.2195 | 0.9922 | Azure | Azure | no |
| 20 | 0 | short | 0.4922 | 0.9841 | Azure | Azure | no |
| 20 | 1 | long | 0.0 | 0.9922 | None | Azure | n/a (missing data) |
| 20 | 1 | short | 0.9847 | 0.9841 | Azure | Azure | no |

**gpt-4o-mini rollup:** 0/7 comparisons changed provider after the idle gap; 0/7 showed a cache-hit drop >20%. (Comparisons with missing provider data are excluded, not counted as degraded.)
