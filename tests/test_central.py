"""The behaviour the result depends on: provenance, replay, context budgets, and reply parsing."""

import json
import os
import tempfile
import unittest

import numpy as np

from memlab import arms, claude, data, memory


class FakeEmbed:
    """Deterministic stand-in for MiniLM, so the tests need no model download."""

    @staticmethod
    def embed(texts):
        out = []
        for t in texts:
            v = np.zeros(384, dtype=np.float32)
            for w in t.lower().split():
                v[hash(w) % 384] += 1
            n = np.linalg.norm(v)
            out.append(v / n if n else v)
        return np.array(out, dtype=np.float32).reshape(len(texts), 384)


memory.embed.embed = FakeEmbed.embed


class StoreTests(unittest.TestCase):
    def test_add_update_none_delete_keep_provenance(self):
        s = memory.Store()
        s.apply(["The user lives in Oslo."], [{"fact": 1, "event": "ADD", "text": "The user lives in Oslo."}],
                [0, 1], "March-01-2024")
        s.apply(["The user moved to Bergen."],
                [{"fact": 1, "event": "UPDATE", "id": 0, "text": "The user lives in Bergen."}], [8, 9], "May-01-2024")
        self.assertEqual(s.items[0]["text"], "The user lives in Bergen.")
        self.assertEqual(s.items[0]["sources"], [0, 1, 8, 9])
        s.apply(["The user lives in Bergen."], [{"fact": 1, "event": "NONE", "id": 0}], [12, 13], "May-02-2024")
        self.assertEqual(s.items[0]["sources"], [0, 1, 8, 9, 12, 13])
        self.assertEqual(s.items[0]["date"], "May-01-2024")
        s.apply(["The user no longer lives in Norway."], [{"fact": 1, "event": "DELETE", "id": 0}], [20, 21], "")
        self.assertEqual(s.live(), [])

    def test_update_of_unknown_id_becomes_add_and_is_counted(self):
        s = memory.Store()
        c = s.apply(["The user likes tea."], [{"fact": 1, "event": "UPDATE", "id": 42, "text": "The user likes tea."}],
                    [3], "")
        self.assertEqual(len(s.live()), 1)
        self.assertEqual(c["ADD"], 1)
        self.assertEqual(c["invalid"], 1)

    def test_fact_without_operation_is_counted_uncovered(self):
        s = memory.Store()
        c = s.apply(["a", "b"], [{"fact": 1, "event": "ADD", "text": "a"}], [0], "")
        self.assertEqual(c["uncovered"], 1)

    def test_replay_rebuilds_the_same_store(self):
        s = memory.Store()
        recs = [
            {"exchange": 0, "turn_ids": [0, 1], "date": "d0", "facts": ["x"],
             "operations": [{"fact": 1, "event": "ADD", "text": "x"}]},
            {"exchange": 1, "turn_ids": [2, 3], "date": "d1", "facts": []},
            {"exchange": 2, "turn_ids": [4, 5], "date": "d2", "facts": ["y"],
             "operations": [{"fact": 1, "event": "UPDATE", "id": 0, "text": "x and y"}]},
        ]
        for r in recs:
            if r["facts"]:
                s.apply(r["facts"], r["operations"], r["turn_ids"], r["date"])
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "log.jsonl")
            with open(p, "w") as f:
                f.writelines(json.dumps(r) + "\n" for r in recs)
            r2, n = memory.replay(p)
        self.assertEqual(n, 3)
        self.assertEqual(r2.items, s.items)


class ArmTests(unittest.TestCase):
    def setUp(self):
        self.live = [{"id": i, "text": f"fact number {i} " + "w" * 30, "sources": [i * 2], "date": "d",
                      "deleted": False} for i in range(10)]
        self.vecs = FakeEmbed.embed([m["text"] for m in self.live])

    def test_memory_context_never_exceeds_the_raw_budget(self):
        budget = 200
        chosen = arms.memory_context(self.live, self.vecs, self.vecs[3], budget)
        self.assertLessEqual(len(arms.memory_text(chosen)), budget)
        self.assertIn(self.live[3], chosen)

    def test_oracle_memory_uses_provenance(self):
        q = {"sources": [4, 5, 99]}
        self.assertEqual([m["id"] for m in arms.oracle_memory(self.live, q)], [2])

    def test_both_arms_share_one_answer_template(self):
        a = arms.answer_prompt("raw", "CTX", "Q?")
        b = arms.answer_prompt("memory", "CTX", "Q?")
        self.assertEqual(a.replace(arms.prompts.SOURCE_RAW, ""), b.replace(arms.prompts.SOURCE_MEMORY, ""))


class ParsingTests(unittest.TestCase):
    def test_last_json_object_wins(self):
        text = 'First {"facts": ["a"]} wait, correction: ```json\n{"facts": ["b", "c"]}\n```'
        self.assertEqual(claude.last_json_object(text, "facts"), {"facts": ["b", "c"]})

    def test_braces_inside_strings(self):
        text = '{"facts": ["uses {curly} braces"]}'
        self.assertEqual(claude.last_json_object(text, "facts")["facts"], ["uses {curly} braces"])

    def test_source_ids_flatten_nested_lists_and_dicts(self):
        self.assertEqual(data.source_ids({"first": [[3, 1]], "second": [2]}), [1, 2, 3])
        self.assertEqual(data.source_ids(None), [])


if __name__ == "__main__":
    unittest.main()
