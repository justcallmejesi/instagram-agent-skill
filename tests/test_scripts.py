"""Checks for the Python tools. Run from the repo root:

    python3 -m unittest discover tests
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for folder in ("ig-caption", "ig-human", "ig-reel", "ig-viral"):
    sys.path.insert(0, os.path.join(ROOT, "skills", folder))

import beats       # noqa: E402
import caption     # noqa: E402
import detect      # noqa: E402
import hookscore   # noqa: E402
import humanize    # noqa: E402
import swipe       # noqa: E402

LEX = humanize.load_lexicon()


class Russian(unittest.TestCase):
    def test_caption_counts_cyrillic_tags_and_asks(self):
        a = caption.analyse("Сохрани этот пост.\n#фриланс #договор #юрист #бизнес #маркетинг #продажи")
        self.assertEqual(len(a["hashtags"]), 6)
        self.assertEqual(a["asks"], ["save this"])

    def test_hook_gets_a_real_score(self):
        self.assertEqual(hookscore.run("Я потерял 180 000 рублей на одном пункте договора")[2], "STRONG")
        self.assertEqual(len(hookscore.run("Привет всем, сегодня расскажу про договоры")[3]), 2)

    def test_humanize_keeps_the_dash_grammatical(self):
        out, _ = humanize.humanize(
            "Договор — это защита.\n— Первый пункт\nВажно отметить, что всё просто.", LEX)
        self.assertEqual(out, "Договор - это защита.\n- Первый пункт\nВсё просто.\n")

    def test_detect_reads_cyrillic_words(self):
        text = "Я потерял 180 000 рублей на договоре. " * 6
        self.assertNotIn("too short", detect.check_voice(text, LEX)[1])

    def test_beats_counts_cyrillic_words(self):
        self.assertEqual(beats.analyse("Я потерял 180 000 рублей.", wpm=140)["total_words"], 5)

    def test_swipe_names_the_formula(self):
        formulas = swipe.load_formulas(swipe.HOOKS)
        hook = "Никто не говорит, что первые 30 рилсов провалятся"
        self.assertEqual(swipe.classify(hook, formulas)[0], 3)


class Fixes(unittest.TestCase):
    def test_every_example_matches_its_own_formula(self):
        formulas = swipe.load_formulas(swipe.HOOKS)
        with open(swipe.HOOKS, encoding="utf-8") as fh:
            for h in json.load(fh)["hooks"]:
                self.assertEqual(swipe.classify(h["example"], formulas)[0], h["id"], h["example"])

    def test_weak_opener_is_a_whole_word(self):
        detail = hookscore.check_frontload("Your first 30 reels are supposed to flop")[1]
        self.assertNotIn("weak opener", detail)

    def test_deleted_slop_leaves_no_orphan_punctuation(self):
        out, _ = humanize.humanize(
            "It works. Here's the thing, nobody reads.\nGreat tips.\nSave this for later!\n", LEX)
        self.assertEqual(out, "It works. Nobody reads.\nGreat tips.\n")

    def test_leading_ellipsis_survives(self):
        out, _ = humanize.humanize("…and that is when the client asked for the money back.", LEX)
        self.assertTrue(out.startswith("...and"))

    def test_heart_emoji_counts_once(self):
        self.assertEqual(caption.analyse("Love this ❤️")["emoji"], 1)

    def test_swipe_out_takes_a_bare_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            tsv = os.path.join(tmp, "in.tsv")
            with open(tsv, "w", encoding="utf-8") as fh:
                fh.write("account\tfollowers\tviews\thook\n@a\t1000\t50000\tstop doing this\n")
            script = os.path.join(ROOT, "skills", "ig-viral", "swipe.py")
            subprocess.run([sys.executable, script, tsv, "--out", "swipe.md"],
                           cwd=tmp, check=True, capture_output=True)
            self.assertTrue(os.path.exists(os.path.join(tmp, "swipe.md")))


if __name__ == "__main__":
    unittest.main()
