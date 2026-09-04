#!/usr/bin/env python3
"""Verify each clip window in analysis/clip-segments.json against the word-level
primary-language transcript: extract exact spoken text, snap boundaries to word
edges, check the 20-60s rule, and surface the answer-start context.
Prints a human-readable report (does not modify the JSON)."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORDS = os.path.join(ROOT, "analysis", "transcript_en_words.jsonl")
QA = os.path.join(ROOT, "analysis", "clip-segments.json")

def hms(t):
    t = float(t); h = int(t//3600); m = int((t%3600)//60); s = int(t%60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

# flat word list
W = []
for line in open(WORDS):
    seg = json.loads(line)
    for w in seg.get("words", []):
        if w.get("w"):
            W.append((float(w["s"]), float(w["e"]), w["w"]))
W.sort()

def span_text(a, b, pad=0.0):
    ws = [x for x in W if x[0] >= a - pad and x[1] <= b + pad]
    if not ws:
        # fallback: words overlapping the range
        ws = [x for x in W if x[1] > a and x[0] < b]
    if not ws:
        return None
    text = " ".join(x[2] for x in ws).replace("  ", " ").strip()
    return ws[0][0], ws[-1][1], text

qa = json.load(open(QA))
print(f"{'='*100}\nCLIP WINDOW VERIFICATION  ({len(qa['clips'])} clips)\n{'='*100}")
flags = []
for c in qa["clips"]:
    a, b = c["suggested_in"], c["suggested_out"]
    dur = b - a
    snap = span_text(a, b, pad=0.4)
    print(f"\n[{c['id']}] ({c['type']}/{c['priority']})  {c['header']}")
    print(f"  suggested window : {hms(a)}-{hms(b)}  ({dur}s)")
    if snap:
        sa, sb, text = snap
        print(f"  word-snapped     : {hms(sa)}-{hms(sb)}  ({int(sb-sa)}s)")
        print(f"  TEXT: {text}")
    else:
        print("  TEXT: <none found>")
    # answer-start context (first ~8 words at/after answer_start)
    astart = c.get("answer_start", a)
    fw = [x for x in W if x[0] >= astart - 0.5][:9]
    if fw:
        print(f"  answer-start @{hms(astart)} -> \"{' '.join(x[2] for x in fw).strip()} ...\"")
    if dur < 20: flags.append((c["id"], f"TOO SHORT ({dur}s < 20)"))
    if dur > 60: flags.append((c["id"], f"TOO LONG ({dur}s > 60)"))

print(f"\n{'='*100}\nFLAGS:")
print("\n".join(f"  {i}: {m}" for i, m in flags) if flags else "  none — all windows within 20-60s")
