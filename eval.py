"""Score the collected replies against the pre-registered thresholds.

    python eval.py            # writes results/summary.json and results/report.md

Needs no model calls. Everything it reads is in runs/.
"""

import collections
import json
import os

from collect import ARMS, EXPLORE_ARMS, built_store, path, read_jsonl, turn_vectors
from memlab import arms, data, embed, stats

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")


def pct(x):
    return round(100 * x, 1)


def build_report(convs):
    rows = []
    for c in convs:
        ext = {r["exchange"]: r for r in read_jsonl(path(f"extract-c{c['id']}.jsonl")) if r["ok"]}
        ext_all = read_jsonl(path(f"extract-c{c['id']}.jsonl"))
        upd = read_jsonl(path(f"update-c{c['id']}.jsonl"))
        ops = collections.Counter()
        for r in upd:
            ops.update(r.get("counts") or {})
        store = built_store(c)
        calls = sum(r["cost"]["calls"] for r in ext_all) + sum(r.get("cost", {}).get("calls", 0) for r in upd)
        cost = sum(r["cost"]["cost_usd"] for r in ext_all) + sum(r.get("cost", {}).get("cost_usd", 0) for r in upd)
        secs = sum(r["cost"]["seconds"] for r in ext_all) + sum(r.get("cost", {}).get("seconds", 0) for r in upd)
        upd_secs = sum(r.get("cost", {}).get("seconds", 0) for r in upd)
        rows.append({
            "conversation": c["id"], "category": c["category"], "turns": len(c["turns"]),
            "exchanges": len(c["exchanges"]), "raw_chars": sum(len(t["text"]) for t in c["turns"]),
            "facts_extracted": sum(len(r["facts"]) for r in ext.values()),
            "operations": dict(ops), "fallbacks": sum(1 for r in upd if r.get("fallback")),
            "live": len(store.live()), "deleted": sum(1 for m in store.items if m["deleted"]),
            "store_chars": sum(len(arms.render_memory(m)) + 1 for m in store.live()),
            "calls": calls, "cost_usd": round(cost, 4), "call_seconds": round(secs, 1),
            "sequential_update_seconds": round(upd_secs, 1),
        })
    return rows


def coverage(convs):
    """Evidence that survived writing, and evidence that each arm's retrieval put in front of the reader."""
    out = []
    for c in convs:
        store = built_store(c)
        live = store.live()
        mem_vecs = store.vectors()[[m["id"] for m in live]]
        tv = turn_vectors(c)
        qv = embed.embed([q["question"] for q in c["questions"]])
        for q, v in zip(c["questions"], qv):
            if not q["sources"]:
                continue
            raw_turns = arms.raw_context(c, tv, v)
            raw_chars = len(arms.raw_text(raw_turns))
            mem_ctx = arms.memory_context(live, mem_vecs, v, raw_chars)
            src = set(q["sources"])
            oracle = arms.oracle_memory(live, q)
            covered_src = {s for m in live for s in m["sources"]} & src
            out.append({
                "qid": q["qid"], "type": q["type"],
                "source_turns": len(src),
                "source_turns_in_memory": len(covered_src),
                "raw_hits": len(src & {t["id"] for t in raw_turns}),
                "oracle_memories": len(oracle),
                "oracle_memories_retrieved": len({m["id"] for m in oracle} & {m["id"] for m in mem_ctx}),
                "memory_items_shown": len(mem_ctx), "live": len(live),
            })
    return out


def main():
    convs = data.load()
    qtype = {q["qid"]: q["type"] for c in convs for q in c["questions"]}
    has_src = {q["qid"] for c in convs for q in c["questions"] if q["sources"]}
    answers = {(r["qid"], r["arm"]): r for r in read_jsonl(path("answers.jsonl")) if r["ok"]}
    judged = {}
    failed = []
    for r in read_jsonl(path("judgments.jsonl")):
        if r["ok"]:
            judged[(r["qid"], r["arm"])] = 100 * r["score"]
    for key in answers:
        if key not in judged:
            failed.append(list(key))

    def paired(arm_a, arm_b, qids):
        keep = [q for q in qids if (q, arm_a) in judged and (q, arm_b) in judged]
        a = [judged[(q, arm_a)] for q in keep]
        b = [judged[(q, arm_b)] for q in keep]
        res = stats.paired_bootstrap(a, b)
        return {k: round(v, 2) if isinstance(v, float) else v for k, v in res.items()} | {
            arm_a: round(stats.mean(a), 1), arm_b: round(stats.mean(b), 1)}

    all_q = sorted(qtype)
    src_q = sorted(has_src)
    primary = paired("raw", "memory", all_q)
    if primary["diff"] <= 2:
        primary_call = "The paper's claim holds for a Claude-written memory (diff <= +2)."
    elif primary["diff"] >= 5 and primary["lo"] > 0:
        primary_call = "The paper's claim fails for a Claude-written memory (diff >= +5, interval above 0)."
    else:
        primary_call = "Inconclusive at this size."
    writing = paired("oracle_raw", "oracle_memory", src_q)
    searching = paired("oracle_memory", "memory", src_q)
    secondary = {
        "lost_while_writing": writing, "lost_while_writing_fires": writing["diff"] <= -10,
        "lost_while_searching": searching, "lost_while_searching_fires": searching["diff"] <= -10,
        "raw_vs_oracle_raw": paired("oracle_raw", "raw", src_q),
    }

    exploratory = {
        "note": "Added after the primary result; not pre-registered. Both arms at about 1,000 tokens.",
        "tight": paired("raw_tight", "memory_tight", all_q),
        "memory_tight_vs_memory": paired("memory", "memory_tight", all_q),
        "raw_tight_vs_raw": paired("raw", "raw_tight", all_q),
        "first_version_underfilled": paired("raw_tight_underfilled", "memory_tight", all_q),
    }

    by_type = {}
    for t in sorted(set(qtype.values())):
        qs = [q for q in all_q if qtype[q] == t]
        by_type[t] = {arm: round(stats.mean([judged[(q, arm)] for q in qs if (q, arm) in judged]), 1)
                      for arm in ARMS + EXPLORE_ARMS if any((q, arm) in judged for q in qs)}

    def answer_costs(arm):
        rs = [r for (q, a), r in answers.items() if a == arm]
        return {
            "n": len(rs),
            "mean_context_chars": round(stats.mean([r["context_chars"] for r in rs])),
            "mean_context_items": round(stats.mean([r["context_items"] for r in rs]), 1),
            "mean_input_tokens": round(stats.mean([r["cost"]["input_tokens"] for r in rs])),
            "mean_seconds": round(stats.mean([r["cost"]["seconds"] for r in rs]), 2),
            "cost_usd": round(sum(r["cost"]["cost_usd"] for r in rs), 4),
        }

    cov = coverage(convs)
    cov_sum = {
        "questions": len(cov),
        "all_source_turns_in_memory": sum(1 for r in cov if r["source_turns_in_memory"] == r["source_turns"]),
        "no_source_turn_in_memory": sum(1 for r in cov if r["source_turns_in_memory"] == 0),
        "source_turn_recall_memory_provenance": pct(sum(r["source_turns_in_memory"] for r in cov)
                                                    / sum(r["source_turns"] for r in cov)),
        "source_turn_recall_raw_top10": pct(sum(r["raw_hits"] for r in cov) / sum(r["source_turns"] for r in cov)),
        "oracle_memory_recall_in_memory_arm": pct(sum(r["oracle_memories_retrieved"] for r in cov)
                                                  / max(1, sum(r["oracle_memories"] for r in cov))),
        "mean_memory_items_shown": round(stats.mean([r["memory_items_shown"] for r in cov]), 1),
    }

    judge_cost = sum(r["cost"]["cost_usd"] for r in read_jsonl(path("judgments.jsonl")))
    summary = {
        "primary": primary, "primary_call": primary_call, "secondary": secondary, "by_type": by_type,
        "exploratory": exploratory,
        "build": build_report(convs), "answers": {arm: answer_costs(arm) for arm in ARMS + EXPLORE_ARMS + ["raw_tight_underfilled"]},
        "coverage": cov_sum, "judge_cost_usd": round(judge_cost, 4), "unscored": failed,
    }
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    with open(os.path.join(RESULTS, "coverage.jsonl"), "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in cov)
    write_report(summary)
    print(json.dumps({k: summary[k] for k in ("primary", "primary_call", "exploratory", "coverage")}, indent=2))


def write_report(s):
    p, sec = s["primary"], s["secondary"]
    lines = [
        "# Result", "",
        f"Primary test, 100 questions: raw {p['raw']}, memory {p['memory']}, "
        f"difference {p['diff']:+.1f} (95% interval {p['lo']:+.1f} to {p['hi']:+.1f}, n={p['n']}).", "",
        s["primary_call"], "",
        "## Where the loss happens (90 questions with evidence turns)", "",
        f"- Oracle raw {sec['lost_while_writing']['oracle_raw']}, oracle memory "
        f"{sec['lost_while_writing']['oracle_memory']}: difference {sec['lost_while_writing']['diff']:+.1f} "
        f"({sec['lost_while_writing']['lo']:+.1f} to {sec['lost_while_writing']['hi']:+.1f}). "
        f"Lost while writing fires: {sec['lost_while_writing_fires']}.",
        f"- Oracle memory {sec['lost_while_searching']['oracle_memory']}, retrieved memory "
        f"{sec['lost_while_searching']['memory']}: difference {sec['lost_while_searching']['diff']:+.1f} "
        f"({sec['lost_while_searching']['lo']:+.1f} to {sec['lost_while_searching']['hi']:+.1f}). "
        f"Lost while searching fires: {sec['lost_while_searching_fires']}.",
        f"- Oracle raw {sec['raw_vs_oracle_raw']['oracle_raw']}, retrieved raw {sec['raw_vs_oracle_raw']['raw']}: "
        f"difference {sec['raw_vs_oracle_raw']['diff']:+.1f}.", "",
        "## By question type (ten questions each; descriptive only)", "",
        "| Type | " + " | ".join(ARMS + EXPLORE_ARMS) + " |", "| --- |" + " ---: |" * len(ARMS + EXPLORE_ARMS),
    ]
    for t, v in s["by_type"].items():
        lines.append(f"| {t} | " + " | ".join(str(v.get(a, "")) for a in ARMS + EXPLORE_ARMS) + " |")
    e = s["exploratory"]["tight"]
    lines += ["", "## Exploratory: both arms at about 1,000 tokens (not pre-registered)", "",
              f"raw_tight {e['raw_tight']}, memory_tight {e['memory_tight']}, difference {e['diff']:+.1f} "
              f"(95% interval {e['lo']:+.1f} to {e['hi']:+.1f}, n={e['n']})."]
    lines += ["", "## Building the memory", "",
              "| Conversation | Turns | Exchanges | Facts | Live | Deleted | Store chars | Raw chars | Calls | Cost (USD) |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for b in s["build"]:
        lines.append(f"| {b['conversation']} {b['category']} | {b['turns']} | {b['exchanges']} | "
                     f"{b['facts_extracted']} | {b['live']} | {b['deleted']} | {b['store_chars']} | "
                     f"{b['raw_chars']} | {b['calls']} | {b['cost_usd']} |")
    lines += ["", "## Answer contexts", "", "| Arm | n | Mean context chars | Mean items | Mean input tokens | Mean seconds |",
              "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for arm, a in s["answers"].items():
        lines.append(f"| {arm} | {a['n']} | {a['mean_context_chars']} | {a['mean_context_items']} | "
                     f"{a['mean_input_tokens']} | {a['mean_seconds']} |")
    lines += ["", "## Evidence coverage (no model calls)", "", "```", json.dumps(s["coverage"], indent=2), "```", "",
              f"Unscored replies: {len(s['unscored'])}.", ""]
    with open(os.path.join(RESULTS, "report.md"), "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
