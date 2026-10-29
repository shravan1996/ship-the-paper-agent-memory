# Ship the Paper: does an agent need a separate memory?

A small test of one claim from Zhou, Wang, Koopman and Zuccon,
[*Do Conversational Agents Need Explicit Memory? A Controlled Comparison with Raw-History Retrieval*](https://arxiv.org/abs/2610.24671)
(arXiv:2610.24671, October 2026): that plain retrieval over the raw chat history answers at least as well as an
explicit memory system. The paper used Qwen3-30B-A3B to build every memory and to answer, and GPT-4o mini to
grade. Here Claude Haiku 5.5 writes the memory, reads every context, and grades every answer.

Written up in the Ship the Paper article
[*The book club that never made it into memory*](https://shravanpendem.com/blog/ship-the-paper/retrieval-and-memory/memory-that-dropped-the-book-club).

## What it compares

Five BEAM-100K conversations (1, 4, 6, 11 and 13; 1,356 messages, 100 probing questions). Every question is
answered from four contexts by the same reader with the same prompt:

| Arm | Context |
| --- | --- |
| `raw` | The ten single messages most similar to the question (all-MiniLM-L6-v2), in conversation order |
| `memory` | The most similar memories, up to the same number of characters as `raw` for that question |
| `oracle_raw` | Every message BEAM lists as evidence for the question |
| `oracle_memory` | Every memory built from one of those messages |

The memory is Mem0-style: per exchange, Claude extracts facts, then compares them with the most similar
stored memories and chooses ADD, UPDATE, DELETE or NONE. Every memory keeps the ids of the messages it came
from, which is what makes the oracle arm possible.

Two more arms, `raw_tight` and `memory_tight`, put both at about 1,000 tokens, the budget in the paper's
controlled comparison. They were added after the primary result and are not part of the pre-registration;
see Deviations.

## Result

| Comparison | Messages | Memory | Memory minus messages (95% interval) |
| --- | ---: | ---: | --- |
| Evidence handed over, 89 questions | 80.5 | 65.8 | -14.7 (-21.1 to -8.7) |
| Searched, same length, 96 questions (pre-registered) | 60.8 | 66.4 | +5.6 (-2.2 to +13.6) |
| Searched, about 1,000 tokens, 99 questions (exploratory) | 51.4 | 61.4 | +10.0 (+2.1 to +17.7) |

Under the thresholds in [PREREGISTRATION.md](PREREGISTRATION.md), the primary test is **inconclusive**: the
memory came out ahead, but not by enough to call the paper's claim failed. The secondary test fires one way:
the memory lost evidence while it was written (14.7 points below the messages it was built from) and almost
none while it was searched (0.5 points). Raw search found 36% of the evidence messages in its top ten.

Building the memory took 1,352 Claude calls for the five conversations, $1.26 at the CLI's list price, and
the store came out at 5% to 9% of the conversation's length. The longest conversation needed 33 minutes of
update calls in sequence. Full tables are in [results/report.md](results/report.md).

## Run it

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt
scripts/fetch_data.sh                                      # BEAM-100K, about 5.4 MB
.venv/bin/python -m unittest -v tests.test_central         # no model calls
.venv/bin/python eval.py                                   # rescores the replies already in runs/
```

`eval.py` needs no model calls and should print the numbers above. To collect fresh replies you need the
[Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) signed in; each stage resumes where it
stopped, so run it in chunks:

```bash
.venv/bin/python collect.py build  --deadline 480 --workers 6   # about 35 minutes over four chunks
.venv/bin/python collect.py answer --deadline 480 --workers 6
.venv/bin/python collect.py judge  --deadline 480 --workers 7
.venv/bin/python tools/figures.py OUT_DIR                        # the article's three figures
```

Set `MEMLAB_RUNS` to write somewhere other than `runs/`, and `MEMLAB_MODEL` to try another Claude model.

## Deviations from the pre-registration

1. **Tight-budget arms added after the result.** Once the primary result showed the memory arm reading about
   half of each store, I added both arms at about 1,000 tokens to see whether the lead came from budget.
2. **The first tight raw arm was underfilled.** Its messages are long, so it stopped at the first one that did
   not fit and used about 2,100 of its 4,000 characters while the memory arm used about 3,900. It reported a
   memory lead of +13.4. The fixed arm cuts the last message to fill the budget and reports +10.0. Both are
   kept: the first is in `runs/` as `raw_tight_underfilled`.

## Limitations

- One memory design, my reimplementation of Mem0's two phases, not Mem0 or the paper's six systems.
- One model, Claude Haiku 5.5, in every role, sampled with adaptive thinking that the CLI cannot switch off,
  and one run per question. The grader is the same model family as the reader and was spot-checked on six
  verdicts, not audited.
- Five of BEAM-100K's twenty conversations; ten questions per type, so the per-type table is descriptive.
- The raw retriever is the paper's best BEAM baseline. A stronger one (keyword plus embedding, or smaller
  chunks of long messages) was not tried, and could change the primary comparison.
- `total_cost_usd` is the CLI's list-price figure and includes its own overhead per call.

## Licence

Code under MIT (`LICENSE`). Replies, memories and tables derived from BEAM are CC BY-SA 4.0
(`LICENSE-DATA.md`).
