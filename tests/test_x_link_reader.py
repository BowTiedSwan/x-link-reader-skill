import unittest

from scripts.x_link_reader import extract_article_text, parse_target


class ParseTargetTests(unittest.TestCase):
    def test_parse_singular_article_url(self):
        parsed = parse_target("https://x.com/i/article/2053500074588532736")

        self.assertEqual(parsed["id"], "2053500074588532736")
        self.assertEqual(parsed["url_kind"], "article")
        self.assertEqual(
            parsed["normalized_url"],
            "https://x.com/i/article/2053500074588532736",
        )

    def test_parse_plural_article_url(self):
        parsed = parse_target("https://x.com/i/articles/2053500074588532736")

        self.assertEqual(parsed["id"], "2053500074588532736")
        self.assertEqual(parsed["url_kind"], "article")
        self.assertEqual(
            parsed["normalized_url"],
            "https://x.com/i/article/2053500074588532736",
        )


class ExtractArticleTextTests(unittest.TestCase):
    def test_extracts_direct_text(self):
        self.assertEqual(
            extract_article_text({"text": "Full article body"}),
            "Full article body",
        )

    def test_extracts_nested_article_blocks(self):
        payload = {
            "content": {
                "sections": [
                    {"text": "Intro paragraph"},
                    {"content": [{"text": "Body paragraph"}]},
                ]
            }
        }

        self.assertEqual(
            extract_article_text(payload),
            "Intro paragraph\n\nBody paragraph",
        )


if __name__ == "__main__":
    unittest.main()
