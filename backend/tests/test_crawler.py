"""Crawler-Unit-Tests: URL-Dedupe (http/https + www./non-www.).

User-Vorgabe: Beim Crawlen zählt nur die Domain mit dem folgenden Pfad —
http/https und www./non-www. derselben Seite dürfen nicht doppelt gecrawlt
werden. Der dedupe_key() in app/engine/crawler.py ist die Identität.
"""
from __future__ import annotations

from app.engine.crawler import Crawler, dedupe_key


# ---------------------------------------------------------------- dedupe_key

def test_dedupe_key_ignoriert_scheme_und_www():
    assert dedupe_key("http://www.romy-schoenherr.de/datenschutz") == dedupe_key(
        "https://romy-schoenherr.de/datenschutz"
    )
    assert dedupe_key("https://WWW.example.de:8080/pfad/") == dedupe_key(
        "http://example.de:8080/pfad"
    )


def test_dedupe_key_root_und_slash_gleich():
    assert dedupe_key("http://example.de") == dedupe_key("https://www.example.de/")


def test_dedupe_key_ignoriert_query_und_fragment():
    assert dedupe_key("http://example.de/a?utm=x") == dedupe_key("https://example.de/a#anker")


def test_dedupe_key_unterscheidet_verschiedene_pfade():
    assert dedupe_key("http://example.de/a") != dedupe_key("https://example.de/b")


# ---------------------------------------------------------------- Crawler

def test_scheme_und_www_variante_nur_einmal_gequeued():
    crawler = Crawler("http://www.romy-schoenherr.de/")
    crawler.enqueue("https://www.romy-schoenherr.de/datenschutz")
    crawler.enqueue("http://romy-schoenherr.de/datenschutz")   # identische Seite
    crawler.enqueue("http://www.romy-schoenherr.de/impressum")
    crawler.enqueue("https://romy-schoenherr.de/impressum")    # identische Seite
    assert len(crawler.queue) == 3  # Start + datenschutz + impressum


def test_besuchte_variante_wird_nicht_erneut_gecrawlt():
    crawler = Crawler("http://www.romy-schoenherr.de/")
    first = crawler.next_url()
    crawler.mark_visited(first)
    # Start-URL als https/non-www erneut anbieten → muss ignoriert werden
    assert not crawler.should_enqueue("https://romy-schoenherr.de/")
    assert "https://romy-schoenherr.de/" not in crawler.queue
    assert crawler.next_url() is None
