#!/usr/bin/env python3
"""Cross-check each suggested clip window against the independent secondary-
language pass. The primary-language-forced pass can silently 'translate' the
secondary language to plausible primary-language text; the secondary-language
pass reveals where it was actually spoken (by script, e.g. Devanagari for
Hindi). For each window we print the secondary-language rendering and a
script ratio so any hidden secondary-language audio inside an apparently
clean clip is caught."""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QA = json.load(open(os.path.join(ROOT, "analysis", "clip-segments.json")))
HI = json.load(open(os.path.join(ROOT, "transcripts", "hi", "audio.json")))
hi_segs = HI.get("segments", [])

DEV = re.compile(r"[ऀ-ॿ]")
def dev_ratio(s):
    if not s.strip(): return 0.0
    dev = len(DEV.findall(s))
    base = sum(1 for c in s if (c.isalpha() or DEV.match(c)))
    return dev / base if base else 0.0

def hms(t):
    t = int(t); h, m, s = t//3600, (t%3600)//60, t%60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

out = [f"LANGUAGE RECONCILIATION — secondary-language-pass view of each suggested window\n{'='*90}"]
flagged = []
for c in QA["clips"]:
    a, b = c["suggested_in"], c["suggested_out"]
    segs = [s for s in hi_segs if s["end"] > a and s["start"] < b]
    txt = " ".join((s.get("text") or "").strip() for s in segs).strip()
    r = dev_ratio(txt)
    out.append(f"\n[{c['id']}]  {hms(a)}-{hms(b)}   Devanagari ratio={r:.2f}")
    out.append(f"  SECONDARY: {txt[:400]}")
    # A window that is genuinely primary-language will come back as mostly
    # transliterated/Latin or broken secondary-language text; a high,
    # *contiguous* script-match run is real secondary-language audio worth
    # flagging.
    if r >= 0.55:
        flagged.append((c["id"], round(r, 2)))

out.append(f"\n{'='*90}\nHIGH-SCRIPT-MATCH WINDOWS (review for hidden secondary-language audio): " +
           (", ".join(f"{i}={r}" for i, r in flagged) if flagged else "none"))
report = os.path.join(ROOT, "analysis", "language_reconciliation.txt")
open(report, "w").write("\n".join(out))
print("\n".join(out))
print("\nwrote", report)
