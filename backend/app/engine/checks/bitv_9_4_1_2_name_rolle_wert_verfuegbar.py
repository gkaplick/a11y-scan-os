"""BITV_9_4_1_2_NAME_ROLLE_WERT_VERFUEGBAR — Name, Rolle, Wert verfügbar.

Prüfschritt 9.4.1.2 (bitvtest.de): Alle Bedienelemente (native HTML-Elemente
und selbst gestaltete Widgets) müssen Name, Rolle und Zustand über die
Barrierefreiheits-API bereitstellen. Unsematische Elemente (``div``/``span``),
die per JavaScript zu Bedienelementen gemacht werden, brauchen WAI-ARIA.

Automatisierbar (Zusammenführung der abdeckenden WCAG-Checks zu 4.1.2):
- ``<button>`` ohne zugänglichen Namen (AccName-Heuristik)
- interaktive Elemente (``input``/``select``/``textarea``/``a`` + ARIA-Widget-
  Rollen) ohne zugänglichen Namen
- ``role="dialog"`` ohne ``aria-label``/``aria-labelledby``
- ungültige ARIA-Rollen (Leerzeichen-getrennte Fallback-Tokens erlaubt)
- ``aria-hidden``/``aria-expanded`` mit ungültigem Wert (nur true/false)
- ``<a>`` ohne ``href`` und ohne Rolle → unsemantisches Bedienelement (F20/F59)
- ``div``/``span`` mit Event-Handler und ``tabindex`` ohne Rolle (F59)

Nicht automatisierbar: die fachliche Prüfung komplexer Widgets auf vollständige,
dynamisch gepflegte ARIA-Zustände (manuell mit Screenreader/ARIA-APG).
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path, is_accessible_element
from ._helpers import has_accessible_name

_BITV_TEST_ID = "BITV_9_4_1_2_NAME_ROLLE_WERT_VERFUEGBAR"

_VALID_ARIA_ROLES = {
    # ARIA 1.2
    "alert", "alertdialog", "application", "article", "banner", "blockquote",
    "button", "caption", "cell", "checkbox", "code", "columnheader", "combobox",
    "comment", "complementary", "contentinfo", "definition", "deletion", "dialog",
    "directory", "document", "emphasis", "feed", "figure", "form", "generic",
    "grid", "gridcell", "group", "heading", "img", "insertion", "link", "list",
    "listbox", "listitem", "log", "main", "mark", "marquee", "math", "menu",
    "menubar", "menuitem", "menuitemcheckbox", "menuitemradio", "meter",
    "navigation", "none", "note", "option", "paragraph", "presentation",
    "progressbar", "radio", "radiogroup", "region", "row", "rowgroup",
    "rowheader", "scrollbar", "search", "searchbox", "separator", "slider",
    "spinbutton", "status", "strong", "subscript", "suggestion", "superscript",
    "switch", "tab", "table", "tablist", "tabpanel", "term", "textbox", "timer",
    "toolbar", "tooltip", "tree", "treegrid", "treeitem",
    # DPUB-ARIA
    "doc-abstract", "doc-acknowledgments", "doc-afterword", "doc-appendix",
    "doc-backlink", "doc-biblioentry", "doc-bibliography", "doc-biblioref",
    "doc-chapter", "doc-colophon", "doc-conclusion", "doc-cover", "doc-credit",
    "doc-credits", "doc-dedication", "doc-endnote", "doc-endnotes", "doc-epigraph",
    "doc-epilogue", "doc-errata", "doc-example", "doc-footnote", "doc-foreword",
    "doc-glossary", "doc-glossref", "doc-index", "doc-introduction", "doc-noteref",
    "doc-notice", "doc-pagebreak", "doc-pagelist", "doc-part", "doc-preface",
    "doc-prologue", "doc-pullquote", "doc-qna", "doc-subtitle", "doc-tip", "doc-toc",
}

_INTERACTIVE_ROLE_RE = re.compile(r"button|link|textbox|combobox|checkbox|radio|slider|spinbutton")

# Event-Handler, die ein div/span zu einem Bedienelement machen (F59)
_INTERACTION_ATTRS = ("onclick", "onmousedown", "onmouseup", "onkeydown", "onkeyup")


async def check_name_rolle_wert_verfuegbar(ctx: CheckContext):
    """BITV 9.4.1.2 — Name, Rolle, Wert für interaktive Elemente und ARIA-Attribute."""
    root = ctx.soup
    errors: list = []

    # --- <button> ohne zugänglichen Namen (WCAG_4_1_2_BUTTON_NAME) ----------
    for button in root.find_all("button"):
        if is_accessible_element(button) and not has_accessible_name(button, root):
            errors.append(finding(
                _BITV_TEST_ID,
                "<button> ohne zugänglichen Namen",
                get_dom_path(button),
            ))

    # --- interaktive Elemente ohne zugänglichen Namen (WCAG_4_1_2_ARIA_LABEL_MISSING)
    interactive = root.find_all(["input", "select", "textarea", "a"])
    interactive += root.find_all(attrs={"role": _INTERACTIVE_ROLE_RE})
    for elem in interactive:
        if not is_accessible_element(elem):
            continue
        if elem.name == "button":
            continue  # eigener Zweig oben (kein Doppelbefund)
        if (elem.get("type") or "").lower() == "hidden":
            continue
        if elem.get("inert") is not None:
            continue
        if re.search(r"display\s*:\s*none|visibility\s*:\s*hidden",
                     elem.get("style") or "", re.I):
            continue
        if has_accessible_name(elem, root):
            continue
        info = elem.name
        if elem.get("type"):
            info += f"[type={elem.get('type')}]"
        if elem.get("id"):
            info += f"#{elem.get('id')}"
        elif elem.get("class"):
            cls = elem.get("class")
            info += f".{cls[0] if isinstance(cls, list) else cls}"
        errors.append(finding(
            _BITV_TEST_ID,
            f"<{info}> ohne zugänglichen Namen (Name, Rolle, Wert nicht verfügbar)",
            get_dom_path(elem),
        ))

    # --- role=dialog ohne aria-label/aria-labelledby (WCAG_4_1_2_DIALOG_LABEL)
    for dialog in root.find_all(attrs={"role": "dialog"}):
        if is_accessible_element(dialog):
            has_label = dialog.get("aria-label") or dialog.get("aria-labelledby")
            if not has_label:
                errors.append(finding(
                    _BITV_TEST_ID,
                    "role='dialog' ohne aria-label/aria-labelledby (Name fehlt)",
                    get_dom_path(dialog),
                ))

    # --- ungültige ARIA-Rollen (WCAG_4_1_2_INVALID_ROLE) --------------------
    for elem in root.find_all(attrs={"role": True}):
        if not is_accessible_element(elem):
            continue
        tokens = [r.strip() for r in (elem.get("role") or "").split()]
        if not tokens:
            continue
        if not any(tok in _VALID_ARIA_ROLES for tok in tokens):
            errors.append(finding(
                _BITV_TEST_ID,
                f"Ungültige ARIA-Rolle '{' '.join(tokens)}' (Rolle nicht verfügbar)",
                get_dom_path(elem),
            ))

    # --- aria-hidden mit ungültigem Wert (WCAG_4_1_2_ARIA_HIDDEN) -----------
    for elem in root.find_all(attrs={"aria-hidden": True}):
        if is_accessible_element(elem):
            value = (elem.get("aria-hidden") or "").lower()
            if value not in ["true", "false"]:
                errors.append(finding(
                    _BITV_TEST_ID,
                    f"Ungültiger Wert für aria-hidden '{value}' (Zustand nicht verfügbar)",
                    get_dom_path(elem),
                ))

    # --- aria-expanded mit ungültigem Wert (WCAG_4_1_2_ARIA_EXPANDED) -------
    for elem in root.find_all(attrs={"aria-expanded": True}):
        if not is_accessible_element(elem):
            continue
        value = (elem.get("aria-expanded") or "").lower()
        if value not in ["true", "false"]:
            errors.append(finding(
                _BITV_TEST_ID,
                f"Ungültiger aria-expanded-Wert '{value}' (Zustand nicht verfügbar)",
                get_dom_path(elem),
            ))

    # --- <a> ohne href und ohne Rolle (unsemantisches Bedienelement) --------
    for a in root.find_all("a"):
        if not is_accessible_element(a):
            continue
        if a.has_attr("href"):
            continue
        if a.get("role"):
            continue  # ARIA-Rolle macht das Bedienelement explizit
        errors.append(finding(
            _BITV_TEST_ID,
            "<a> ohne href und ohne ARIA-Rolle — Bedienelement ohne Rolle",
            get_dom_path(a),
        ))

    # --- div/span mit Event-Handler + tabindex ohne Rolle (F59) -------------
    for el in root.find_all(["div", "span"]):
        if not is_accessible_element(el):
            continue
        if el.get("role"):
            continue  # Semantik per ARIA nachgebildet
        if el.get("tabindex") is None:
            continue  # nicht fokussierbar → kein Bedienelement
        if not any(el.has_attr(attr) for attr in _INTERACTION_ATTRS):
            continue
        errors.append(finding(
            _BITV_TEST_ID,
            f"<{el.name}> mit Event-Handler und tabindex ohne ARIA-Rolle — "
            f"Bedienelement ohne Rolle (F59)",
            get_dom_path(el),
        ))

    return errors
