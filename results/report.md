# Result

Primary test, 100 questions: raw 60.8, memory 66.4, difference +5.6 (95% interval -2.2 to +13.6, n=96).

Inconclusive at this size.

## Where the loss happens (90 questions with evidence turns)

- Oracle raw 80.5, oracle memory 65.8: difference -14.7 (-21.1 to -8.7). Lost while writing fires: True.
- Oracle memory 64.4, retrieved memory 63.9: difference -0.5 (-4.8 to +4.0). Lost while searching fires: False.
- Oracle raw 80.3, retrieved raw 58.6: difference -21.6.

## By question type (ten questions each; descriptive only)

| Type | raw | memory | oracle_raw | oracle_memory | raw_tight | memory_tight |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| abstention | 95.0 | 85.0 |  |  | 85.0 | 85.0 |
| contradiction_resolution | 61.1 | 43.8 | 68.1 | 31.2 | 48.8 | 40.0 |
| event_ordering | 30.1 | 41.7 | 82.1 | 58.8 | 16.1 | 41.7 |
| information_extraction | 67.5 | 50.0 | 90.0 | 44.2 | 55.8 | 44.2 |
| instruction_following | 90.0 | 90.6 | 90.0 | 90.0 | 82.5 | 90.0 |
| knowledge_update | 47.5 | 62.5 | 60.0 | 62.5 | 42.5 | 67.5 |
| multi_session_reasoning | 43.4 | 64.5 | 72.2 | 70.9 | 30.6 | 52.2 |
| preference_following | 83.3 | 94.4 | 93.3 | 95.0 | 75.8 | 83.3 |
| summarization | 41.6 | 58.4 | 77.5 | 60.1 | 25.3 | 41.8 |
| temporal_reasoning | 60.0 | 77.5 | 90.0 | 75.0 | 50.0 | 70.0 |

## Exploratory: both arms at about 1,000 tokens (not pre-registered)

raw_tight 51.4, memory_tight 61.4, difference +10.0 (95% interval +2.1 to +17.7, n=99).

## Building the memory

| Conversation | Turns | Exchanges | Facts | Live | Deleted | Store chars | Raw chars | Calls | Cost (USD) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 Coding | 188 | 94 | 442 | 277 | 1 | 45142 | 523015 | 186 | 0.2133 |
| 4 Math | 212 | 106 | 335 | 174 | 1 | 30682 | 673796 | 211 | 0.204 |
| 6 Writing Assistant & Learning | 258 | 129 | 396 | 235 | 4 | 37715 | 589867 | 257 | 0.231 |
| 11 Philosophical or Ethical Discussion | 388 | 194 | 582 | 286 | 4 | 47193 | 900933 | 388 | 0.3589 |
| 13 Asking Recommendation | 310 | 155 | 451 | 231 | 3 | 38257 | 518056 | 310 | 0.255 |

## Answer contexts

| Arm | n | Mean context chars | Mean items | Mean input tokens | Mean seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| raw | 100 | 21291 | 10.0 | 8485 | 11.86 |
| memory | 100 | 20956 | 121.0 | 8276 | 11.98 |
| oracle_raw | 90 | 3735 | 3.1 | 2207 | 9.94 |
| oracle_memory | 90 | 1591 | 7.5 | 1428 | 9.78 |
| raw_tight | 100 | 3998 | 3.6 | 2302 | 10.17 |
| memory_tight | 100 | 3878 | 20.8 | 2220 | 10.27 |
| raw_tight_underfilled | 100 | 2097 | 2.7 | 1604 | 9.31 |

## Evidence coverage (no model calls)

```
{
  "questions": 90,
  "all_source_turns_in_memory": 90,
  "no_source_turn_in_memory": 0,
  "source_turn_recall_memory_provenance": 100.0,
  "source_turn_recall_raw_top10": 36.0,
  "oracle_memory_recall_in_memory_arm": 78.1,
  "mean_memory_items_shown": 123.8
}
```

Unscored replies: 7.
