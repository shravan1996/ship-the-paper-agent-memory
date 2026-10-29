"""A Mem0-style explicit memory, written by Claude, with provenance on every memory.

Two phases per exchange, as in Mem0: extraction (independent per exchange, so it runs in parallel)
and update (sequential, because each decision reads the store the previous one left). Every memory
records the turn ids it was built from, which is what the oracle check in eval.py needs.

Provenance rule: ADD and UPDATE attach the current exchange's turn ids. NONE attaches them too,
because the stored memory already holds what that exchange said. DELETE removes the memory from
retrieval but keeps it in the audit log.
"""

import json

import numpy as np

from . import data, embed, prompts

NEIGHBOURS_PER_FACT = 5
MAX_SHOWN = 30


def render_exchange(ex):
    return "\n\n".join(data.render_turn(t) for t in ex["turns"]) if ex else "(none)"


def extract_prompt(conv, i):
    ex = conv["exchanges"][i]
    prev = conv["exchanges"][i - 1] if i > 0 else None
    return prompts.EXTRACT.format(date=ex["date"] or "unknown", previous=render_exchange(prev),
                                  current=render_exchange(ex))


class Store:
    def __init__(self):
        self.items = []          # {"id", "text", "sources", "date", "deleted"}
        self._vecs = np.zeros((0, 384), dtype=np.float32)

    def live(self):
        return [m for m in self.items if not m["deleted"]]

    def _set_vec(self, mid, text):
        v = embed.embed([text])[0]
        if mid < len(self._vecs):
            self._vecs[mid] = v
        else:
            self._vecs = np.vstack([self._vecs, v[None, :]])

    def neighbours(self, facts):
        """Live memories most similar to any of the new facts, in id order, at most MAX_SHOWN."""
        live = [m["id"] for m in self.items if not m["deleted"]]
        if not live or not facts:
            return []
        mat = self._vecs[live]
        picked = []
        for fv in embed.embed(facts):
            for j in embed.top_k(fv, mat, NEIGHBOURS_PER_FACT):
                if live[j] not in picked:
                    picked.append(live[j])
        return [self.items[i] for i in sorted(picked)[:MAX_SHOWN]]

    def update_prompt(self, facts, date):
        shown = self.neighbours(facts)
        mem_lines = "\n".join(f"{m['id']}. {m['text']}" for m in shown) or "(none)"
        fact_lines = "\n".join(f"{k + 1}. {f}" for k, f in enumerate(facts))
        return prompts.UPDATE.format(date=date or "unknown", facts=fact_lines, memories=mem_lines), \
            [m["id"] for m in shown]

    def apply(self, facts, ops, turn_ids, date):
        """Apply one exchange's operations. Returns counts, including facts no operation covered."""
        counts = {"ADD": 0, "UPDATE": 0, "DELETE": 0, "NONE": 0, "invalid": 0, "uncovered": 0}
        covered = set()
        for op in ops or []:
            event = str(op.get("event", "")).upper()
            fact_no = op.get("fact")
            if isinstance(fact_no, int) and 1 <= fact_no <= len(facts):
                covered.add(fact_no)
            mid = op.get("id")
            target = self.items[mid] if isinstance(mid, int) and 0 <= mid < len(self.items) \
                and not self.items[mid]["deleted"] else None
            text = (op.get("text") or "").strip()
            if event == "ADD" or (event == "UPDATE" and target is None):
                if not text and isinstance(fact_no, int) and 1 <= fact_no <= len(facts):
                    text = facts[fact_no - 1]
                if not text:
                    counts["invalid"] += 1
                    continue
                if event == "UPDATE":
                    counts["invalid"] += 1
                self._add(text, turn_ids, date)
                counts["ADD"] += 1
            elif event == "UPDATE":
                if text:
                    target["text"] = text
                    self._set_vec(target["id"], text)
                target["sources"] = sorted(set(target["sources"]) | set(turn_ids))
                target["date"] = date
                counts["UPDATE"] += 1
            elif event == "DELETE" and target is not None:
                target["deleted"] = True
                counts["DELETE"] += 1
            elif event == "NONE" and target is not None:
                target["sources"] = sorted(set(target["sources"]) | set(turn_ids))
                counts["NONE"] += 1
            elif event == "NONE":
                counts["NONE"] += 1
            else:
                counts["invalid"] += 1
        counts["uncovered"] = len(set(range(1, len(facts) + 1)) - covered)
        return counts

    def _add(self, text, turn_ids, date):
        mid = len(self.items)
        self.items.append({"id": mid, "text": text, "sources": sorted(turn_ids), "date": date,
                           "deleted": False})
        self._set_vec(mid, text)

    def vectors(self):
        return self._vecs


def replay(update_log_path):
    """Rebuild a store from an update log, so a stopped build resumes exactly where it was."""
    store, done = Store(), 0
    try:
        with open(update_log_path) as f:
            for line in f:
                rec = json.loads(line)
                if rec["exchange"] != done:
                    raise ValueError(f"update log out of order at exchange {rec['exchange']}")
                if rec.get("facts"):
                    store.apply(rec["facts"], rec.get("operations"), rec["turn_ids"], rec["date"])
                done += 1
    except FileNotFoundError:
        pass
    return store, done
