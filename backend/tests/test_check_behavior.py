"""
Verhaltens-Fixtures für die am stärksten korrigierten Syntax-Checks.

Jeder Fix aus dem Review bekommt hier Positiv- UND Negativ-Befund:
Autoplay-Boolean-Attribut, dekorative Bilder (alt=""), Button-Namen
(AccName + verwaiste Referenz), Meta-Refresh-Ausnahmen, main-Dedupe.
Resolution-Checks (Playwright) liegen in test_resolution_behavior.py.
"""
from __future__ import annotations

from bs4 import BeautifulSoup

from app.engine.checks._base import CheckContext
from app.engine.checks.wcag_1_1_1_img_alt import check_img_alt
from app.engine.checks.wcag_1_3_1_landmark_main import check_landmark_main
from app.engine.checks.wcag_1_4_2_autoplay import check_autoplay
from app.engine.checks.wcag_2_2_1_meta_refresh import check_meta_refresh
from app.engine.checks.wcag_4_1_2_button_name import check_button_name


def _ctx(html: str) -> CheckContext:
    return CheckContext(
        url="https://example.com/",
        soup=BeautifulSoup(html, "html.parser"),
        test_id="WCAG_1_4_2_AUTOPLAY",
        w3c_enabled=False,
    )


# ----------------------------------------------------------------- 1.4.2 Autoplay

async def test_autoplay_video_without_muted_is_found():
    """Boolean-Attribut: <video autoplay> hat Wert '' — has_attr() muss greifen."""
    findings = await check_autoplay(_ctx('<video autoplay src="v.mp4"></video>'))
    assert len(findings) == 1
    assert findings[0].test_id == "WCAG_1_4_2_AUTOPLAY"


async def test_autoplay_muted_video_is_allowed():
    assert await check_autoplay(_ctx('<video autoplay muted src="v.mp4"></video>')) == []


async def test_video_without_autoplay_is_ok():
    assert await check_autoplay(_ctx('<video src="v.mp4"></video>')) == []


async def test_autoplay_audio_is_found():
    assert len(await check_autoplay(_ctx('<audio autoplay src="a.mp3"></audio>'))) == 1


# ---------------------------------------------------------------- 1.1.1 img alt

async def test_img_alt_missing_is_found():
    findings = await check_img_alt(_ctx('<img src="bild.jpg">'))
    assert len(findings) == 1
    assert findings[0].test_id == "WCAG_1_1_1_IMG_ALT"


async def test_img_alt_decorative_empty_alt_is_ok():
    """H67: alt="" ist ein gültiges Dekorativ-Marker — kein Befund."""
    assert await check_img_alt(_ctx('<img src="bild.jpg" alt="">')) == []


async def test_img_alt_filled_alt_is_ok():
    assert await check_img_alt(_ctx('<img src="bild.jpg" alt="Beschreibung">')) == []


async def test_img_alt_presentation_role_is_ok():
    assert await check_img_alt(_ctx('<img src="bild.jpg" role="presentation">')) == []
    assert await check_img_alt(_ctx('<img src="bild.jpg" role="none">')) == []


async def test_img_alt_same_url_deduplicated():
    """c=/w=/h=-Parameter werden normalisiert → nur ein Befund pro Bild-URL."""
    findings = await check_img_alt(
        _ctx('<img src="bild.jpg"><img src="bild.jpg?c=2&w=100">')
    )
    assert len(findings) == 1


# ------------------------------------------------------------ 4.1.2 button name

async def test_button_without_name_is_found():
    findings = await check_button_name(_ctx("<button></button>"))
    assert len(findings) == 1
    assert findings[0].test_id == "WCAG_4_1_2_BUTTON_NAME"


async def test_button_with_text_is_ok():
    assert await check_button_name(_ctx("<button>OK</button>")) == []


async def test_button_with_aria_label_is_ok():
    assert await check_button_name(_ctx('<button aria-label="Schließen"></button>')) == []


async def test_button_with_labelledby_reference_is_ok():
    html = '<button aria-labelledby="lbl"></button><span id="lbl">Name</span>'
    assert await check_button_name(_ctx(html)) == []


async def test_button_with_dangling_labelledby_is_found():
    """Verwaiste aria-labelledby-Referenz = kein Name (FN-Vermeidung)."""
    findings = await check_button_name(_ctx('<button aria-labelledby="missing"></button>'))
    assert len(findings) == 1


async def test_button_with_child_img_alt_is_ok():
    html = '<button><img src="x.jpg" alt="Schließen"></button>'
    assert await check_button_name(_ctx(html)) == []


# --------------------------------------------------------- 2.2.1 meta refresh

async def test_meta_refresh_seconds_is_found():
    findings = await check_meta_refresh(_ctx('<meta http-equiv="refresh" content="5">'))
    assert len(findings) == 1
    assert findings[0].test_id == "WCAG_2_2_1_META_REFRESH"


async def test_meta_refresh_immediate_redirect_is_allowed():
    """0;url=… ist ein Sofort-Redirect — keine Zeitbegrenzung."""
    html = '<meta http-equiv="refresh" content="0; url=https://example.com/">'
    assert await check_meta_refresh(_ctx(html)) == []


async def test_meta_refresh_over_20h_is_allowed():
    html = '<meta http-equiv="refresh" content="99999">'
    assert await check_meta_refresh(_ctx(html)) == []


async def test_meta_refresh_with_url_is_found():
    html = '<meta http-equiv="refresh" content="5; url=/weiter.html">'
    assert len(await check_meta_refresh(_ctx(html))) == 1


async def test_meta_refresh_unparseable_is_found():
    html = '<meta http-equiv="refresh" content="abc">'
    assert len(await check_meta_refresh(_ctx(html))) == 1


# --------------------------------------------------------- 1.3.1 main landmark

async def test_single_main_is_ok():
    assert await check_landmark_main(_ctx("<main></main>")) == []


async def test_main_with_role_main_deduped():
    """<main role="main"> ist EIN Element — find_all(role) + find_all(main) 1× zählen."""
    assert await check_landmark_main(_ctx('<main role="main"></main>')) == []


async def test_two_mains_is_found():
    findings = await check_landmark_main(_ctx("<main></main><main></main>"))
    assert len(findings) == 1
    assert findings[0].test_id == "WCAG_1_3_1_LANDMARK_MAIN"


async def test_hidden_main_not_counted():
    """display:none-Main ist nicht sichtbar → genau ein sichtbares Landmark."""
    html = '<main style="display:none"></main><main></main>'
    assert await check_landmark_main(_ctx(html)) == []
