#!/usr/bin/env python3
"""Draw the article's three figures. The result chart reads results/summary.json.

    python tools/figures.py OUT_DIR
"""

import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
S = json.loads((ROOT / "results" / "summary.json").read_text())

INK, MID, SOFT, RULE = "#191F1D", "#3F4945", "#5C6964", "#D3DBD7"
GREEN, GREEN_BG, AMBER, AMBER_INK, AMBER_BG = "#1F6B4C", "#E8F2EC", "#D9A55B", "#6B4812", "#FBF1E1"
PANEL, PANEL_EDGE = "#F3F6F4", "#C9D3CE"

STYLE = f"""  <style>
    text {{ stroke: none; }}
    .serif {{ font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif; }}
    .sans  {{ font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; }}
    .h1 {{ font-size: 26px; font-weight: 600; fill: {INK}; }}
    .sub {{ font-size: 14.5px; fill: {MID}; }}
    .label {{ font-size: 11px; font-weight: 700; letter-spacing: 1.1px; fill: {SOFT}; }}
    .label-ok {{ font-size: 11px; font-weight: 700; letter-spacing: 1.1px; fill: {GREEN}; }}
    .label-warn {{ font-size: 11px; font-weight: 700; letter-spacing: 1.1px; fill: {AMBER_INK}; }}
    .box {{ font-size: 15px; font-weight: 600; fill: {INK}; }}
    .small {{ font-size: 13.5px; fill: {MID}; }}
    .quote {{ font-size: 14px; fill: {MID}; font-style: italic; }}
    .row {{ font-size: 14.5px; fill: {INK}; }}
    .val {{ font-size: 14px; font-weight: 700; fill: {GREEN}; }}
    .val-warn {{ font-size: 14px; font-weight: 700; fill: {AMBER_INK}; }}
    .num {{ font-size: 14px; fill: {MID}; }}
    .foot {{ font-size: 13.5px; fill: {MID}; }}
  </style>
  <defs>
    <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" fill="{SOFT}"/>
    </marker>
  </defs>"""


def svg(width, height, title, desc, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">\n'
            f'  <title id="title">{escape(title)}</title>\n  <desc id="desc">{escape(desc)}</desc>\n'
            f'{STYLE}\n' + "\n".join(body) + "\n</svg>\n")


def text(x, y, s, cls, anchor=None):
    a = f' text-anchor="{anchor}"' if anchor else ""
    return f'  <text class="{cls}" x="{x}" y="{y}"{a}>{escape(s)}</text>'


def lines(x, y, rows, cls, step=20):
    return [text(x, y + i * step, r, cls) for i, r in enumerate(rows)]


def rect(x, y, w, h, fill, stroke, rx=4):
    return f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}"/>'


def arrow(x1, y1, x2, y2):
    return (f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{SOFT}" stroke-width="1.5" '
            f'marker-end="url(#arr)"/>')


def header(title, subs):
    out = [text(32, 44, title, "serif h1")]
    out += lines(32, 72, subs, "sans sub")
    y = 72 + 20 * (len(subs) - 1) + 16
    out.append(f'  <line x1="32" y1="{y}" x2="648" y2="{y}" stroke="{RULE}" stroke-width="1"/>')
    return out, y


def mechanism():
    body, y = header("Where the book club went", [
        "Two messages from one BEAM conversation, and what each kind",
        "of memory kept of them."])
    y += 16
    body.append(rect(32, y, 616, 112, PANEL, PANEL_EDGE))
    body.append(text(48, y + 22, "TWO THINGS THE USER SAID, MESSAGES 16 AND 64", "sans label"))
    body += lines(48, y + 46, ['"I met Kelly at the East Janethaven Library book club on',
                               'October 12, 2022..."'], "serif quote")
    body.append(text(48, y + 94, '"I\'ve never met Kelly at any book club or library event..."', "serif quote"))
    top = y + 112
    body.append(arrow(176, top, 176, top + 22))
    body.append(arrow(504, top, 504, top + 22))
    y = top + 24
    # Left: keep the messages
    body.append(rect(32, y, 296, 150, PANEL, PANEL_EDGE))
    body.append(text(48, y + 22, "KEEP THE MESSAGES", "sans label"))
    body += lines(48, y + 46, ["Both messages stay word for word.",
                               "A search over every message has",
                               "to find them both: ten of the",
                               "conversation's 310 messages fit."], "sans small")
    body.append(text(48, y + 134, "CAN BE LOST WHILE SEARCHING", "sans label"))
    # Right: write notes
    body.append(rect(352, y, 296, 150, AMBER_BG, AMBER))
    body.append(text(368, y + 22, "WRITE NOTES WITH CLAUDE", "sans label-warn"))
    body += lines(368, y + 46, ['"The user and Kelly both enjoy',
                                'discussing books together."',
                                '"...has never met her at any',
                                'such event."'], "serif quote")
    body.append(text(368, y + 134, "LOST WHILE WRITING: THE LIBRARY", "sans label-warn"))
    bot = y + 150
    body.append(arrow(176, bot, 176, bot + 22))
    body.append(arrow(504, bot, 504, bot + 22))
    y = bot + 24
    body.append(rect(32, y, 296, 108, GREEN_BG, GREEN))
    body.append(text(48, y + 22, "READER, GIVEN BOTH MESSAGES", "sans label-ok"))
    body += lines(48, y + 46, ['"The retrieved conversations',
                               'contradict each other, so I can\'t',
                               'give you a definitive answer."'], "serif quote")
    body.append(rect(352, y, 296, 108, AMBER_BG, AMBER))
    body.append(text(368, y + 22, "READER, GIVEN THE NOTES", "sans label-warn"))
    body += lines(368, y + 46, ['"Based on my notes, no. As of',
                                'November 5, 2023, you had never met',
                                'Kelly at a book club or library event."'], "serif quote")
    y += 108 + 32
    w = S["secondary"]["lost_while_writing"]
    body += lines(32, y, [
        f"Across the 90 questions that point at evidence messages, answers from",
        f"those messages scored {w['oracle_raw']}; answers from every note built from them",
        f"scored {w['oracle_memory']}. Both readers were Claude Haiku 5.5."], "sans foot")
    h = y + 40 + 14
    desc = ("Two messages from BEAM conversation 13. Message 16: I met Kelly at the East Janethaven Library "
            "book club on October 12, 2022. Message 64: I've never met Kelly at any book club or library event. "
            "Kept as messages, both survive word for word and a search over all 310 messages has to find them. "
            "Written into notes by Claude, the first becomes 'The user and Kelly both enjoy discussing books "
            "together', losing the library and the date, and the second is kept. Given both messages, the reader "
            "says they contradict each other. Given every note built from them, the reader answers no, the user "
            "has never met Kelly at such an event. Across 90 questions with evidence messages, answers from the "
            f"messages scored {w['oracle_raw']} and answers from the notes scored {w['oracle_memory']}.")
    return svg(680, h, "Where the book club went", desc, body)


def result():
    body, y = header("The notes lost evidence, and still came out ahead", [
        "Mean rubric score out of 100, with the 95% interval of the notes'",
        "lead or deficit. Claude Haiku 5.5 read every answer context."])
    p, w, t = S["primary"], S["secondary"]["lost_while_writing"], S["exploratory"]["tight"]
    groups = [
        (f"EVERY EVIDENCE MESSAGE HANDED OVER, {w['n']} QUESTIONS", "", [
            ("The original messages", w["oracle_raw"], False), ("Every note built from them", w["oracle_memory"], True)], w),
        (f"SEARCHED, ABOUT 21,000 CHARACTERS EACH, {p['n']} QUESTIONS", "PRE-REGISTERED", [
            ("Ten most similar messages", p["raw"], False), ("Most similar notes, same length", p["memory"], True)], p),
        (f"SEARCHED, ABOUT 1,000 TOKENS EACH, {t['n']} QUESTIONS", "ADDED AFTER THE RESULT", [
            ("Messages, the last one cut to fit", t["raw_tight"], False), ("Most similar notes", t["memory_tight"], True)], t),
    ]
    X0, W = 270, 230
    y += 30
    body.append(text(640, y, "NOTES MINUS MESSAGES", "sans label", "end"))
    y += 16
    for title, tag, rows, d in groups:
        y += 14
        body.append(text(32, y, title, "sans label"))
        if tag:
            body.append(text(32, y + 15, tag, "sans label-warn" if "AFTER" in tag else "sans label-ok"))
            y += 15
        y += 10
        for k, (name, v, notes) in enumerate(rows):
            cy = y + 18
            bw = W * v / 100
            fill = AMBER if notes else GREEN
            body.append(text(32, cy, name, "sans row"))
            body.append(f'  <rect x="{X0}" y="{y + 4}" width="{bw:.1f}" height="18" fill="{fill}"/>')
            body.append(text(round(X0 + bw + 6, 1), cy, f"{v:.1f}", "sans val-warn" if notes else "sans val"))
            if k == 1:
                body.append(text(640, cy - 16, f"{d['diff']:+.1f}", "sans row", "end"))
                body.append(text(640, cy + 2, f"{d['lo']:+.1f} to {d['hi']:+.1f}", "sans num", "end"))
            y += 30
        y += 12
    y += 10
    body += lines(32, y, [
        "Each question is scored against BEAM's rubric, 1, 0.5 or 0 per item, by Claude Haiku 5.5,",
        "blind to which context produced the answer. Pairs with an unscored reply are left out.",
        "Five BEAM-100K conversations, one sampled run per question."], "sans foot")
    h = y + 40 + 16
    desc = (f"Three comparisons. With every evidence message handed over, on {w['n']} questions, answers from "
            f"the original messages scored {w['oracle_raw']} and answers from the notes built from them scored "
            f"{w['oracle_memory']}, a difference of {w['diff']:+.1f} (interval {w['lo']:+.1f} to {w['hi']:+.1f}). "
            f"Searched, with about 21,000 characters of context each, on {p['n']} questions, the pre-registered "
            f"test: ten most similar messages {p['raw']}, notes {p['memory']}, difference {p['diff']:+.1f} "
            f"(interval {p['lo']:+.1f} to {p['hi']:+.1f}). Searched at about 1,000 tokens, added after the result, "
            f"on {t['n']} questions: messages {t['raw_tight']}, notes {t['memory_tight']}, difference "
            f"{t['diff']:+.1f} (interval {t['lo']:+.1f} to {t['hi']:+.1f}).")
    return svg(680, h, "The notes lost evidence, and still came out ahead", desc, body)


def architecture():
    body, y = header("Keep the messages; let the notes point back", [
        "A shape for a long-running assistant. Green was built and measured",
        "here; grey is from the paper; amber is untested glue."])
    y += 18
    # Write path
    body.append(text(32, y, "WRITE PATH, AFTER EACH EXCHANGE", "sans label"))
    y += 12
    body.append(rect(32, y, 180, 70, PANEL, PANEL_EDGE))
    body += lines(46, y + 28, ["Message log", "append-only, kept"], "sans box", 20)
    body.append(arrow(212, y + 35, 240, y + 35))
    body.append(rect(242, y, 196, 70, GREEN_BG, GREEN))
    body += lines(256, y + 28, ["Note writer", "extract, then update"], "sans box", 20)
    body.append(arrow(438, y + 35, 466, y + 35))
    body.append(rect(468, y, 180, 70, GREEN_BG, GREEN))
    body += lines(482, y + 28, ["Notes", "each with message ids"], "sans box", 20)
    y += 70 + 34
    # Read path
    body.append(text(32, y, "READ PATH, FOR EACH QUESTION", "sans label"))
    y += 12
    body.append(rect(32, y, 296, 64, PANEL, PANEL_EDGE))
    body += lines(46, y + 26, ["Search the messages", "embeddings plus keywords"], "sans box", 20)
    body.append(rect(352, y, 296, 64, GREEN_BG, GREEN))
    body += lines(366, y + 26, ["Search the notes", "same budget as the messages"], "sans box", 20)
    body.append(arrow(180, y + 64, 180, y + 92))
    body.append(arrow(500, y + 64, 500, y + 92))
    y += 64 + 30
    body.append(rect(32, y, 616, 84, AMBER_BG, AMBER))
    body.append(text(46, y + 26, "Open the messages behind the top notes", "sans box"))
    body += lines(46, y + 48, ["when the question asks for a detail, a date, or a yes or no about",
                               "something the user said; show both sides when two sources disagree"],
                  "sans small", 19)
    body.append(arrow(340, y + 84, 340, y + 110))
    y += 84 + 28
    body.append(rect(220, y, 240, 48, PANEL, PANEL_EDGE))
    body.append(text(340, y + 30, "Reader writes the reply", "sans box", "middle"))
    y += 48 + 34
    # Controls
    body.append(text(32, y, "CONTROLS", "sans label"))
    y += 12
    ctrl = [
        (GREEN_BG, GREEN, "Oracle split, monthly", ["give the reader the evidence,", "then the notes made from it"]),
        (AMBER_BG, AMBER, "Deletion follows ids", ["deleting a message deletes", "or rewrites its notes"]),
        (PANEL, PANEL_EDGE, "Compare with plain search", ["the paper's baseline, on the", "same budget, before launch"]),
    ]
    for i, (bg, edge, title, rows) in enumerate(ctrl):
        x = 32 + i * 210
        body.append(rect(x, y, 196, 92, bg, edge))
        body.append(text(x + 12, y + 26, title, "sans box"))
        body += lines(x + 12, y + 50, rows, "sans small", 19)
    y += 92 + 34
    body += lines(32, y, [
        "Only the note writer, the provenance ids and the oracle split ran in this prototype.",
        "Nothing here measured the step that opens the messages behind a note."], "sans foot")
    h = y + 20 + 16
    desc = ("Write path: every exchange is appended to a message log that is never discarded; a note writer "
            "extracts facts and then updates the notes, and every note records the ids of the messages it came "
            "from. Read path: the question searches both the messages, with embeddings plus keywords, and the "
            "notes, at the same budget. An untested step then opens the messages behind the top notes when the "
            "question asks for a detail, a date, or a yes or no about something the user said, and shows both "
            "sides when sources disagree, before the reader writes the reply. Controls: a monthly oracle split, "
            "deletion that follows message ids, and a comparison with plain search before launch. Only the note "
            "writer, the provenance ids and the oracle split ran in the prototype.")
    return svg(680, h, "Keep the messages; let the notes point back", desc, body)


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    (out / "mechanism-overview.svg").write_text(mechanism())
    (out / "prototype-result.svg").write_text(result())
    (out / "reference-architecture.svg").write_text(architecture())


if __name__ == "__main__":
    main()
