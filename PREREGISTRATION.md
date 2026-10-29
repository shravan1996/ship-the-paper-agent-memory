# Pre-registration

Written and committed on 2026-10-29, before any reply on the five selected conversations was collected.

## The paper

Yongjie Zhou, Shuai Wang, Bevan Koopman, Guido Zuccon. *Do Conversational Agents Need Explicit Memory?
A Controlled Comparison with Raw-History Retrieval.* arXiv:2610.24671, v1 posted 2026-10-17.

Its central finding (Section 4, Finding 1): none of six explicit memory systems (MemoryBank, A-Mem, Mem0,
LightMem, SimpleMem, HyperMem) beats the strongest raw-history retrieval baseline. On BEAM-100K that
baseline is every single turn as a retrieval unit, all-MiniLM-L6-v2, top 10, at 56.2 (Table 1). Its oracle
analysis on BEAM-100K (Table 6, Findings 5 and 6) splits the losses into evidence that construction threw
away and evidence the system kept but did not retrieve. The answer model throughout is
Qwen3-30B-A3B-Instruct-2507, and Appendix B.2 reports that Mem0 gains 11.5 points when GPT-4o mini builds
its memory instead, so the writer matters.

## The question

When a strong model writes the memory, does the paper's result still hold? Concretely: on BEAM-100K, does
a Mem0-style explicit memory written by Claude Haiku 5.5 answer at least as well as top-10 raw-history
retrieval, with the same reader, the same judge, and the same amount of context per question?

## Data

BEAM-100K (Tavakoli et al., 2025; Hugging Face `Mohammadta/BEAM`, CC BY-SA 4.0). Five of its twenty
conversations, chosen by a fixed rule before looking at any reply: the lowest-numbered conversation in each
of the first five categories in id order. That is conversations 1 (Coding), 4 (Math), 6 (Writing), 11
(Philosophical or Ethical) and 13 (Asking Recommendation): 1,356 turns, 678 exchanges, 100 probing
questions, ten of each of BEAM's ten types.

## Arms

Every arm uses the same answer prompt (`memlab/prompts.py`), the same reader (Claude Haiku 5.5 through
`claude -p`, tools off) and the same judge.

| Arm | Context |
| --- | --- |
| `raw` | Top 10 single turns by MiniLM cosine to the question, shown in conversation order with their dates |
| `memory` | Live memories by MiniLM cosine, best first, until the next would make the context longer than the `raw` context for the same question; shown in date order with the date each was recorded |
| `oracle_raw` | Every turn BEAM lists in the question's `source_chat_ids` |
| `oracle_memory` | Every live memory whose provenance includes one of those turns |

The two oracle arms run only on the 90 questions with evidence turns; BEAM's abstention questions have none.

The memory is built in two phases per exchange (one user turn and the assistant reply), as Mem0 does:
extraction, which sees the current exchange and the previous one for context, and update, which shows the
new facts beside the most similar stored memories (top 5 per fact by MiniLM, at most 30) and asks for ADD,
UPDATE, DELETE or NONE per fact. Every memory records the turns it came from.

## Scoring

The judge (Claude Haiku 5.5) scores each of BEAM's rubric items for the question 1, 0.5 or 0, blind to the
arm. A question's score is the mean over its items, reported on a 0 to 100 scale. A reply the judge cannot
score after three tries is dropped from both arms of every comparison it belongs to, and reported.

## Primary test

Δ = mean `memory` score minus mean `raw` score over the 100 questions, with a 95% paired bootstrap interval
(10,000 resamples of questions, seed 0).

- **The paper's claim holds for a Claude-written memory** if Δ ≤ +2.
- **It fails** if Δ ≥ +5 and the interval's lower end is above 0.
- Anything between is **inconclusive at this size**, and will be reported as that.

## Where the loss happens (secondary, on the 90 questions with evidence turns)

- **Lost while writing:** `oracle_memory` is at least 10 points below `oracle_raw`.
- **Lost while searching:** `memory` is at least 10 points below `oracle_memory`.

Both, one or neither can hold.

## Descriptive only

Scores by question type (ten questions each, no tests), the size of the memory store, the operations the
update phase chose, and the cost of building it: Claude calls, list-price cost from the CLI, and wall time,
against zero model calls to index the raw turns.

## Known departures from the paper

- One memory design, a Mem0-style reimplementation, not the six published systems or the Mem0 library.
- Claude Haiku 5.5 writes the memory, reads, and judges. The paper used Qwen3-30B-A3B to read and GPT-4o
  mini to judge. Haiku 5.5 thinks adaptively through the CLI and the CLI cannot set temperature, so every
  call is sampled; there is one run per cell.
- Five of twenty conversations, so 100 questions, not 400.
- The judge scores every type by rubric, including event ordering, which BEAM scores with its own metric.
- The memory arm's budget is matched to the raw arm's context per question, which is larger than the
  1,000-token budget in the paper's controlled comparison (Table 2).

## Pilot

Before writing this, the build ran for 75 seconds on conversation 2, which is not in the analysis: 39
extraction calls (all parsed, 8.0 s each on average) and 8 update calls (about 9 s each). It measured speed
and checked parsing. No answer or judgment was collected, and no prompt was changed afterwards.
