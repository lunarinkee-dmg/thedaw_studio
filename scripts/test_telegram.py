"""Offline regression tests for Telegram public channel parsing."""
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from io import BytesIO
from telegram import collect_telegram, TelegramMessages


HTML = '''
<html><body>
<div class="tgme_widget_message_wrap">
 <div class="tgme_widget_message js-widget_message" data-post="quicknrapp/12345">
  <div class="tgme_widget_message_bubble">
   <div class="tgme_widget_message_text js-message_text">
     Новая музыка от артиста <b>сегодня</b><br/>Скоро выходит альбом!
   </div>
   <a class="tgme_widget_message_date" href="https://t.me/quicknrapp/12345">
    <time datetime="2026-10-12T10:30:00+00:00">10:30</time>
   </a>
  </div>
 </div>
</div>
<div class="tgme_widget_message_wrap">
 <div class="tgme_widget_message" data-post="quicknrapp/12346">
  <div class="tgme_widget_message_text">Ещё одна интересная публикация для читателей</div>
  <time datetime="2026-10-12T10:40:00+00:00"></time>
 </div>
</div>
</body></html>
'''


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return HTML.encode("utf-8")


class TelegramParsingTests(unittest.TestCase):
    def test_nested_html_and_messages(self):
        parser = TelegramMessages()
        parser.feed(HTML)
        parser.finish()
        self.assertEqual(len(parser.messages), 2)
        self.assertIn("сегодня", parser.messages[0]["text"])
        self.assertEqual(parser.messages[0]["date"], "2026-10-12T10:30:00+00:00")

    @patch("telegram.urllib.request.urlopen", return_value=FakeResponse())
    def test_feed_contract_and_stable_ids(self, _):
        items = collect_telegram(
            "Quick N Rapp", "Музыка / Рэп",
            "https://t.me/s/quicknrapp",
            datetime(2026, 10, 12, 11, tzinfo=timezone.utc),
        )
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["url"], "https://t.me/quicknrapp/12345")
        self.assertEqual(items[0]["source"], "Quick N Rapp")
        self.assertTrue(items[0]["id"].startswith("tg"))
        self.assertEqual(items[0]["published_at"], "2026-10-12T10:30:00+00:00")
        self.assertIn("Скоро выходит альбом!", items[0]["summary"])


if __name__ == "__main__":
    unittest.main()
