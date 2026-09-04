# livestream-clip-cutter

Turn a long, bilingual educational livestream into a **cut-list**: a set of
short, vertical-clip candidates with exact in/out timestamps, the verbatim
question or hook as the on-screen header, and a language note on every
window. This repo produces the cut-list data (JSON + text reports) that a
video editor works from -- it does **not** render or export clips itself.

## The problem this solves

A 60-90 minute livestream Q&A usually has a handful of moments worth cutting
into standalone vertical clips: a sharp answer to a chat question, a strong
standalone teaching moment. Finding them by scrubbing the timeline by hand is
slow. Worse, on a bilingual (e.g. English-Hindi) stream, a clip that *reads*
clean in a transcript can still have a stretch of the other language buried
in the actual audio -- and the transcript won't tell you, because of how
speech-to-text handles a language it's forced to expect.

## The core finding: a forced-language transcript cannot certify language

If you force Whisper to transcribe in English, it doesn't fail or flag the
parts that were actually spoken in Hindi -- it **translates them to plausible
English, or drops them**. The output reads as fluent, coherent English even
over audio that code-switches. A clip selected from that transcript alone can
still be full of untranslated, on-camera Hindi with no sign of it in the text
that greenlit the clip.

The fix is a second, independent pass: re-transcribe each *candidate window
only* (not the whole file) with the language forced the other way. Read what
comes back:
- Latin-script text, or the primary language's words merely transliterated
  into the secondary script, means the audio really is the primary language.
- Genuine secondary-language grammar (real postpositions, real verb forms,
  not just loanwords) means the audio really does contain that language, and
  the span should be flagged for the editor to trim.

In practice, this has caught genuine code-switching that an English-forced
transcript alone rendered as clean -- the second pass is not a formality. A
deeper write-up of that finding, and of two dead-end approaches that don't
work (a full-file forced-secondary pass hallucinates repetition loops; a
naive multi-file transcription call silently collides every output into one
file), is coming in a follow-up pass on this repo.

## Pipeline

Script numbers reflect each step's role in the pipeline, not the order you
run them in -- `06`/`06b` (the decisive language check) run before `05` (a
coarser variant of the same check); see Reproduce below for the real order.

```
scripts/01_download_audio.sh   audio-only fetch (yt-dlp, m4a) -- no video file ever touches disk
scripts/02_transcribe.sh       local transcription (mlx-whisper), word-level timestamps
scripts/03_build_views.py      -> analysis/transcript_en_segments.txt + transcript_en_words.jsonl
  [ clip windows are selected here, into analysis/clip-segments.json -- this
    step is human/model judgment, not a script; see "Selecting clips" below ]
scripts/04_verify_windows.py   word-exact text per window, boundary-snap, 20-60s check
scripts/06_window_hi_check.sh  extracts each candidate window to its own WAV
scripts/06b_window_hi_each.py  the decisive per-window secondary-language re-read
scripts/05_reconcile_language.py   a coarser, full-transcript version of the same check
```

## Reproduce

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # ffmpeg must also be on PATH, installed separately

bash   scripts/01_download_audio.sh "<youtube-url>"
bash   scripts/02_transcribe.sh en primary      # primary-language pass, word timestamps
bash   scripts/02_transcribe.sh hi secondary    # optional coarse full-file cross-check
python scripts/03_build_views.py

# Now select clip windows into analysis/clip-segments.json (see "Selecting
# clips" below) -- this is the one step this repo does not automate.

python scripts/04_verify_windows.py
bash   scripts/06_window_hi_check.sh            # runs 06b_window_hi_each.py internally
python scripts/05_reconcile_language.py         # optional, coarser full-transcript view
```

### `analysis/clip-segments.json` shape

```json
{
  "clips": [
    {
      "id": "ama-01",
      "type": "ama",
      "priority": "high",
      "header": "The verbatim chat question, verbatim",
      "answer_start": 2312.4,
      "suggested_in": 2308.0,
      "suggested_out": 2351.5
    }
  ]
}
```

Clip selection itself is a judgment call over `analysis/transcript_en_segments.txt`
(find the moments worth cutting, note where each answer starts, sanity a
20-60s window around it) -- this repo does not include an automated selector,
because "is this moment worth a clip" is exactly the kind of call that should
stay a human or a closely-supervised model decision, not a heuristic.

## Honest scope

- **Apple Silicon only.** `mlx-whisper` needs Metal; this pipeline does not
  run as-is on Linux or an Intel Mac. A `faster-whisper`/CPU fallback would
  work but is meaningfully slower and isn't wired up here.
- **Data, not video.** Nothing in this repo renders, trims, or exports an
  actual clip file. The output is exact timestamps and verified text for an
  editor (or a downstream tool) to cut from.
- **Bilingual English/Hindi is the case this was built and tuned for.** The
  language-reconciliation scripts assume a primary/secondary language pair
  and a Devanagari-script check; a different language pair needs a different
  script-detection rule in `scripts/05_reconcile_language.py`.
- **Suggested windows are starting points.** Even a window that passes every
  check here is worth an editor's ear -- word timestamps drift by roughly a
  second, and "make one complete point and flow naturally" is a judgment call
  no script makes for you.
- **A document/cut-sheet exporter is not included in this initial port.** The
  pipeline here stops at verified, language-checked clip data; turning that
  into a shareable document for an editor is a natural next piece, not yet
  ported.

## Requirements

- Python 3.10+, a `.venv` (see Reproduce above)
- [`yt-dlp`](https://github.com/yt-dlp/yt-dlp)
- [`ffmpeg`](https://ffmpeg.org/) on `PATH`
- An Apple-Silicon Mac (M-series) for `mlx-whisper`

No API keys or secrets are needed anywhere in this pipeline.
