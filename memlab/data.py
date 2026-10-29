"""BEAM-100K loading: conversations, turns, exchanges and probing questions.

BEAM (Tavakoli et al., 2025) ships each conversation as a list of batches of turns. Every turn has a
global integer `id`, a role, its text and a `time_anchor` date. Probing questions point at the turns
that hold their evidence through `source_chat_ids`, which is either a list of ids or a dict of lists.
"""

import ast
import os

import pyarrow.parquet as pq

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARQUET = os.path.join(HERE, "data", "beam-100k.parquet")

# Pre-registered: the lowest-numbered conversation in each of the first five categories, in id order.
SELECTED = ["1", "4", "6", "11", "13"]


def load(path=PARQUET, ids=SELECTED):
    rows = {r["conversation_id"]: r for r in pq.read_table(path).to_pylist()}
    return [conversation(rows[i]) for i in ids]


def conversation(row):
    turns = [
        {"id": t["id"], "role": t["role"], "date": t.get("time_anchor") or "", "text": t["content"]}
        for batch in row["chat"] for t in batch
    ]
    turns.sort(key=lambda t: t["id"])
    # Only the first turn of each batch carries a date; every later turn inherits it.
    current = ""
    for t in turns:
        current = t["date"] or current
        t["date"] = current
    return {
        "id": row["conversation_id"],
        "title": row["conversation_seed"]["title"],
        "category": row["conversation_seed"]["category"],
        "turns": turns,
        "exchanges": exchanges(turns),
        "questions": questions(row["conversation_id"], row["probing_questions"]),
    }


def exchanges(turns):
    """Group turns into user-led exchanges: one user turn and every assistant turn that follows it."""
    out = []
    for t in turns:
        if t["role"] == "user" or not out:
            out.append([])
        out[-1].append(t)
    return [
        {"index": i, "turn_ids": [t["id"] for t in ex], "date": ex[0]["date"], "turns": ex}
        for i, ex in enumerate(out)
    ]


def source_ids(value):
    """Flatten BEAM's source_chat_ids, which nest lists inside lists or dicts, into a sorted list."""
    found = set()

    def walk(v):
        if v is None:
            return
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                walk(x)
        else:
            found.add(int(v))

    walk(value)
    return sorted(found)


def questions(conv_id, raw):
    data = ast.literal_eval(raw) if isinstance(raw, str) else raw
    out = []
    for qtype, items in data.items():
        for k, q in enumerate(items):
            out.append({
                "qid": f"c{conv_id}-{qtype}-{k}",
                "conversation": conv_id,
                "type": qtype,
                "question": q["question"],
                "rubric": list(q.get("rubric") or []),
                "sources": source_ids(q.get("source_chat_ids")),
            })
    return out


def render_turn(t):
    who = "User" if t["role"] == "user" else "Assistant"
    date = f" ({t['date']})" if t["date"] else ""
    return f"{who}{date}: {t['text']}"
