#!/usr/bin/env python3
"""Build human/agent-friendly views from the word-level primary-language transcript.
Assumes the primary-language pass was run as "en" (scripts/02_transcribe.sh en primary);
change SRC below if your primary language is a different code.
Outputs:
  analysis/transcript_en_segments.txt  -> [HH:MM:SS] segment text (whole recording)
  analysis/transcript_en_words.jsonl   -> one JSON object per segment: {start,end,text,words:[{w,s,e}]}
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "transcripts", "en", "audio.json")
OUTDIR = os.path.join(ROOT, "analysis")
os.makedirs(OUTDIR, exist_ok=True)

def hms(t):
    t = float(t); h = int(t//3600); m = int((t%3600)//60); s = int(t%60)
    return f"{h:01d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

data = json.load(open(SRC))
segs = data.get("segments", [])

seg_path = os.path.join(OUTDIR, "transcript_en_segments.txt")
wrd_path = os.path.join(OUTDIR, "transcript_en_words.jsonl")
with open(seg_path, "w") as f, open(wrd_path, "w") as g:
    for s in segs:
        text = (s.get("text") or "").strip()
        f.write(f"[{hms(s['start'])}] {text}\n")
        words = [{"w": w.get("word", "").strip(), "s": round(w.get("start", 0), 2),
                  "e": round(w.get("end", 0), 2)} for w in s.get("words", [])]
        g.write(json.dumps({"start": round(s["start"], 2), "end": round(s["end"], 2),
                            "text": text, "words": words}, ensure_ascii=False) + "\n")

dur = segs[-1]["end"] if segs else 0
print(f"segments: {len(segs)}  last_end: {hms(dur)}")
print(f"wrote: {seg_path}")
print(f"wrote: {wrd_path}")
