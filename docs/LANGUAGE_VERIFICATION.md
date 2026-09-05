# Why a forced-language transcript can't certify a clip's language

Field notes from building this pipeline's language check. If you're adapting this
repo for a different bilingual source, read this before touching
`scripts/05_reconcile_language.py` or `scripts/06b_window_hi_each.py` — it explains
why the check is shaped the way it is, and two approaches that look reasonable but
don't work.

## The decisive finding

Forcing a speech-to-text model to transcribe in one language does not make it fail,
or flag, or leave a gap where the speaker actually used a different language. It
**translates that stretch into plausible text in the forced language, or drops it
outright.** The transcript comes back fluent and internally consistent even where
the underlying audio code-switches.

The practical consequence: a clip whose only quality gate is "does the transcript
read as clean [language A]" can still contain untranslated [language B] on the
actual audio, with nothing in the text that approved the clip hinting at it.
**A transcript being clean in the target language is not evidence that the audio
is.** That distinction is the entire reason this pipeline runs a second,
independent pass per window instead of trusting the primary transcript alone.

## Two things that look like a fix and aren't

**A full-file pass with the language forced the other way, run on a fast/small
model.** The intent is reasonable — force the opposite language, see what comes
back, use that to spot code-switched stretches. In practice, a fast model forced
into the wrong language over a long recording degenerates into repetition loops
(the same word or short phrase repeated for lines at a time) far more often than it
produces a useful transcript, and forcing the "wrong" language onto genuinely
in-language speech transliterates it into the other script instead of leaving it
alone — so a same-script-density heuristic can't reliably tell the two apart either.
A full-file, wrong-model pass is not a substitute for the per-window check below.

**Passing every candidate window as separate files to one CLI invocation.** Doing
this to save on model-load time seems free — the model only has to load once
either way. It isn't: at least one popular CLI transcription tool silently writes
only the *last* file's output, saved under *every* input file's name. Every window
except the last ends up holding a copy of a different clip's transcript, and
nothing about the run looks like it failed. The fix that actually works and still
only pays the model-load cost once is a loop over the **library's Python API**
(`06b_window_hi_each.py`), not the CLI, transcribing one window at a time and
writing each result under its own filename explicitly.

## What actually works

Re-transcribe **only the candidate windows** (not the whole file) with the
secondary language forced, using the same full-quality model you used for the
primary pass — not the fast/small one. A single window is short enough that the
full model doesn't meaningfully cost more time than the fast one would have, and it
does not hallucinate the way the fast model does over a full recording.

Reading the output takes a second judgment call, because the secondary-language
pass alone is not self-explanatory either:

- **Loanwords or the primary language merely transliterated into the secondary
  script** still mean the audio is the primary language. A term borrowed from the
  primary language, or an English phrase rendered in Devanagari letters, is not
  evidence of code-switching by itself.
- **Genuine secondary-language grammar** — real postpositions, real verb
  conjugations, sentence structure that isn't just a borrowed noun sitting inside a
  primary-language sentence — means the speaker actually switched languages for
  that stretch, and the window should be flagged for the editor to trim.

Illustrative example only (not from a real run): if a fitness-coaching Q&A clip's
secondary-language pass comes back as `"progressive overload बहुत ज़रूरी है"` (a
transliterated English fitness term inside a genuine Hindi sentence, with a real
Hindi verb and copula), that's a real code-switch worth flagging — as opposed to
`"प्रोग्रेसिव ओवरलोड सेट"`, which is just the same English phrase spelled out in
Devanagari with no Hindi grammar attached, i.e. still English content.

**Rule of thumb:** never trust one forced-language pass to certify a clip's
language. Always run the per-window secondary re-read, and treat even a window
that passes it as worth an editor's ear before it ships — word-level timestamps
drift by roughly a second either way, so "clean" from this check still means
"clean, pending a human listen," not "verified beyond review."

## Smaller gotchas worth knowing before you re-run this

- **Turn on verbose output and disable Python's stdout buffering** if you want to
  watch progress live. A local transcription model that writes output only at the
  very end, piped through Python's default (block-buffered, not line-buffered)
  stdout, looks identical to a hung process for the full runtime — for a
  60-90 minute recording, that's 15+ minutes of silence with real work happening
  underneath.
- **If you grep a progress log for error keywords, exclude the transcript lines
  themselves first.** A transcript is free-form spoken text; sooner or later a
  segment will contain a word like "exception," "error," or "killed" as ordinary
  vocabulary, and a naive grep across the whole log will false-positive on it.
  Filter to non-transcript lines (this pipeline's transcript lines all start with
  a `[` timestamp) before scanning for real failures.
- **Expect ASR to occasionally garble proper nouns, acronyms, and brand names into
  unrelated-sounding words or syllables.** This is harmless for this pipeline
  specifically, because window boundaries come from timestamps, not from the
  transcript text — the editor cuts from the audio, and only the on-screen header
  text (which a human writes or reviews) needs to be correct.
- **A bilingual pair other than English/Hindi needs its own script-detection
  rule.** `scripts/05_reconcile_language.py`'s coarse full-transcript check keys off
  the Devanagari Unicode block specifically; swap in the right script range (or a
  language-ID model) for a different secondary language, and rely on the per-window
  grammar read above regardless of which script you're checking.
