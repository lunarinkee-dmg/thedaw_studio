"""Offline regressions for HTML fallback date discovery."""
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
import aggregate

class HtmlFallbackTests(unittest.TestCase):
    def test_meta_and_json_dates(self):
        homepage = '<a href="/news/new-album">A sufficiently long music article title</a>'
        for article in [
            '<meta property="article:published_time" content="2026-10-12T10:30:00Z">',
            "<meta name='pubdate' content='2026-10-12T10:30:00Z'>",
            '<script type="application/ld+json">{"datePublished" : "2026-10-12T10:30:00Z"}</script>',
        ]:
            with self.subTest(article=article), patch.object(aggregate, 'fetch', side_effect=[
                (homepage.encode(), 'https://example.com'),
                (article.encode(), 'https://example.com/news/new-album'),
            ]), patch.object(aggregate, 'NOW', datetime(2026, 10, 12, 11, tzinfo=timezone.utc)):
                items = aggregate.html_fallback('The Flow', 'Музыка', 'https://example.com')
                self.assertEqual(len(items), 1)
                self.assertEqual(items[0]['published_at'], '2026-10-12T10:30:00+00:00')

if __name__ == '__main__':
    unittest.main()
