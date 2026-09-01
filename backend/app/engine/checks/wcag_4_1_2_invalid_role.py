"""WCAG 4.1.2 — Name, Rolle, Wert: nicht standardisierte ARIA-Rolle.

Fixes (Review): Rollenliste auf ARIA 1.2 + DPUB-ARIA vervollständigt
(meter, code, generic, mark, strong, doc-*, …); Leerzeichen-getrennte
Fallback-Rollen (role="foo button") einzeln geprüft — ein gültiger Token
reicht.
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

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


async def check_invalid_role(ctx: CheckContext):
    """WCAG 4.1.2 — nicht standardisierte ARIA-Rolle (Fallback-Tokens erlaubt)."""
    errors = []
    for elem in ctx.soup.find_all(attrs={"role": True}):
        if not is_accessible_element(elem):
            continue
        tokens = [r.strip() for r in (elem.get("role") or "").split()]
        if not tokens:
            continue
        if not any(tok in _VALID_ARIA_ROLES for tok in tokens):
            errors.append(finding("WCAG_4_1_2_INVALID_ROLE",
                                  f"Ungültige ARIA-Rolle '{' '.join(tokens)}'",
                                  get_dom_path(elem)))
    return errors
