"""The four contexts a question can be answered from.

raw            top-10 single turns by MiniLM cosine to the question, shown in conversation order
               (the paper's all-turns baseline).
memory         live memories by MiniLM cosine, added best first until the next one would make the
               context longer than the raw arm's context for the same question, shown in date order.
oracle_raw     every turn the question's evidence points at.
oracle_memory  every live memory whose provenance includes one of those turns.

Matching the memory arm's length to the raw arm's, question by question, is this prototype's version
of the paper's controlled setting: neither arm wins by seeing more text.
"""

from . import data, embed, prompts

RAW_K = 10


def render_memory(m):
    return f"[{m['date'] or 'undated'}] {m['text']}"


def raw_context(conv, turn_vecs, qvec):
    picked = sorted(embed.top_k(qvec, turn_vecs, RAW_K))
    return [conv["turns"][i] for i in picked]


def memory_context(live, mem_vecs, qvec, budget_chars):
    chosen, used = [], 0
    for j in embed.top_k(qvec, mem_vecs, len(live)):
        line = render_memory(live[j])
        if used + len(line) + 1 > budget_chars:
            break
        chosen.append(live[j])
        used += len(line) + 1
    return sorted(chosen, key=lambda m: (m["sources"][0] if m["sources"] else -1, m["id"]))


def oracle_raw(conv, q):
    want = set(q["sources"])
    return [t for t in conv["turns"] if t["id"] in want]


def oracle_memory(live, q):
    want = set(q["sources"])
    hits = [m for m in live if want & set(m["sources"])]
    return sorted(hits, key=lambda m: (m["sources"][0] if m["sources"] else -1, m["id"]))


def raw_text(turns):
    return "\n\n".join(data.render_turn(t) for t in turns)


def memory_text(mems):
    return "\n".join(render_memory(m) for m in mems)


def answer_prompt(kind, context_text, question):
    source = prompts.SOURCE_MEMORY if kind.endswith("memory") else prompts.SOURCE_RAW
    return prompts.ANSWER.format(source=source, context=context_text or "(nothing found)",
                                 question=question)


def judge_prompt(q, answer):
    rubric = "\n".join(f"{k + 1}. {r}" for k, r in enumerate(q["rubric"]))
    return prompts.JUDGE.format(question=q["question"], answer=answer, rubric=rubric)
