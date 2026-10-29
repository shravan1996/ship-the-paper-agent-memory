"""Collect every Claude reply the experiment needs, in resumable chunks.

    python collect.py build   --deadline 480 --workers 4
    python collect.py answer  --deadline 480 --workers 5
    python collect.py judge   --deadline 480 --workers 5

Each stage appends one JSON line per finished unit of work to runs/ and skips work already there,
so a chunk that is stopped or times out loses only the calls in flight. `--deadline` stops new
work after that many seconds; calls already started are allowed to finish.
"""

import argparse
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from memlab import arms, claude, data, embed, memory

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.environ.get("MEMLAB_RUNS", os.path.join(HERE, "runs"))
LOCK = threading.Lock()
ARMS = ["raw", "memory", "oracle_raw", "oracle_memory"]


def path(name):
    return os.path.join(RUNS, name)


def read_jsonl(p):
    try:
        with open(p) as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []


def append(p, rec):
    with LOCK:
        with open(p, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def run_pool(tasks, fn, workers, deadline):
    start, done = time.time(), [0]

    def guarded(t):
        if time.time() - start > deadline:
            return
        fn(t)
        with LOCK:
            done[0] += 1

    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(guarded, tasks))
    left = len(tasks) - done[0]
    print(f"finished {done[0]} of {len(tasks)} this chunk; {left} left; {time.time() - start:.0f}s")


def turn_vectors(conv):
    p = path(f"turnvecs-c{conv['id']}.npy")
    if os.path.exists(p):
        return np.load(p)
    v = embed.embed([t["text"] for t in conv["turns"]])
    np.save(p, v)
    return v


# Building the memory. Extraction is one call per exchange and needs nothing but the conversation,
# so it runs in a pool, earliest exchanges first. Update is sequential within a conversation and
# follows extraction as results land, one thread per conversation.

def extracted_so_far(c):
    return {r["exchange"]: r for r in read_jsonl(path(f"extract-c{c['id']}.jsonl")) if r["ok"]}


def stage_build(convs, workers, deadline):
    start = time.time()
    extracted = {c["id"]: extracted_so_far(c) for c in convs}
    tasks = sorted(((i, c["id"]) for c in convs for i in range(len(c["exchanges"]))
                    if i not in extracted[c["id"]]))
    by_id = {c["id"]: c for c in convs}
    pool_done = threading.Event()

    def extract(t):
        i, cid = t
        c = by_id[cid]
        obj, attempts = claude.call_json(memory.extract_prompt(c, i), "facts")
        facts = [str(f).strip() for f in (obj or {}).get("facts", []) if str(f).strip()]
        rec = {"exchange": i, "ok": obj is not None, "facts": facts,
               "raw": [a.get("content") or a.get("error") for a in attempts], "cost": claude.totals(attempts)}
        append(path(f"extract-c{cid}.jsonl"), rec)
        if rec["ok"]:
            with LOCK:
                extracted[cid][i] = rec

    def extraction():
        run_pool(tasks, extract, workers, deadline)
        pool_done.set()

    def update(c):
        log = path(f"update-c{c['id']}.jsonl")
        store, nxt = memory.replay(log)
        while nxt < len(c["exchanges"]) and time.time() - start < deadline:
            with LOCK:
                ready = extracted[c["id"]].get(nxt)
            if ready is None:
                if pool_done.is_set():
                    print(f"c{c['id']}: exchange {nxt} has no extraction; stopping this conversation")
                    break
                time.sleep(1)
                continue
            ex, facts = c["exchanges"][nxt], ready["facts"]
            rec = {"exchange": nxt, "turn_ids": ex["turn_ids"], "date": ex["date"], "facts": facts}
            if facts:
                prompt, shown = store.update_prompt(facts, ex["date"])
                obj, attempts = claude.call_json(prompt, "operations")
                ops = (obj or {}).get("operations")
                if not isinstance(ops, list):
                    ops = [{"fact": k + 1, "event": "ADD", "text": f} for k, f in enumerate(facts)]
                    rec["fallback"] = "unparsed reply; every fact added"
                rec |= {"shown": shown, "operations": ops,
                        "raw": [a.get("content") or a.get("error") for a in attempts],
                        "cost": claude.totals(attempts)}
                rec["counts"] = store.apply(facts, ops, ex["turn_ids"], ex["date"])
            append(log, rec)
            nxt += 1
        print(f"c{c['id']}: {nxt} of {len(c['exchanges'])} exchanges in memory, {len(store.live())} live")

    feeder = threading.Thread(target=extraction)
    feeder.start()
    with ThreadPoolExecutor(len(convs)) as pool:
        list(pool.map(update, convs))
    feeder.join()


def built_store(c):
    store, n = memory.replay(path(f"update-c{c['id']}.jsonl"))
    if n != len(c["exchanges"]):
        raise SystemExit(f"c{c['id']}: memory has {n} of {len(c['exchanges'])} exchanges; run update first")
    return store


# Answers: four arms per question (the two oracle arms only where BEAM names evidence turns).

def contexts(c):
    store = built_store(c)
    live = store.live()
    mem_vecs = store.vectors()[[m["id"] for m in live]]
    tv = turn_vectors(c)
    qv = embed.embed([q["question"] for q in c["questions"]])
    out = {}
    for q, v in zip(c["questions"], qv):
        raw_turns = arms.raw_context(c, tv, v)
        raw = arms.raw_text(raw_turns)
        mem = arms.memory_text(arms.memory_context(live, mem_vecs, v, len(raw)))
        out[(q["qid"], "raw")] = (raw, len(raw_turns))
        out[(q["qid"], "memory")] = (mem, mem.count("\n") + 1 if mem else 0)
        if q["sources"]:
            o_raw = arms.oracle_raw(c, q)
            o_mem = arms.oracle_memory(live, q)
            out[(q["qid"], "oracle_raw")] = (arms.raw_text(o_raw), len(o_raw))
            out[(q["qid"], "oracle_memory")] = (arms.memory_text(o_mem), len(o_mem))
    return out


def stage_answer(convs, workers, deadline):
    have = {(r["qid"], r["arm"]) for r in read_jsonl(path("answers.jsonl")) if r["ok"]}
    qs = {q["qid"]: q for c in convs for q in c["questions"]}
    tasks = []
    for c in convs:
        for (qid, arm), (text, n_items) in contexts(c).items():
            if (qid, arm) not in have:
                tasks.append((qid, arm, text, n_items))

    def work(t):
        qid, arm, text, n_items = t
        q = qs[qid]
        attempts = []
        for _ in range(3):
            r = claude.call(arms.answer_prompt(arm, text, q["question"]))
            attempts.append(r)
            if r["status"] == "ok" and r["content"].strip():
                break
        ok = attempts[-1]["status"] == "ok" and bool(attempts[-1]["content"].strip())
        append(path("answers.jsonl"), {
            "qid": qid, "arm": arm, "type": q["type"], "conversation": q["conversation"], "ok": ok,
            "context_chars": len(text), "context_items": n_items,
            "answer": attempts[-1].get("content") if ok else None, "cost": claude.totals(attempts)})

    run_pool(tasks, work, workers, deadline)


def stage_judge(convs, workers, deadline):
    qs = {q["qid"]: q for c in convs for q in c["questions"]}
    have = {(r["qid"], r["arm"]) for r in read_jsonl(path("judgments.jsonl")) if r["ok"]}
    tasks = [r for r in read_jsonl(path("answers.jsonl")) if r["ok"] and (r["qid"], r["arm"]) not in have]

    def work(r):
        q = qs[r["qid"]]
        obj, attempts = claude.call_json(arms.judge_prompt(q, r["answer"]), "scores")
        scores = (obj or {}).get("scores")
        ok = isinstance(scores, list) and len(scores) == len(q["rubric"]) and \
            all(isinstance(s, (int, float)) and s in (0, 0.5, 1) for s in scores)
        append(path("judgments.jsonl"), {
            "qid": r["qid"], "arm": r["arm"], "type": r["type"], "ok": ok,
            "scores": scores, "score": sum(scores) / len(scores) if ok else None,
            "raw": [a.get("content") or a.get("error") for a in attempts], "cost": claude.totals(attempts)})

    run_pool(tasks, work, workers, deadline)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["build", "answer", "judge"])
    ap.add_argument("--deadline", type=float, default=480)
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--conversations", default=",".join(data.SELECTED))
    a = ap.parse_args()
    os.makedirs(RUNS, exist_ok=True)
    convs = data.load(ids=a.conversations.split(","))
    if a.stage == "build":
        stage_build(convs, a.workers, a.deadline)
    elif a.stage == "answer":
        stage_answer(convs, a.workers, a.deadline)
    else:
        stage_judge(convs, a.workers, a.deadline)


if __name__ == "__main__":
    main()
