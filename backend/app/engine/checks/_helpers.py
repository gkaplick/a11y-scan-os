"""
Geteilte Bausteine der Check-Dateien (eine Datei je Test, flach).

Einmal definiert statt in 60 Dateien dupliziert — die Einzel-Checks importieren
aus ``_helpers``: Farb-/Kontrast-Kern, W3C-Lauf, Überschriften-Sammlung,
JS-DOM-Pfad-Builder, Medien-Selektion, Label-/Namen-Helfer, HTTP-Client mit
htaccess-Auth und der vereinheitlichte Fokus-Selektor.

Konvention: Namen ohne führenden Unterstrich sind bewusst öffentlich
(importiert von den Check-Dateien), Namen mit Unterstrich bleiben intern.
"""
from __future__ import annotations

import asyncio
import hashlib
import re
import weakref
from urllib.parse import urljoin

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

__all__ = [
    # Farb-/Kontrast-Kern
    "CSS_NAMED_COLORS", "parse_color", "rel_lum", "contrast", "_clamp",
    "_is_large_text", "_GET_EFFECTIVE_COLORS_JS", "_TEXT_ELEMENTS_SELECTOR",
    "_deepest_text_elements", "_NON_TEXT_SELECTOR", "_NON_TEXT_CONTRAST_BATCH_JS",
    "_non_text_contrast_batch", "_COLOR_ONLY_SELECTOR", "_COLOR_ONLY_BATCH_JS",
    "_color_only_links_batch",
    # W3C-Lauf
    "_call_validator", "_run_w3c", "_dom_path_at_position", "_findings_for",
    # Überschriften
    "_HEADINGS", "_collect_headings",
    # JS-DOM-Pfad
    "DOM_PATH_JS",
    # Medien
    "_media_elements", "_media_has_ad", "_media_has_transcript",
    "_media_has_captions", "_media_ist_design_element", "_media_ist_live_stream",
    # Konsistente Navigation / Bezeichnung (seitenübergreifend)
    "_link_signatur", "_nav_signatur", "_signaturen_gleich", "_nav_diff_beschreibung",
    "_norm_link_text", "_konsistente_bezeichnung_befunde",
    # Labels / Namen
    "resolve_idrefs", "resolve_accessible_name", "has_accessible_name",
    "element_label", "visible_label",
    # HTTP
    "fetch_url", "abs_url",
    # Fokus-Selektor + Fokus-Messung (Batch)
    "_FOCUSABLE_SELECTOR", "_IS_VISIBLE_REPLICA_JS", "_FOCUS_CHUNK_SIZE",
    "_STYLE_JS", "_outline_visible", "_style_changed",
    "_FOCUS_ACC_PRE_JS", "_FOCUS_INDICATOR_BATCH_JS", "_FOCUS_MEASURE_CHUNK_JS",
    "_HIDDEN_SKIP_JS", "_HIDDEN_FOCUSABLE_BATCH_JS", "_HIDDEN_FOCUS_CHUNK_JS",
    "_TRAP_COLLECT_JS", "_TRAP_STEP_JS", "_CLEANUP_JS",
]

# --------------------------------------------------------------------------
# 1. Farb-/Kontrast-Kern (RGBA)
# --------------------------------------------------------------------------

CSS_NAMED_COLORS = {
    "black": (0, 0, 0), "white": (255, 255, 255), "red": (255, 0, 0), "green": (0, 128, 0),
    "blue": (0, 0, 255), "yellow": (255, 255, 0), "cyan": (0, 255, 255), "magenta": (255, 0, 255),
    "silver": (192, 192, 192), "gray": (128, 128, 128), "maroon": (128, 0, 0), "olive": (128, 128, 0),
    "lime": (0, 255, 0), "aqua": (0, 255, 255), "teal": (0, 128, 128), "navy": (0, 0, 128),
    "fuchsia": (255, 0, 255), "purple": (128, 0, 128),
}


def _clamp(v: float) -> int:
    return max(0, min(int(v), 255))


def parse_color(c: str):
    """Liefert (r,g,b,a), r,g,b 0–255, a 0–1; unbekannte Formate ⇒ None."""
    if not c or c.lower() in ("transparent", "none"):
        return None
    c = c.strip().lower()

    m = re.match(r"rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:[\/,\s]+([\d.]+))?\s*\)", c)
    if m:
        r, g, b = (float(x) for x in m.group(1, 2, 3))
        a = float(m.group(4)) if m.group(4) else 1
        return (_clamp(r), _clamp(g), _clamp(b), max(0, min(a, 1)))

    m = re.match(r"hsla?\(\s*([\d.]+)[,\s]+([\d.]+)%[,\s]+([\d.]+)%(?:[\/,\s]+([\d.]+))?\s*\)", c)
    if m:
        h, s, light = (float(x) for x in m.group(1, 2, 3))
        a = float(m.group(4)) if m.group(4) else 1
        s /= 100
        light /= 100
        k = lambda n: (n + h / 30) % 12  # noqa: E731
        f = lambda n: light - s * min(light, 1 - light) * max(-1, min(min(k(n) - 3, 9 - k(n)), 1))  # noqa: E731
        r, g, b = (_clamp(x * 255) for x in (f(0), f(8), f(4)))
        return (r, g, b, a)

    m = re.match(r"#([0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})$", c)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(ch * 2 for ch in h)
        if len(h) == 6:
            h += "ff"
        r, g, b, a = (int(h[i:i + 2], 16) for i in range(0, 8, 2))
        return (r, g, b, a / 255)

    if c in CSS_NAMED_COLORS:
        r, g, b = CSS_NAMED_COLORS[c]
        return (r, g, b, 1)

    return None


def rel_lum(rgb) -> float:
    """Relative Luminanz nach W3C."""
    r, g, b = (x / 255 for x in rgb[:3])
    conv = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4  # noqa: E731
    r, g, b = map(conv, (r, g, b))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(c1, c2) -> float:
    """Kontrastverhältnis zwischen zwei Farben nach WCAG."""
    l1, l2 = rel_lum(c1), rel_lum(c2)
    if l1 < l2:
        l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)


def _is_large_text(font_size: int, is_bold: bool) -> bool:
    """Großer Text nach WCAG: >= 18pt (24px) bzw. >= 14pt fett (18,66px)."""
    return (is_bold and font_size >= 18.66) or font_size >= 24


# Holt Vorder-/Hintergrundfarbe eines Elements inkl. Gradient-Analyse.
# Tokens, die keine Farben sind (linear/to/right/…), werden per Canvas-Probe
# herausgefiltert — sie würden sonst als transparent→Schwarz gemustert und
# Massen-False-Positives erzeugen.
_GET_EFFECTIVE_COLORS_JS = """
(element) => {
    const parseColor = (colorStr) => {
        const canvas = document.createElement('canvas');
        canvas.width = 1; canvas.height = 1;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = colorStr;
        ctx.fillRect(0, 0, 1, 1);
        const data = ctx.getImageData(0, 0, 1, 1).data;
        return { r: data[0], g: data[1], b: data[2], a: data[3] / 255 };
    };
    const blendColors = (fg, bg) => {
        const alpha = fg.a + bg.a * (1 - fg.a);
        if (alpha === 0) return { r: 255, g: 255, b: 255, a: 1 };
        return {
            r: Math.round((fg.r * fg.a + bg.r * bg.a * (1 - fg.a)) / alpha),
            g: Math.round((fg.g * fg.a + bg.g * bg.a * (1 - fg.a)) / alpha),
            b: Math.round((fg.b * fg.a + bg.b * bg.a * (1 - fg.a)) / alpha),
            a: alpha
        };
    };
    const isValidColorToken = (token) => {
        if (/^#[0-9a-fA-F]{3,8}$/.test(token)) return true;
        if (/^(rgb|hsl)a?\\(/.test(token)) return true;
        // String-Vergleich statt Pixel-Probe: der Default-fillStyle ist Schwarz,
        // ein ungültiges Token würde also immer schwarz füllen und als gültig
        // gelten. Ungültige Tokens bleiben dagegen auf dem Sentinel stehen.
        const ctx = document.createElement('canvas').getContext('2d');
        ctx.fillStyle = '#000000';
        ctx.fillStyle = token;
        return ctx.fillStyle !== '#000000';
    };
    const extractGradientColors = (gradientString) => {
        const colors = [];
        const colorRegex = /(rgba?\\([^)]+\\)|hsla?\\([^)]+\\)|#[0-9a-fA-F]{3,8}|[a-z]+)/g;
        let match;
        while ((match = colorRegex.exec(gradientString)) !== null) {
            const token = match[1];
            if (isValidColorToken(token)) colors.push(token);
        }
        return colors;
    };
    const getEffectiveBackgroundColor = (el) => {
        const backgrounds = [];
        let current = el;
        while (current) {
            const style = window.getComputedStyle(current);
            const bgColor = style.backgroundColor;
            if (bgColor && bgColor !== 'rgba(0, 0, 0, 0)' && bgColor !== 'transparent') {
                const parsed = parseColor(bgColor);
                backgrounds.push(parsed);
                if (parsed.a === 1) break;
            }
            const bgImage = style.backgroundImage;
            if (bgImage && bgImage !== 'none' && bgImage.includes('gradient')) {
                const gradientColors = extractGradientColors(bgImage);
                if (gradientColors.length > 0) {
                    return { isGradient: true, colors: gradientColors, original: bgImage };
                }
            }
            if (current.tagName.toLowerCase() === 'html') break;
            current = current.parentElement;
        }
        if (backgrounds.length === 0) backgrounds.push({ r: 255, g: 255, b: 255, a: 1 });
        let effectiveBg = { r: 255, g: 255, b: 255, a: 1 };
        for (let i = backgrounds.length - 1; i >= 0; i--) {
            effectiveBg = blendColors(backgrounds[i], effectiveBg);
        }
        return { isGradient: false, color: `rgb(${effectiveBg.r}, ${effectiveBg.g}, ${effectiveBg.b})`,
                 rgba: effectiveBg };
    };
    const getLuminance = (rgb) => {
        const [r, g, b] = [rgb.r / 255, rgb.g / 255, rgb.b / 255];
        const srgb = [r, g, b].map(c => c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
        return 0.2126 * srgb[0] + 0.7152 * srgb[1] + 0.0722 * srgb[2];
    };
    const style = window.getComputedStyle(element);
    // -webkit-text-fill-color übersteuert color für den gerenderten Text;
    // ungesetzt liefert es denselben Wert wie color.
    const fillColor = style.webkitTextFillColor;
    const foregroundColor = parseColor(fillColor && fillColor !== 'currentcolor' ? fillColor : style.color);
    // Element-Transparenz (opacity) zusätzlich in die effektive Vordergrundfarbe einblenden.
    const opacity = parseFloat(style.opacity);
    if (!isNaN(opacity) && opacity !== 1) foregroundColor.a *= opacity;
    const backgroundData = getEffectiveBackgroundColor(element);
    let effectiveForeground = foregroundColor;
    if (foregroundColor.a < 1 && backgroundData.rgba) {
        effectiveForeground = blendColors(foregroundColor, backgroundData.rgba);
    }
    const fontSize = parseInt(style.fontSize, 10);
    const isBold = parseInt(style.fontWeight, 10) >= 700;
    let contrastResults = null;
    if (backgroundData.isGradient && backgroundData.colors.length > 0) {
        const ratios = backgroundData.colors.map(bgColor => {
            try {
                const bg = parseColor(bgColor);
                const effectiveBg = blendColors(bg, { r: 255, g: 255, b: 255, a: 1 });
                const effectiveFg = blendColors(foregroundColor, effectiveBg);
                const lumFg = getLuminance(effectiveFg);
                const lumBg = getLuminance(effectiveBg);
                const ratio = (Math.max(lumFg, lumBg) + 0.05) / (Math.min(lumFg, lumBg) + 0.05);
                return { color: bgColor, ratio: ratio };
            } catch (e) {
                return { color: bgColor, ratio: 1.0 };
            }
        });
        contrastResults = {
            isGradient: true, ratios: ratios,
            worstRatio: Math.min(...ratios.map(r => r.ratio)),
            bestRatio: Math.max(...ratios.map(r => r.ratio))
        };
    }
    return {
        foreground: `rgb(${effectiveForeground.r}, ${effectiveForeground.g}, ${effectiveForeground.b})`,
        background: backgroundData.isGradient ? backgroundData.original : backgroundData.color,
        fontSize: fontSize, isBold: isBold, contrastResults: contrastResults
    };
}
"""

_TEXT_ELEMENTS_SELECTOR = (
    "p, a, span, li, h1, h2, h3, h4, h5, h6, button, strong, em, b, i, td, th, label, "
    "div, section, article, aside, header, footer, nav, main"
)


# Die tiefsten Text-Elemente (inkl. Effektiv-Farben) werden gebatcht in EINEM
# page.evaluate() extrahiert — Definition siehe Abschnitt "JS-DOM-Pfad" (nach
# DOM_PATH_JS), weil die Batch-JS DOM_PATH_JS einbettet.


# --------------------------------------------------------------------------
# 2. W3C-HTML-Validierung (4.1.1)
# --------------------------------------------------------------------------

_PARSING_ERROR_PATTERNS = (
    re.compile(r"duplicate id", re.I),
    re.compile(r"duplicate attribute|attribute .+ duplicated", re.I),
    re.compile(r"stray end tag|unexpected end tag", re.I),
    re.compile(r"end tag .+ seen, but there were open elements", re.I),
    re.compile(r"end tag for .+ which is not open", re.I),
    re.compile(r"start tag .+ seen", re.I),
    re.compile(r"mismatched tag", re.I),
    re.compile(r"violates nesting rules|nesting", re.I),
    re.compile(r"unclosed element|no .+ in scope but a .+ end tag seen", re.I),
)


def _is_parsing_relevant(message: str) -> bool:
    """4.1.1-Filter: nur doppelte IDs/Attribute und fehlerhafte Tag-Struktur.

    Sonstige Validator-Meldungen (unbekannte Attribute, obsolete Elemente …)
    gehören zu anderen Kriterien und würden 4.1.1 mit Fremd-Befunden überfrachten.
    """
    return any(pattern.search(message) for pattern in _PARSING_ERROR_PATTERNS)


def _call_validator(
    html_content: str,
    *,
    validator_url: str,
    htaccess_user: str | None = None,
    htaccess_pw: str | None = None,
    timeout: int = 10,
) -> tuple[list, list]:
    """POST des HTML an validator.w3.org/nu; liefert (errors, warnings)."""
    import requests

    session = requests.Session()
    session.verify = False
    if htaccess_user and htaccess_pw:
        session.auth = (htaccess_user, htaccess_pw)
    headers = {
        "Content-Type": "text/html; charset=utf-8",
        "User-Agent": "a11y-scanner/1.0 (HTML validation check)",
    }
    response = session.post(
        validator_url,
        data=html_content.encode("utf-8"),
        headers=headers,
        timeout=timeout,
    )
    errors, warnings = [], []
    if response.status_code != 200:
        return errors, warnings
    messages = response.json().get("messages", [])
    for message in messages:
        msg_type = message.get("type", "")
        if msg_type != "error" and not (msg_type == "info" and message.get("subType") == "warning"):
            continue
        text = message.get("message", "")
        if not _is_parsing_relevant(text):
            continue
        entry = {
            "message": text,
            "line": message.get("lastLine"),
            "col": message.get("lastColumn"),
        }
        if msg_type == "error":
            errors.append(entry)
        else:
            warnings.append(entry)
    return errors, warnings


# Cache: die beiden W3C-Checks (Fehler + Warnungen) laufen separat und würden
# den langsamen Validator sonst doppelt pro Seite aufrufen. Key = Inhalts-Hash,
# damit identischer Inhalt gecacht wird, ohne dass sich Seiten/Jobs gegenseitig
# beeinflussen. Bounded, damit der Prozess über viele Jobs hinweg nicht
# unendlich wächst.
_w3c_cache: dict[str, tuple[str, list, list]] = {}
_W3C_CACHE_MAX = 500


async def _run_w3c(ctx: CheckContext) -> tuple[str, list, list]:
    """Liefert (html_str, errors, warnings) — leere Listen wenn deaktiviert/Fehler."""
    if not ctx.w3c_enabled:
        return "", [], []
    # str(soup) (statt prettify): der Validator bekommt genau die Serialisierung,
    # die wir für die Zeilen→Element-Zuordnung verwenden — str(el) ist dann immer
    # ein (Teil-)Substring und die gemeldeten lastLine-Werte passen exakt.
    # Hinweis: ungeschlossene Tags repariert bereits der HTML-Parser — dieser Teil
    # von 4.1.1 bleibt damit pragmatisch unterdetektiert (bekannte Grenze).
    html_str = str(ctx.soup)
    cache_key = hashlib.sha256(html_str.encode("utf-8")).hexdigest()
    cached = _w3c_cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        errors, warnings = await asyncio.to_thread(
            _call_validator,
            html_str,
            validator_url=ctx.w3c_validator_url,
            htaccess_user=ctx.htaccess_user,
            htaccess_pw=ctx.htaccess_pw,
        )
        result = (html_str, errors, warnings)
        if len(_w3c_cache) >= _W3C_CACHE_MAX:
            _w3c_cache.clear()
        _w3c_cache[cache_key] = result
        return result
    except Exception:
        return "", [], []


def _dom_path_at_position(soup, html_str: str, line) -> str:
    """DOM-Pfad des kleinsten Elements, dessen Bereich die Zeile enthält.

    Der W3C-Validator liefert lastLine im POST-Output (= str(soup)). Wir suchen
    das tiefste Element, dessen Serialisierung diese Zeile überdeckt (Heuristik:
    bei identischen Wiederholungen wird die erste passende Instanz gewählt).
    """
    import bisect

    if not line or not html_str:
        return ""
    line_starts = [i for i, ch in enumerate(html_str) if ch == "\n"]
    if line < 1 or line > len(line_starts) + 1:
        return ""

    def line_of(offset: int) -> int:
        return bisect.bisect_left(line_starts, offset) + 1

    best = None
    best_size = 0
    for el in soup.descendants:
        if not getattr(el, "name", None):
            continue
        el_str = str(el)
        if not el_str:
            continue
        size = len(el_str)
        if best is not None and size >= best_size:
            continue
        start = html_str.find(el_str)
        if start == -1:
            continue
        start_line = line_of(start)
        end_line = line_of(start + size)
        if start_line <= line <= end_line:
            best = el
            best_size = size
    return get_dom_path(best) if best is not None else ""


def _findings_for(entries: list[dict], soup, html_str: str, test_id: str) -> list:
    rows = []
    for entry in entries:
        dom_path = _dom_path_at_position(soup, html_str, entry.get("line"))
        line, col = entry.get("line"), entry.get("col")
        location = f"Zeile {line}, Spalte {col}" if line and col else "html"
        rows.append(
            finding(
                test_id,
                entry["message"],
                dom_path=dom_path,
                detail=f"W3C-Position: {location}",
            )
        )
    return rows


# --------------------------------------------------------------------------
# 3. Überschriften-Sammlung (1.3.1 / 2.4.6)
# --------------------------------------------------------------------------

_HEADINGS = ["h1", "h2", "h3", "h4", "h5", "h6"]


def _collect_headings(ctx: CheckContext) -> list:
    return [h for h in ctx.soup.find_all(_HEADINGS) if is_accessible_element(h)]


# --------------------------------------------------------------------------
# 4. JS-DOM-Pfad (ein Builder für alle Live-Checks)
# --------------------------------------------------------------------------

DOM_PATH_JS = """(e) => {
    const p = [];
    while (e && e.nodeType === 1 && e !== document.body) {
        let t = e.nodeName.toLowerCase();
        if (e.id) {
            t += '#' + e.id;
        } else {
            if (e.className) t += '.' + e.className.trim().split(/\\s+/)[0];
            // Geschwister gleichen Tag-Namens? → Index ergänzen, damit der Pfad
            // das Element eindeutig adressiert (Screenshot-Locator). nth-of-type
            // zählt über alle Geschwister des Tags, unabhängig von Klasse/Index.
            if (e.parentElement) {
                const sibs = Array.from(e.parentElement.children)
                    .filter(s => s.nodeName === e.nodeName);
                if (sibs.length > 1) {
                    t += ':nth-of-type(' + (sibs.indexOf(e) + 1) + ')';
                }
            }
        }
        p.unshift(t);
        e = e.parentElement;
    }
    p.unshift('body');
    return p.join(' > ');
}"""


# --------------------------------------------------------------------------
# 4b. Text-Kontrast-Batch (geteilt von BITV 9.1.4.3 / WCAG 1.4.3 / 1.4.6)
# --------------------------------------------------------------------------
# EIN page.evaluate-Aufruf je Seite statt vieler Playwright-Round-Trips
# (query_selector_all → is_visible → inner_text → has-direct-text → DOM-Pfad
# → _GET_EFFECTIVE_COLORS_JS → erneut inner_text).
# Die Farb-Logik ist exakt _GET_EFFECTIVE_COLORS_JS (per Konkatenation
# eingebettet); is_visible repliziert Playwrights is_visible (verbunden +
# visibility != hidden + nicht-leere Bounding-Box). Das Ergebnis wird je
# (page, resolution, url) gecacht, damit die drei Kontrast-Checks dieselbe
# Extraktion teilen.
_TEXT_KONTRAST_BATCH_JS = (
    "() => {\n"
    "    const domPath = " + DOM_PATH_JS + ";\n"
    "    const computeColors = " + _GET_EFFECTIVE_COLORS_JS + ";\n"
    "    const isVisible = (el) => {\n"
    "        if (!el.isConnected) return false;\n"
    "        const cs = window.getComputedStyle(el);\n"
    "        if (cs.visibility === 'hidden') return false;\n"
    "        const r = el.getBoundingClientRect();\n"
    "        return r.width !== 0 && r.height !== 0;\n"
    "    };\n"
    "    const out = [];\n"
    "    for (const el of document.querySelectorAll('" + _TEXT_ELEMENTS_SELECTOR + "')) {\n"
    "        try {\n"
    "            if (!isVisible(el)) continue;\n"
    "            const text = el.innerText || '';\n"
    "            if (!text.trim()) continue;\n"
    "            const hasDirectText = Array.from(el.childNodes).some(\n"
    "                n => n.nodeType === 3 && n.textContent.trim().length > 0\n"
    "            );\n"
    "            const colors = computeColors(el);\n"
    "            out.push({\n"
    "                path: domPath(el),\n"
    "                text,\n"
    "                hasDirectText,\n"
    "                fontSize: colors.fontSize,\n"
    "                isBold: colors.isBold,\n"
    "                foreground: colors.foreground,\n"
    "                background: colors.background,\n"
    "                contrastResults: colors.contrastResults,\n"
    "            });\n"
    "        } catch (e) {}\n"
    "    }\n"
    "    return out;\n"
    "}"
)

# Cache je Seite (WeakKeyDictionary → verschwindet mit der Seite): der Runner
# nutzt EINE Playwright-Seite für alle URLs, deshalb ist der Schlüssel
# (resolution, url). Die drei Kontrast-Checks teilen sich so pro Seite eine
# einzige Extraktion.
_kontrast_batch_cache: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


async def _deepest_text_elements(page, resolution=None, url=""):
    """Tiefste sichtbare Text-Elemente mit Effektiv-Farben (EIN page.evaluate).

    Liefert pro Element ein Dict mit path/text/fontSize/isBold/foreground/
    background/contrastResults. Der Tiefste-Filter: eigener Textknoten ODER
    kein Text-Deszendent mit Pfad-Präfix; die Extraktion ist gebatcht.
    """
    cache = _kontrast_batch_cache.get(page)
    if cache is None:
        cache = {}
        _kontrast_batch_cache[page] = cache
    key = (resolution, url)
    if key in cache:
        return cache[key]

    data = await page.evaluate(_TEXT_KONTRAST_BATCH_JS)
    rows = []
    for item in data:
        path = item["path"]
        has_direct = item["hasDirectText"]
        has_text_descendant = any(
            other["path"] != path and other["path"].startswith(path + " > ")
            for other in data
        )
        if has_direct or not has_text_descendant:
            rows.append(item)
    # Cache begrenzt halten (Seite lebt über viele URLs im Runner).
    if len(cache) >= 200:
        cache.clear()
    cache[key] = rows
    return rows


# --------------------------------------------------------------------------
# 4c. Rahmen-Kontrast-Batch (geteilt von BITV 9.1.4.11 / WCAG 1.4.11)
# --------------------------------------------------------------------------
# Ein page.evaluate() (query_selector_all + _BORDER_CONTRAST_JS + DOM_PATH_JS
# gebatcht); die Logik ist per Konkatenation eingebettet. Nur gerahmte
# Elemente werden zurückgegeben.
_NON_TEXT_SELECTOR = "input:not([type=hidden]), select, textarea, button"

_NON_TEXT_CONTRAST_BATCH_JS = (
    "() => {\n"
    "    const domPath = " + DOM_PATH_JS + ";\n"
    "    const canvas = document.createElement('canvas');\n"
    "    canvas.width = 1; canvas.height = 1;\n"
    "    const ctx = canvas.getContext('2d');\n"
    "    const parseColor = (colorStr) => {\n"
    "        ctx.fillStyle = colorStr;\n"
    "        ctx.fillRect(0, 0, 1, 1);\n"
    "        const d = ctx.getImageData(0, 0, 1, 1).data;\n"
    "        return { r: d[0], g: d[1], b: d[2], a: d[3] / 255 };\n"
    "    };\n"
    "    const blend = (fg, bg) => {\n"
    "        const alpha = fg.a + bg.a * (1 - fg.a);\n"
    "        if (alpha === 0) return { r: 255, g: 255, b: 255, a: 1 };\n"
    "        return {\n"
    "            r: Math.round((fg.r * fg.a + bg.r * bg.a * (1 - fg.a)) / alpha),\n"
    "            g: Math.round((fg.g * fg.a + bg.g * bg.a * (1 - fg.a)) / alpha),\n"
    "            b: Math.round((fg.b * fg.a + bg.b * bg.a * (1 - fg.a)) / alpha),\n"
    "            a: alpha,\n"
    "        };\n"
    "    };\n"
    "    const out = [];\n"
    "    for (const el of document.querySelectorAll('" + _NON_TEXT_SELECTOR + "')) {\n"
    "        try {\n"
    "            const cs = window.getComputedStyle(el);\n"
    "            const sides = ['Top', 'Right', 'Bottom', 'Left'];\n"
    "            let maxW = 0;\n"
    "            let color = null;\n"
    "            for (const s of sides) {\n"
    "                const w = parseFloat(cs['border' + s + 'Width']);\n"
    "                const st = cs['border' + s + 'Style'];\n"
    "                if (w > 0 && st && st !== 'none' && w >= maxW) {\n"
    "                    maxW = w;\n"
    "                    color = cs['border' + s + 'Color'];\n"
    "                }\n"
    "            }\n"
    "            if (!color) continue;\n"
    "            let bg = { r: 255, g: 255, b: 255, a: 1 };\n"
    "            let cur = el;\n"
    "            const root = document.documentElement;\n"
    "            while (cur) {\n"
    "                const c = window.getComputedStyle(cur).backgroundColor;\n"
    "                if (c && c !== 'transparent' && c !== 'rgba(0, 0, 0, 0)') {\n"
    "                    bg = blend(parseColor(c), bg);\n"
    "                    break;\n"
    "                }\n"
    "                if (cur === root) break;\n"
    "                cur = cur.parentElement;\n"
    "            }\n"
    "            const border = blend(parseColor(color), bg);\n"
    "            out.push({\n"
    "                path: domPath(el),\n"
    "                border: [border.r, border.g, border.b],\n"
    "                background: [bg.r, bg.g, bg.b],\n"
    "                width: maxW,\n"
    "            });\n"
    "        } catch (e) {}\n"
    "    }\n"
    "    return out;\n"
    "}"
)


async def _non_text_contrast_batch(page):
    """Gerahmte Bedienelemente mit Rahmen-/Hintergrundfarbe (EIN evaluate)."""
    return await page.evaluate(_NON_TEXT_CONTRAST_BATCH_JS)


# --------------------------------------------------------------------------
# 4d. Farb-Codierung-Batch (geteilt von WCAG 1.4.1 / BITV 9.1.4.1)
# --------------------------------------------------------------------------
# Ein page.evaluate() statt query_selector_all + is_visible + _STYLE_JS je
# Link + inner_text/DOM_PATH_JS je Befund. is_visible repliziert Playwright
# (verbunden + visibility != hidden + nicht-leere Bounding-Box).
_IS_VISIBLE_REPLICA_JS = (
    "const isVisible = (el) => {\n"
    "    if (!el.isConnected) return false;\n"
    "    const cs = window.getComputedStyle(el);\n"
    "    if (cs.visibility === 'hidden') return false;\n"
    "    const r = el.getBoundingClientRect();\n"
    "    return r.width !== 0 && r.height !== 0;\n"
    "};\n"
)

_COLOR_ONLY_SELECTOR = (
    "p a, div a, span a, td a, li a, nav a, main a, header a, footer a, "
    "article a, section a, aside a, blockquote a, h1 a, h2 a, h3 a, h4 a, h5 a, h6 a"
)

_COLOR_ONLY_BATCH_JS = (
    "() => {\n"
    "    const domPath = " + DOM_PATH_JS + ";\n"
    "    " + _IS_VISIBLE_REPLICA_JS + "\n"
    "    // Permanent integriertes Symbol: eingebettetes SVG/Bild/Icon-Element,\n"
    "    // Pfeil-Zeichen im Text oder CSS-Pseudo-Content (Icon-Fonts).\n"
    "    const ICON_RE = /[\\u2190-\\u21ff\\u27a1\\u2b05-\\u2b07\\u2794\\u279c-\\u27bf]/u;\n"
    "    const hatIcon = (el) => {\n"
    "        if (el.querySelector('svg, img, [class*=\"icon\"], [class*=\"material-icons\"], "
    "[class*=\"glyphicon\"], i[class*=\"fa-\"], span[class*=\"fa-\"]')) return true;\n"
    "        if (ICON_RE.test(el.innerText || '')) return true;\n"
    "        for (const pseudo of ['::before', '::after']) {\n"
    "            const v = getComputedStyle(el, pseudo).content;\n"
    "            if (v && v !== 'none' && v !== 'normal' && v.replace(/[\"']/g, '').trim() !== '') return true;\n"
    "        }\n"
    "        return false;\n"
    "    };\n"
    "    const out = [];\n"
    "    for (const el of document.querySelectorAll('" + _COLOR_ONLY_SELECTOR + "')) {\n"
    "        try {\n"
    "            if (!isVisible(el)) continue;\n"
    "            const cs = window.getComputedStyle(el);\n"
    "            const parent = el.parentElement;\n"
    "            const parentStyle = parent ? window.getComputedStyle(parent) : null;\n"
    "            out.push({\n"
    "                path: domPath(el),\n"
    "                text: el.innerText || '',\n"
    "                color: cs.color,\n"
    "                parentColor: parentStyle ? parentStyle.color : null,\n"
    "                parentFontWeight: parentStyle ? parentStyle.fontWeight : null,\n"
    "                hasUnderline: cs.textDecoration.includes('underline'),\n"
    "                hasBorder: cs.borderWidth !== '0px' || cs.borderBottomWidth !== '0px',\n"
    "                hasBackground: cs.backgroundColor !== 'rgba(0, 0, 0, 0)' "
    "&& cs.backgroundColor !== 'transparent',\n"
    "                fontStyle: cs.fontStyle,\n"
    "                fontWeight: cs.fontWeight,\n"
    "                hasIcon: hatIcon(el),\n"
    "            });\n"
    "        } catch (e) {}\n"
    "    }\n"
    "    return out;\n"
    "}"
)


async def _color_only_links_batch(page):
    """Sichtbare Links mit Farb-/Stil-Merkmalen (EIN evaluate)."""
    return await page.evaluate(_COLOR_ONLY_BATCH_JS)


def _hat_dauerhaftes_nicht_farb_merkmal(link: dict) -> bool:
    """Dauerhaftes Nicht-Farb-Merkmal nach 1.4.1/G182/G183?

    Unterstreichung, Rahmen, eigener Hintergrund (Marker), abweichender
    Font-Style, Fettung ab halbfett (≥ 600, relativ zum Fließtext) oder ein
    fest integriertes Symbol. Trägt der Link eines davon, ist er bereits im
    Initialzustand über die Farbe hinaus erkennbar — kein 1.4.1-Befund.
    """
    if link["hasUnderline"] or link["hasBorder"] or link["hasBackground"] or link["hasIcon"]:
        return True
    if link["fontStyle"] != "normal":
        return True
    try:
        fw = int(link["fontWeight"])
        pfw = int(link.get("parentFontWeight") or 400)
        if fw >= 600 and fw > pfw:
            return True
    except (TypeError, ValueError):
        pass
    return False


async def _hat_hover_fokus_unterstreichung(page, dom_path: str) -> bool:
    """True, wenn beim Hover ODER Fokus eine Unterstreichung erscheint.

    BITV-/G183-Ausnahme: Ein Fließtext-Link mit ≥ 3:1 Kontrast zur umgebenden
    Textfarbe braucht im Initialzustand keine weitere Hervorhebung, muss aber
    bei Fokuserhalt zusätzlich hervorgehoben werden. Simuliert Hover und Fokus
    per Playwright und liest text-decoration-line bzw. border-bottom des Links.
    Best-effort: schlägt die Simulation fehl (Element off-canvas/verdeckt),
    gilt die Unterstreichung als nicht vorhanden.
    """
    async def _lese_zustand() -> dict:
        return await page.locator(dom_path).first.evaluate(
            "el => { const cs = getComputedStyle(el);"
            " return { deco: cs.textDecorationLine, border: cs.borderBottomWidth }; }"
        )

    def _ist_unterstrichen(state: dict) -> bool:
        deco = (state.get("deco") or "").lower()
        border = (state.get("border") or "0px").lower()
        return "underline" in deco or border not in ("0px", "0", "", "none")

    try:
        await page.locator(dom_path).first.hover()
        if _ist_unterstrichen(await _lese_zustand()):
            return True
        await page.locator(dom_path).first.focus()
        return _ist_unterstrichen(await _lese_zustand())
    except Exception:
        return False
    finally:
        try:
            await page.evaluate("() => { const a = document.activeElement; if (a) a.blur(); }")
            await page.mouse.move(0, 0)
        except Exception:
            pass


async def _color_only_befunde(ctx) -> list[dict]:
    """Links, die ausschließlich durch Farbe vom umgebenden Text unterscheidbar sind.

    Geteilt von WCAG_1_4_1_COLOR_ONLY und BITV_9_1_4_1_OHNE_FARBEN_NUTZBAR.
    Ein Link ist ausreichend gekennzeichnet, wenn er ein dauerhaftes
    Nicht-Farb-Merkmal trägt (s. ``_hat_dauerhaftes_nicht_farb_merkmal``) oder
    die G183-/BITV-Ausnahme greift: ≥ 3:1 Kontrast zur umgebenden Textfarbe
    UND Unterstreichung bei Hover/Fokus. Ein gar nicht farblich abgesetzter
    Link (gleiche Farbe wie Umgebung) ist kein 1.4.1-Fall — Farbe wird dann
    nicht als Information eingesetzt (bitvtest-Abgrenzung).
    """
    if ctx.page is None:
        return []
    links = await _color_only_links_batch(ctx.page)
    befund: list[dict] = []
    for link in links:
        if _hat_dauerhaftes_nicht_farb_merkmal(link):
            continue
        if not link.get("color") or not link.get("parentColor"):
            continue
        if link["color"] == link["parentColor"]:
            continue  # nicht farblich abgesetzt → kein "nur-Farbe"-Fall
        fg = parse_color(link["color"])
        bg = parse_color(link["parentColor"])
        if fg and bg and contrast(fg, bg) >= 3.0:
            # Ausnahme: ≥ 3:1 zur Umgebung UND zusätzliche Hervorhebung bei
            # Hover/Fokus — sonst bleibt der Link nur durch Farbe erkennbar.
            if await _hat_hover_fokus_unterstreichung(ctx.page, link["path"]):
                continue
        befund.append(link)
    return befund


# Fokus-Selektor (einheitlich; nur Desktop, > keyboard_min_width) — vor den
# Batch-JS-Schnipseln definiert, die ihn zur Importzeit einbetten.
_FOCUSABLE_SELECTOR = "a[href], button, input, select, textarea, [tabindex]:not([tabindex='-1'])"


# --------------------------------------------------------------------------
# 4e. Fokus-Messung (geteilt von WCAG 2.4.7 / BITV 9.2.4.7 / 2.1.2)
# --------------------------------------------------------------------------
# Die Fokus-Checks sind die teuersten Resolution-Checks (pro Element mehrere
# Playwright-Round-Trips + Wartepausen). Strategie: die Vor-Prüfungen in EINEM
# evaluate bündeln (liefert Kandidaten mit Index/Path), die Fokus-Messung —
# die je Element fokussieren UND warten MUSS — in gechunkten evaluates
# (_FOCUS_CHUNK_SIZE so gewählt, dass die Wartepausen je Chunk unter dem
# evaluate-Timeout bleiben). _STYLE_JS/_outline_visible/_style_changed waren
# in drei Check-Dateien identisch dupliziert und sind hier zentralisiert.
_FOCUS_CHUNK_SIZE = 40

_STYLE_JS = """(e) => {
    const cs = getComputedStyle(e);
    const csBefore = getComputedStyle(e, '::before');
    const csAfter = getComputedStyle(e, '::after');
    return {
        outlineStyle: cs.outlineStyle, outlineWidth: cs.outlineWidth, outlineColor: cs.outlineColor,
        boxShadow: cs.boxShadow, backgroundColor: cs.backgroundColor, color: cs.color,
        borderColor: cs.borderColor, borderWidth: cs.borderWidth, borderStyle: cs.borderStyle,
        beforeOutline: { style: csBefore.outlineStyle, width: csBefore.outlineWidth },
        afterOutline: { style: csAfter.outlineStyle, width: csAfter.outlineWidth }
    };
}"""


def _outline_visible(outline) -> bool:
    return outline["style"] not in ["none", ""] and outline["width"] not in ["0px", "0"]


def _style_changed(inactive, focused) -> bool:
    """Sichtbare Änderung zwischen inaktivem und fokussiertem Zustand?"""
    if inactive["outlineStyle"] != focused["outlineStyle"] or inactive["outlineWidth"] != focused["outlineWidth"]:
        if _outline_visible(focused) or "auto" in str(focused["outlineStyle"]).lower():
            return True
    # ::before/::after-Outline (Indikator-CSS-Muster)
    for key in ("beforeOutline", "afterOutline"):
        if inactive[key] != focused[key] and _outline_visible(focused[key]):
            return True
    # Box-Shadow
    if inactive["boxShadow"] != focused["boxShadow"] and focused["boxShadow"] not in ["none", ""]:
        return True
    # Hintergrund / Rahmen / Textfarbe
    if (inactive["backgroundColor"] != focused["backgroundColor"]
            or inactive["borderStyle"] != focused["borderStyle"]
            or inactive["borderWidth"] != focused["borderWidth"]
            or inactive["borderColor"] != focused["borderColor"]
            or inactive["color"] != focused["color"]):
        return True
    return False


# Vor-Prüfung des Fokus-Indikator-Checks (ohne Fokus-Test): der canFocus-Test
# wird in die gechunkte Messung integriert, die ohnehin fokussiert.
_FOCUS_ACC_PRE_JS = """(el) => {
    if (el.closest('#BorlabsCookieBox')) {
        return { accessible: false, reason: 'borlabs-cookie-box-exception' };
    }
    if (el.getAttribute('aria-hidden') === 'true' || el.closest('[aria-hidden="true"]') !== null) {
        return { accessible: false, reason: 'aria-hidden' };
    }
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) === 0) {
        return { accessible: false, reason: 'not-visible' };
    }
    if (el.disabled === true) {
        return { accessible: false, reason: 'disabled' };
    }
    if (el.tagName === 'INPUT' && el.readOnly === true) {
        return { accessible: false, reason: 'readonly' };
    }
    if (el.tabIndex < 0) {
        return { accessible: false, reason: 'negative-tabindex' };
    }
    if (el.hasAttribute('inert') || el.closest('[inert]')) {
        return { accessible: false, reason: 'inert' };
    }
    if (el.tagName === 'A' && !el.hasAttribute('href')) {
        return { accessible: false, reason: 'link-no-href' };
    }
    return { accessible: true };
}"""

_FOCUS_INDICATOR_BATCH_JS = (
    "() => {\n"
    "    const domPath = " + DOM_PATH_JS + ";\n"
    "    " + _IS_VISIBLE_REPLICA_JS + "\n"
    "    const pre = " + _FOCUS_ACC_PRE_JS + ";\n"
    "    const nodes = document.querySelectorAll(\"" + _FOCUSABLE_SELECTOR + "\");\n"
    "    const out = [];\n"
    "    for (let i = 0; i < nodes.length; i++) {\n"
    "        const el = nodes[i];\n"
    "        try {\n"
    "            const check = pre(el);\n"
    "            if (!check.accessible) continue;\n"
    "            if (!isVisible(el)) continue;\n"
    "            const tag = el.tagName.toLowerCase();\n"
    "            out.push({\n"
    "                index: i,\n"
    "                path: domPath(el),\n"
    "                node: tag,\n"
    "                id: el.id || '',\n"
    "                isFormField: tag === 'input' || tag === 'select' || tag === 'textarea',\n"
    "            });\n"
    "        } catch (e) {}\n"
    "    }\n"
    "    return out;\n"
    "}"
)

# Gechunkte Messung: inaktive Styles → focus({focusVisible:true}) → canFocus →
# 200 ms → fokussierte Styles → blur → 50 ms. Labels werden für Formularfelder
# wie im Original über label[for] + closest('label') ergänzt.
_FOCUS_MEASURE_CHUNK_JS = (
    "async (candidates) => {\n"
    "    const nodes = document.querySelectorAll(\"" + _FOCUSABLE_SELECTOR + "\");\n"
    "    const sleep = (ms) => new Promise(r => setTimeout(r, ms));\n"
    "    const style = " + _STYLE_JS + ";\n"
    "    const out = [];\n"
    "    for (const c of candidates) {\n"
    "        const el = nodes[c.index];\n"
    "        if (!el) continue;\n"
    "        try {\n"
    "            const labelEls = (c.isFormField && c.id) ?\n"
    "                Array.from(document.querySelectorAll('label[for=\"' + CSS.escape(c.id) + '\"]')) : [];\n"
    "            const parentLabel = el.closest('label');\n"
    "            const elementsToTest = [el].concat(labelEls, parentLabel ? [parentLabel] : []);\n"
    "            const inactive = elementsToTest.map(style);\n"
    "            el.focus({ focusVisible: true });\n"
    "            if (document.activeElement !== el) continue;\n"
    "            await sleep(200);\n"
    "            const focused = elementsToTest.map(style);\n"
    "            out.push({ index: c.index, inactive: inactive, focused: focused });\n"
    "            el.blur();\n"
    "            await sleep(50);\n"
    "        } catch (e) {}\n"
    "    }\n"
    "    return out;\n"
    "}"
)


# --- Versteckt fokussierbare Elemente (WCAG 2.4.7 hidden / BITV 9.2.4.7) ----

_HIDDEN_SKIP_JS = """(el) => {
    if (el.getAttribute('aria-hidden') === 'true' || el.closest('[aria-hidden="true"]')) {
        return { shouldSkip: true };
    }
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || el.offsetParent === null || cs.visibility === 'hidden') {
        return { shouldSkip: true };
    }
    if (el.disabled === true) { return { shouldSkip: true }; }
    if (el.tabIndex < 0) { return { shouldSkip: true }; }
    return { shouldSkip: false };
}"""

_HIDDEN_FOCUSABLE_BATCH_JS = (
    "() => {\n"
    "    const domPath = " + DOM_PATH_JS + ";\n"
    "    const skip = " + _HIDDEN_SKIP_JS + ";\n"
    "    const nodes = document.querySelectorAll(\"" + _FOCUSABLE_SELECTOR + "\");\n"
    "    const out = [];\n"
    "    for (let i = 0; i < nodes.length; i++) {\n"
    "        try {\n"
    "            if (skip(nodes[i]).shouldSkip) continue;\n"
    "            out.push({ index: i });\n"
    "        } catch (e) {}\n"
    "    }\n"
    "    return out;\n"
    "}"
)

_HIDDEN_FOCUS_CHUNK_JS = (
    "async (candidates) => {\n"
    "    const nodes = document.querySelectorAll(\"" + _FOCUSABLE_SELECTOR + "\");\n"
    "    const sleep = (ms) => new Promise(r => setTimeout(r, ms));\n"
    "    " + _IS_VISIBLE_REPLICA_JS + "\n"
    "    const domPath = " + DOM_PATH_JS + ";\n"
    "    const out = [];\n"
    "    for (const c of candidates) {\n"
    "        const el = nodes[c.index];\n"
    "        if (!el) continue;\n"
    "        try {\n"
    "            el.focus();\n"
    "            await sleep(50);\n"
    "            if (!isVisible(el)) {\n"
    "                const cs = getComputedStyle(el);\n"
    "                const cls = (typeof el.className === 'string') ? el.className : '';\n"
    "                out.push({\n"
    "                    index: c.index,\n"
    "                    tagName: el.tagName,\n"
    "                    id: el.id,\n"
    "                    className: cls,\n"
    "                    display: cs.display,\n"
    "                    opacity: cs.opacity,\n"
    "                    path: domPath(el),\n"
    "                });\n"
    "            }\n"
    "        } catch (e) {}\n"
    "        finally {\n"
    "            try { el.blur(); } catch (e) {}\n"
    "        }\n"
    "    }\n"
    "    return out;\n"
    "}"
)


# --- Tastaturfallen-Test (WCAG 2.1.2 / BITV 9.2.1.2) -----------------------

# Sammlung in EINEM evaluate: sichtbare, aktivierte, nicht-versteckte,
# nicht-Sprunglink-Fokussierbare als Indices in den Fokus-Selektor.
_TRAP_COLLECT_JS = (
    "() => {\n"
    "    " + _IS_VISIBLE_REPLICA_JS + "\n"
    "    const isEnabled = (el) => {\n"
    "        if (el.disabled) return false;\n"
    "        if (el.closest('fieldset[disabled]')) return false;\n"
    "        if (el.tagName === 'OPTION') {\n"
    "            const sel = el.closest('select');\n"
    "            if (sel && sel.disabled) return false;\n"
    "        }\n"
    "        return true;\n"
    "    };\n"
    "    const mainTargets = ['content','main','navigation','nav','header','footer'];\n"
    "    const isSkipLink = (id, cls, href) => {\n"
    "        return (id || '').toLowerCase().includes('skip')\n"
    "            || (cls || '').toLowerCase().includes('skip')\n"
    "            || ((href || '').startsWith('#') && mainTargets.some(t => (href || '').toLowerCase().includes(t)));\n"
    "    };\n"
    "    const nodes = document.querySelectorAll(\"" + _FOCUSABLE_SELECTOR + "\");\n"
    "    const out = [];\n"
    "    for (let i = 0; i < nodes.length; i++) {\n"
    "        const el = nodes[i];\n"
    "        try {\n"
    "            if (!isVisible(el)) continue;\n"
    "            if (!isEnabled(el)) continue;\n"
    "            if (el.getAttribute('aria-hidden') === 'true') continue;\n"
    "            if (isSkipLink(el.id, el.getAttribute('class') || '', el.getAttribute('href') || '')) continue;\n"
    "            out.push(i);\n"
    "        } catch (e) {}\n"
    "    }\n"
    "    return { count: out.length, indices: out };\n"
    "}"
)

_TRAP_STEP_JS = """() => {
    const el = document.activeElement;
    if (!el || el === document.body) return { element: null, trapDetected: false };
    const id = el.id || '';
    const className = el.className || '';
    const href = el.getAttribute('href') || '';
    const isSkipLink = (
        id.toLowerCase().includes('skip') ||
        className.toLowerCase().includes('skip') ||
        (href.startsWith('#') && ['content','main','navigation','nav','header','footer']
            .some(t => href.toLowerCase().includes(t)))
    );
    if (isSkipLink) return { element: null, trapDetected: false, skipLink: true };
    const tag = el.tagName.toLowerCase();
    const path = [];
    let current = el;
    while (current && current !== document.body) {
        let selector = current.tagName.toLowerCase();
        if (current.id) selector += '#' + current.id;
        else if (current.className) selector += '.' + current.className.split(' ')[0];
        path.unshift(selector);
        current = current.parentElement;
    }
    const wasVisited = el.hasAttribute('data-a11y-visited');
    if (wasVisited) {
        return { element: { tag, path: path.join(' > ') }, trapDetected: true };
    }
    el.setAttribute('data-a11y-visited', 'true');
    return { element: { tag, path: path.join(' > ') }, trapDetected: false };
}"""

_CLEANUP_JS = """() => {
    document.querySelectorAll('[data-a11y-visited]').forEach(el => el.removeAttribute('data-a11y-visited'));
}"""


# --------------------------------------------------------------------------
# 5. Medien-Selektion (video/audio)
# --------------------------------------------------------------------------

def _media_elements(ctx: CheckContext, kinds=("video", "audio")) -> list:
    """Sichtbare (zugängliche) Medien-Elemente der Seite."""
    return [el for el in ctx.soup.find_all(list(kinds)) if is_accessible_element(el)]


def _media_has_ad(video) -> bool:
    """True, wenn eine funktionierende Audiodeskriptions-Spur existiert.

    Ein <track kind="descriptions"> ohne src liefert keine Audiodeskription
    und zählt nicht.
    """
    ad_tracks = [
        t for t in video.find_all("track")
        if t.get("kind") in ("descriptions", "described", "description")
        or ("description" in (t.get("label") or "").lower())
    ]
    if not ad_tracks:
        return False
    return any(t.has_attr("src") and (t.get("src") or "").strip() for t in ad_tracks)


def _media_has_captions(video) -> bool:
    """True, wenn eine funktionierende Untertitel-Spur (kind="captions") existiert.

    Nur kind="captions" ist eine Untertitel-Alternative — kind="subtitles" ist
    eine Übersetzung ohne Geräusche-Information; ein <track> ohne src liefert
    keine Untertitel.
    """
    return any(
        t.get("kind") == "captions"
        and t.has_attr("src") and (t.get("src") or "").strip()
        for t in video.find_all("track")
    )


def _media_ist_design_element(media) -> bool:
    """True, wenn das Medium ein reines Gestaltungselement ist (kein Text nötig).

    Ein stummes Video (muted) ohne Bedienelemente (controls) dient als
    dekorativer Hintergrund: Es hat keinen (nutzbaren) gesprochenen Inhalt und
    bietet dem Nutzer keine Möglichkeit, den Ton zu aktivieren — dafür sind
    keine Untertitel/Audiodeskription erforderlich. Alle Video-Checks, die
    fehlende Textalternativen melden, überspringen solche Elemente.
    """
    return media.has_attr("muted") and not media.has_attr("controls")


# Live-/Adaptiv-Stream-Formate (HLS *.m3u8/*.m3u, MPEG-DASH *.mpd)
_STREAM_EXTENSIONS = (".m3u8", ".m3u", ".mpd")


def _media_ist_live_stream(video) -> bool:
    """True, wenn die Video-Quelle auf einen Live-/Adaptiv-Stream hinweist."""
    quellen = []
    src = video.get("src")
    if src:
        quellen.append(src)
    for source in video.find_all("source"):
        if source.get("src"):
            quellen.append(source.get("src"))
    return any(q.lower().split("?")[0].endswith(_STREAM_EXTENSIONS) for q in quellen)


# --------------------------------------------------------------------------
# Konsistente Navigation / Bezeichnung (BITV 9.3.2.3 / 9.3.2.4, WCAG 3.2.3/3.2.4)
# --------------------------------------------------------------------------
# Signatur-Helfer für die seitenübergreifenden Konsistenz-Checks. Der Runner
# reicht pro Job einen gemeinsamen `state`-Dict über ctx.state — die Checks
# sammeln dort die Signaturen der besuchten Seiten und vergleichen ab Seite 2.

_NAV_IGNORE_TEXTS = {"", "menu", "navigation", "hauptmenü", "hauptnavigation", "seitenmenü"}


def _link_signatur(a) -> tuple:
    """Kompakte Signatur eines Links: (href, sichtbarer Text, aria-label, title).

    href wird normalisiert (klein, ohne Fragment/Whitespace). Text = sichtbarer
    Text, sonst aria-label/title als Fallback. Dient dem Label-Vergleich über
    Seiten hinweg (konsistente Bezeichnung).
    """
    href = (a.get("href") or "").strip().lower().split("#")[0]
    text = a.get_text(" ", strip=True) or (a.get("aria-label") or "").strip() or (a.get("title") or "").strip()
    return href, text


def _norm_link_text(text: str) -> str:
    """Normalisierter Vergleichstext für Bezeichnungen: Whitespace kollabiert,
    kleingeschrieben, führendes ``www.`` entfernt — so gelten „Unityed.de" und
    „www.unityed.de" als dieselbe Bezeichnung (Brand-Variante, kein Befund)."""
    s = re.sub(r"\s+", " ", text.strip()).lower()
    return re.sub(r"^www\.", "", s)


def _konsistente_bezeichnung_befunde(ctx: CheckContext, test_id: str) -> list:
    """Links mit inkonsistenter Bezeichnung (WCAG 3.2.4 / BITV 9.3.2.4).

    Vergleichsschlüssel ist (href, DOM-Pfad): Eine „wiederholt eingesetzte
    Funktion" liegt nur vor, wenn derselbe Link an derselben Komponenten-
    Position (DOM-Pfad im wiederholten Seiten-Template, z. B. Navigation/
    Footer) auf mehreren Seiten wiederkehrt. Steht derselbe Ziel-Link auf
    verschiedenen Seiten an unterschiedlichen Positionen (etwa ein externer
    Link im Inhalt), ist es eine andere Komponente — die Bezeichnung wird
    nicht mit anderen Positionen verglichen (kein False-Positive auf
    Einzel-Links). Bezeichnungen werden normalisiert verglichen
    (``_norm_link_text``). Befunde sind Hinweise, keine abschließende Bewertung.
    """
    state = ctx.state if ctx.state is not None else {}
    labels = state.setdefault("link_labels", {})  # (href, dom_path) → (text, erste URL)

    errors = []
    for a in ctx.soup.find_all("a", href=True):
        if not is_accessible_element(a):
            continue
        href, text = _link_signatur(a)
        if not href or not text:
            # Kein echter Ziel-Link oder keine bezeichenbare Textalternative —
            # Konsistenz ist ohne Bezeichnung nicht bewertbar.
            continue
        schluessel = (href, get_dom_path(a))
        bekannt = labels.get(schluessel)
        if bekannt is None:
            labels[schluessel] = (text, ctx.url)
            continue
        if _norm_link_text(bekannt[0]) != _norm_link_text(text):
            errors.append(finding(
                test_id,
                f"Link „{text}“ ({href}) ist auf einer anderen Seite als "
                f"„{bekannt[0]}“ bezeichnet — wiederholt eingesetzte Funktionen "
                "sollen einheitlich bezeichnet sein (konsistente Bezeichnung)",
                schluessel[1],
                detail=f"Erstmals beobachtet als „{bekannt[0]}“ auf {bekannt[1]}",
            ))
    return errors


def _nav_signatur(ctx: CheckContext) -> tuple[list, list[tuple]]:
    """Navigationselemente + Reihenfolge der Links der aktuellen Seite.

    Betrachtet die sichtbaren (zugänglichen) <nav>-Landmarks; fehlt eine,
    das erste strukturell als Menü erkennbare <ul>/<ol>. Gibt (navs, sig)
    zurück: navs = beteiligte Elemente (für den DOM-Pfad eines Befunds),
    sig = Liste der Link-Signaturen in Dokument-Reihenfolge. Keine Navigation
    ⇒ ([], []).
    """
    soup = ctx.soup
    navs = [el for el in soup.find_all("nav") if is_accessible_element(el)]
    if not navs:
        # Fallback: erstes zugängliches <ul> mit mind. zwei Links (Menü-Heuristik)
        for ul in soup.find_all(["ul", "ol"]):
            if not is_accessible_element(ul):
                continue
            links = [a for a in ul.find_all("a", href=True) if is_accessible_element(a)]
            if len(links) >= 2:
                navs = [ul]
                break
    if not navs:
        return [], []
    sig = []
    for nav in navs:
        for a in nav.find_all("a", href=True):
            if not is_accessible_element(a):
                continue
            href, text = _link_signatur(a)
            if not text or text.lower() in _NAV_IGNORE_TEXTS:
                continue
            sig.append((href, text))
    return navs, sig


def _signaturen_gleich(a: list, b: list) -> bool:
    """True, wenn zwei Navigations-Signaturen (Reihenfolge) identisch sind."""
    if len(a) != len(b):
        return False
    return all(x[0] == y[0] and x[1] == y[1] for x, y in zip(a, b))


def _nav_diff_beschreibung(a: list, b: list) -> str:
    """Kurze Beschreibung, was sich zwischen Referenz- und aktueller Nav ändert."""
    sa = set(a)
    sb = set(b)
    fehlt = [f"{t} ({h})" for h, t in sa - sb][:3]
    neu = [f"{t} ({h})" for h, t in sb - sa][:3]
    teile = []
    if fehlt:
        teile.append("fehlende Einträge: " + ", ".join(fehlt))
    if neu:
        teile.append("neue Einträge: " + ", ".join(neu))
    if not teile:
        # gleiche Menge, andere Reihenfolge
        teile.append("gleiche Einträge in anderer Reihenfolge")
    return "; ".join(teile)


_TRANSCRIPT_KEYWORDS = (
    "transkript", "transcript", "abschrift", "wortprotokoll", "volltext",
    "textfassung", "medienalternative", "untertitel",
)


def _media_has_transcript(media, root) -> bool:
    """True, wenn in unmittelbarer Nähe ein Transkript/Volltext vorhanden ist.

    Geteilt von BITV 9.1.2.1 (Audio + stumme Videos) und 9.1.2.3 (Videos):
    (a) ein Link mit Transkript-/Volltext-Keyword im selben übergeordneten
    Block (Text, aria-label oder title), (b) eine aria-describedby-Referenz
    mit Transkript-Keyword, oder (c) eine audiobeschreibungsspur
    (kind="descriptions") — die zählt bei 9.1.2.3 als Volltext-Fallback nur,
    wenn keine Audiodeskription nötig ist; hier reicht der Verweis.
    """
    parent = media.find_parent()
    if parent is not None:
        for link in parent.find_all("a", href=True):
            hay = " ".join(filter(None, (
                link.get_text(strip=True),
                link.get("aria-label"),
                link.get("title"),
            ))).lower()
            if any(w in hay for w in _TRANSCRIPT_KEYWORDS):
                return True
    describedby = media.get("aria-describedby")
    if describedby:
        for lid in (describedby or "").split():
            el = root.find(id=lid)
            if el is not None:
                hay = (el.get_text(" ", strip=True) or "").lower()
                if any(w in hay for w in _TRANSCRIPT_KEYWORDS):
                    return True
    return False


# --------------------------------------------------------------------------
# 6. Label-/Namen-Helfer (AccName-Heuristik)
# --------------------------------------------------------------------------

def resolve_idrefs(root, ids: str) -> str:
    """Text aller aria-labelledby-Referenzen, durch Leerzeichen getrennt."""
    parts = []
    for lid in (ids or "").split():
        el = root.find(id=lid)
        if el is not None:
            text = el.get_text(" ", strip=True)
            if text:
                parts.append(text)
    return " ".join(parts).strip()


def resolve_accessible_name(element, root) -> str:
    """Zugänglicher Name eines interaktiven Elements (AccName-Heuristik).

    Reihenfolge: aria-labelledby (aufgelöst) → aria-label → eigener Text →
    title → Kind-<img alt> → input-value bei submit/button/reset.
    Verwaiste oder leere aria-labelledby-Referenzen ergeben '' (kein Fallback) —
    das Kriterium verlangt eine funktionierende Referenz, nicht ein Attr-Bürfnis.
    """
    labelledby = element.get("aria-labelledby")
    if labelledby:
        ref_text = resolve_idrefs(root, labelledby)
        if ref_text:
            return ref_text
        return ""

    aria_label = (element.get("aria-label") or "").strip()
    if aria_label:
        return aria_label

    own_text = element.get_text(strip=True)
    if own_text:
        return own_text

    title = (element.get("title") or "").strip()
    if title:
        return title

    if element.name == "input" and (element.get("type") or "text").lower() in ("submit", "button", "reset"):
        value = (element.get("value") or "").strip()
        if value:
            return value

    img_alts = [a.strip() for img in element.find_all("img")
                if (a := (img.get("alt") or "").strip())]
    return " ".join(img_alts).strip()


def has_accessible_name(element, root) -> bool:
    """Interaktives Element hat einen zugänglichen Namen (AccName + Label)."""
    return bool(resolve_accessible_name(element, root) or element_label(element, root))


def element_label(element, root) -> str:
    """Beschriftung eines Formularfelds (programmatisch + textuell) — '' wenn keine.

    Quellen: aria-label, aria-labelledby (aufgelöst, verwaist ⇒ ''),
    label[for], umschließendes <label>, title.
    """
    aria_label = (element.get("aria-label") or "").strip()
    if aria_label:
        return aria_label

    if element.get("aria-labelledby"):
        return resolve_idrefs(root, element.get("aria-labelledby"))

    eid = element.get("id")
    if eid:
        label = root.find("label", {"for": eid})
        if label and label.get_text(strip=True):
            return label.get_text(strip=True)

    parent_label = element.find_parent("label")
    if parent_label:
        text = parent_label.get_text(strip=True)
        own = element.get_text(strip=True)
        if own:
            text = text.replace(own, "").strip()
        if text:
            return text

    return (element.get("title") or "").strip()


def visible_label(element, root) -> str:
    """Sichtbare <label>-Beschriftung (for oder umschließend) — '' wenn keine.

    Für 3.3.2 (Labels or Instructions): nur sichtbarer Text zählt — aria-label,
    title und placeholder sind keine sichtbaren Beschriftungen.
    """
    eid = element.get("id")
    if eid:
        label = root.find("label", {"for": eid})
        if label and label.get_text(strip=True):
            return label.get_text(strip=True)

    parent_label = element.find_parent("label")
    if parent_label:
        text = parent_label.get_text(strip=True)
        own = element.get_text(strip=True)
        if own:
            text = text.replace(own, "").strip()
        if text:
            return text
    return ""


# --------------------------------------------------------------------------
# 7. HTTP-Client mit htaccess-Auth (blockierend; im Runner via to_thread)
# --------------------------------------------------------------------------

def fetch_url(
    url: str,
    *,
    htaccess_user: str | None = None,
    htaccess_pw: str | None = None,
    timeout: int = 10,
    user_agent: str = "a11y-scanner/1.0",
) -> str | None:
    """Lädt eine URL (GET) und liefert den Body — None bei Fehlern/Nicht-200."""
    import requests

    session = requests.Session()
    session.verify = False
    if htaccess_user and htaccess_pw:
        session.auth = (htaccess_user, htaccess_pw)
    try:
        response = session.get(url, timeout=timeout, headers={"User-Agent": user_agent})
        if response.status_code == 200:
            return response.text
    except Exception:
        pass
    return None


def abs_url(ctx: CheckContext, href: str) -> str:
    """Relative hrefs (z. B. 'css/main.css') gegen die Seiten-URL auflösen."""
    return urljoin(ctx.url, href)


# --------------------------------------------------------------------------
# 8. Fokus-Selektor — Definition siehe Abschnitt 4e (vor den Batch-JS)
# --------------------------------------------------------------------------
