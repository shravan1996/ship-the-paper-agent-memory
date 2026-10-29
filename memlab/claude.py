"""Claude through the Claude Code CLI, with tools, MCP servers and settings turned off.

There is no API key in the environment this was built in, so every call is `claude -p`. The CLI
cannot set temperature or switch off Haiku 5.5's adaptive thinking, so every arm is sampled and
thinks; both arms share that. `total_cost_usd` is the CLI's list-price figure and includes about
880 tokens of its own per call, so it overstates what a direct API pipeline would pay.
"""

import json
import os
import re
import subprocess
import tempfile
import time

MODEL = os.environ.get("MEMLAB_MODEL", "claude-haiku-5-5")
SCRATCH = os.environ.get("MEMLAB_CLAUDE_CWD", os.path.join(tempfile.gettempdir(), "memlab-claude"))


def call(prompt, model=MODEL, timeout=300):
    os.makedirs(SCRATCH, exist_ok=True)
    cmd = ["claude", "-p", "--model", model, "--system-prompt", "", "--tools", "",
           "--strict-mcp-config", "--setting-sources", "", "--no-session-persistence",
           "--output-format", "json"]
    t = time.time()
    try:
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout,
                              cwd=SCRATCH)
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "timeout", "seconds": round(time.time() - t, 3)}
    if proc.returncode != 0:
        return {"status": "error", "error": (proc.stderr or proc.stdout)[-500:],
                "seconds": round(time.time() - t, 3)}
    out = json.loads(proc.stdout)
    if out.get("is_error"):
        return {"status": "error", "error": str(out.get("result"))[-500:],
                "seconds": round(time.time() - t, 3)}
    u = out.get("usage", {})
    return {
        "status": "ok",
        "content": out.get("result") or "",
        "input_tokens": (u.get("input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0)
                        + (u.get("cache_read_input_tokens") or 0),
        "output_tokens": u.get("output_tokens"),
        "thinking_tokens": (u.get("output_tokens_details") or {}).get("thinking_tokens"),
        "seconds": round(time.time() - t, 3),
        "cost_usd": out.get("total_cost_usd"),
    }


def last_json_object(text, key):
    """Return the last top-level JSON object in `text` that has `key`, or None.

    Replies sometimes print an object, correct themselves, and print another; the last one is the
    answer. Fenced code blocks are fine because the scan looks only at braces.
    """
    found = None
    for start in [m.start() for m in re.finditer(r"\{", text)]:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            c = text[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start:i + 1])
                    except ValueError:
                        break
                    if isinstance(obj, dict) and key in obj:
                        found = obj
                    break
    return found


def call_json(prompt, key, model=MODEL, tries=3):
    """Call until the reply holds a JSON object with `key`. Every raw reply is kept."""
    attempts = []
    for _ in range(tries):
        r = call(prompt, model=model)
        attempts.append(r)
        if r["status"] == "ok":
            obj = last_json_object(r["content"], key)
            if obj is not None:
                return obj, attempts
    return None, attempts


def totals(attempts):
    keys = ("input_tokens", "output_tokens", "thinking_tokens", "seconds", "cost_usd")
    return {k: round(sum((a.get(k) or 0) for a in attempts), 6) for k in keys} | {"calls": len(attempts)}
