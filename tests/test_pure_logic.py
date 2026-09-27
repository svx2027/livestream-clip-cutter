"""Tests for the credential-free, file-free logic in scripts/03, 04, 05.

These three scripts each mix real file I/O (reading transcripts/clip-segments
that only exist after a real mlx-whisper run on Apple Silicon) with small pure
functions: timestamp formatting, word-span text extraction, and Devanagari-
script-ratio detection. The I/O halves cannot run in CI (no GPU, no audio, no
Apple Silicon); the pure halves need nothing but stdlib and are exactly the
logic that decides what an editor is shown, so they are what this suite pins.

Each script is loaded by file path (their numeric-prefixed filenames are not
importable module names) and never executes its module-level I/O, because that
I/O now only runs under ``if __name__ == "__main__":``.
"""
import importlib.util
import os
import sys
import unittest

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")


def load(filename):
    path = os.path.join(SCRIPTS, filename)
    name = filename.rsplit(".", 1)[0]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build_views = load("03_build_views.py")
verify_windows = load("04_verify_windows.py")
reconcile = load("05_reconcile_language.py")


class TestHms(unittest.TestCase):
    """Both 03 and 04 define hms(); 04's differs from 03/05's in one detail
    (h:MM:SS vs h:01d), so each copy is pinned separately rather than assuming
    they behave the same way."""

    def test_build_views_hms_under_an_hour_has_no_hour_field(self):
        self.assertEqual(build_views.hms(0), "00:00")
        self.assertEqual(build_views.hms(65), "01:05")
        self.assertEqual(build_views.hms(59.9), "00:59")

    def test_build_views_hms_over_an_hour_includes_hour_field(self):
        self.assertEqual(build_views.hms(3661), "1:01:01")

    def test_verify_windows_hms_matches_same_shape(self):
        self.assertEqual(verify_windows.hms(0), "00:00")
        self.assertEqual(verify_windows.hms(65), "01:05")
        self.assertEqual(verify_windows.hms(3661), "1:01:01")

    def test_reconcile_hms_truncates_rather_than_rounds(self):
        # int(t) truncation, unlike the float-based hms in the other two scripts
        self.assertEqual(reconcile.hms(59.9), "00:59")
        self.assertEqual(reconcile.hms(3600), "1:00:00")


class TestSpanText(unittest.TestCase):
    def setUp(self):
        # (start, end, word) tuples, matching load_words()'s output shape
        self.words = [
            (10.0, 10.4, "So"),
            (10.4, 10.6, "the"),
            (10.6, 11.0, "answer"),
            (11.0, 11.3, "is"),
            (11.3, 11.8, "yes."),
            (20.0, 20.5, "Unrelated"),
        ]

    def test_exact_window_returns_snapped_bounds_and_joined_text(self):
        sa, sb, text = verify_windows.span_text(10.0, 11.8, self.words)
        self.assertEqual((sa, sb), (10.0, 11.8))
        self.assertEqual(text, "So the answer is yes.")

    def test_pad_pulls_in_a_word_that_starts_slightly_outside_the_window(self):
        # word "So" starts at 10.0; without pad, a window starting at 10.1
        # would fall back to the overlap path and still find it (it overlaps),
        # but a tight window with pad=0 that starts after the word ends should not.
        sa, sb, text = verify_windows.span_text(10.4, 11.8, self.words, pad=0.0)
        self.assertNotIn("So", text)
        sa, sb, text = verify_windows.span_text(10.4, 11.8, self.words, pad=0.5)
        self.assertIn("So", text)

    def test_no_word_in_or_overlapping_range_returns_none(self):
        self.assertIsNone(verify_windows.span_text(100.0, 101.0, self.words))

    def test_falls_back_to_overlap_when_no_word_is_fully_inside(self):
        # a single word spanning the whole requested window (starts before,
        # ends after) has no word strictly inside [a, b], so the strict pass
        # finds nothing and the overlap fallback must still return it.
        words = [(5.0, 15.0, "straddling")]
        result = verify_windows.span_text(8.0, 9.0, words)
        self.assertIsNotNone(result)
        self.assertEqual(result[2], "straddling")


class TestDevRatio(unittest.TestCase):
    def test_empty_or_whitespace_string_is_zero(self):
        self.assertEqual(reconcile.dev_ratio(""), 0.0)
        self.assertEqual(reconcile.dev_ratio("   "), 0.0)

    def test_pure_latin_text_is_zero(self):
        self.assertEqual(reconcile.dev_ratio("so the answer is yes"), 0.0)

    def test_pure_devanagari_text_is_one(self):
        # "namaste" in Devanagari
        self.assertEqual(reconcile.dev_ratio("नमस्ते"), 1.0)

    def test_mixed_script_is_between_zero_and_one(self):
        r = reconcile.dev_ratio("so नमस्ते friend")
        self.assertGreater(r, 0.0)
        self.assertLess(r, 1.0)

    def test_digits_and_punctuation_are_not_counted_as_base_characters(self):
        # only alphabetic (Latin or Devanagari) characters count toward the
        # denominator, so a numbers-only string is 0/0 -> 0.0, not a crash
        self.assertEqual(reconcile.dev_ratio("123 456!"), 0.0)


if __name__ == "__main__":
    unittest.main()
