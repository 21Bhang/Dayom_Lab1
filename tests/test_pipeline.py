import unittest

from core.ingestion_pipeline import apply_filter_terms, clean_text, make_record
from core.sentiment_analyzer import analyze_sentiment
from core.translation_engine import translate_text


class PipelineTests(unittest.TestCase):
    def test_preserves_nuer_orthography_and_cleans_social_noise(self):
        self.assertEqual(clean_text(" @user  ä ö ɛ ɔ https://example.org 🙂 #hello "), "ä ö ɛ ɔ hello")

    def test_mask_matches_whole_terms_case_insensitively(self):
        result = apply_filter_terms("Badword badwordish", ["Badword"], "mask")
        self.assertEqual(result.text, "[FILTERED] badwordish")
        self.assertEqual(result.matches, ("Badword",))

    def test_exclude_and_keep_modes(self):
        excluded = apply_filter_terms("example term here", ["term"], "exclude")
        kept = apply_filter_terms("example term here", ["term"], "keep")
        self.assertEqual(excluded.text, "")
        self.assertEqual(kept.text, "example term here")
        self.assertEqual(excluded.matches, ("term",))

    def test_output_uses_common_schema(self):
        record = make_record({"text": "ä ɔ"}, language_code="nus")
        self.assertEqual(record["language_code"], "nus")
        self.assertEqual(record["cleaned_text"], "ä ɔ")
        self.assertIsNone(record["english_translation"])
        self.assertIn("toxicity_score", record["annotations"])

    def test_unconfigured_providers_do_not_fabricate_results(self):
        self.assertIsNone(translate_text("text", "nus", "eng"))
        self.assertIsNone(analyze_sentiment("text", "nus")["sentiment"])


if __name__ == "__main__":
    unittest.main()
