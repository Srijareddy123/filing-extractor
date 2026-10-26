"""Rules baseline: regular expressions for the five fields. No training, no model."""

from __future__ import annotations

import re

from filing_extractor.schema import UNRESOLVED, Extraction

_MONEY = (
    r"(?:U\.S\.)?(?:US)?[$€£]\s?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:\s?(?:million|billion))?"
)
_DATE = (
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r" \d{1,2}, ?\d{4}"
)
_PCT = r"\d+(?:\.\d+)?%"

_SIZE_CONTEXT = re.compile(
    r"aggregate (?:principal )?(?:amount|commitments?)|principal amount|commitments?|"
    r"credit facility|line of credit|term loan|revolving|loan amount|maximum",
    re.I,
)
_SIZE_REJECT = re.compile(
    r"sublimit|minimum|whole multiple|integral multiple|in excess thereof|not (?:to )?exceed|"
    r"shall not exceed|fee|basket|threshold|material indebtedness|judgment|"
    r"\bletter of credit\b.{0,40}commitment|swing ?line",
    re.I,
)
_MATURITY_KEY = re.compile(
    r"maturity date|termination date|final maturity|shall mature|will mature|matures on|"
    r"due and payable (?:in full )?on",
    re.I,
)
_MATURITY_REJECT = re.compile(r"extend|extension|availability period|commitment termination", re.I)
_MARGIN_PATTERNS = (
    re.compile(
        rf"(?:Term SOFR|SOFR|LIBOR|Prime Rate|Eurodollar|Adjusted Term SOFR|Daily Simple SOFR)"
        rf"[^.;]{{0,60}}?\bplus\b[^.;%]{{0,40}}?({_PCT})",
        re.I,
    ),
    re.compile(rf"margin (?:of|equal to|means)[^.;%]{{0,30}}?({_PCT})", re.I),
    re.compile(rf"(?:bear|accrue)s?\s+interest[^.;%]{{0,120}}?(?:rate of|at)\s+({_PCT})", re.I),
    re.compile(rf"fixed rate of (?:interest )?(?:equal to )?(?:[a-z\- ]+\()?({_PCT})", re.I),
    re.compile(
        rf"(?:interest|rate)[^.;%]{{0,80}}?\b(?:at|of|equal to)\s+(?:[a-z\- ]+\()?({_PCT})\)?\s+per (?:annum|year)",
        re.I,
    ),
    re.compile(rf"Applicable (?:Margin|Rate)\W+(?:means|shall mean)[^.;%]{{0,100}}?({_PCT})", re.I),
    re.compile(rf"(?:Interest Rate|Rate)\W+(?:means|shall be|is)[^.;%]{{0,60}}?({_PCT})", re.I),
)
_MARGIN_REJECT = re.compile(
    r"default|overdue|Federal Funds|0\.1\d*%|adjustment|\bfee\b|Alternate Base Rate|\bABR\b|"
    r"Base Rate\W+(?:means|shall mean)|ABR\W+(?:means|shall mean)|Adjusted (?:Term|Daily)|Prime Rate\W+(?:means|shall)|"
    r"Floor|Overnight Bank",
    re.I,
)
_AGENT = re.compile(r"as (?:the )?(?:sole )?(?:administrative|collateral|lead) agent", re.I)
_NAME_END = (
    r"(?:N\.A\.|National Association|NATIONAL ASSOCIATION|Bank|BANK|PLC|ACB|LLC|Inc\.|"
    r"Corporation|CORPORATION|Branch|BRANCH|Company|Finance|FINANCE|Capital|CAPITAL)"
)
_NAME = re.compile(
    rf"((?:[A-Z][A-Za-z0-9&.'\-]*)(?:(?:,\s*|\s+)(?:[A-Z][A-Za-z0-9&.'\-]*|of|&)){{0,6}}?"
    rf"(?:,\s*|\s+){_NAME_END}(?:,?\s+(?:N\.A\.|National Association|NATIONAL ASSOCIATION|PLC|ACB|Ltd\.|Inc\.|LLC))*)"
    r"(?=[\s,(]|$)",
)
_RATIO = re.compile(
    r"((?:[A-Z][A-Za-z\-]*\s+){1,7}(?:Ratio|Worth|Liquidity))"
    r"[^.;]{0,420}?(?:exceed|greater than|less than|not (?:to )?be less than|at least|"
    r"of not less than|below|lower than)\s+(?:\w+\s)?(\d+(?:\.\d+)?\s?(?:to|:)\s?1(?:\.0+)?)",
)
_COVENANT_REJECT = re.compile(
    r"Pro Forma|Restricted Payment|Incremental|Investment|Permitted Acquisition|"
    r"Liens?\b|Indebtedness (?:may|to be incurred)|Interest Rate Cap",
)
_WORTH = re.compile(
    r"((?:[A-Z][A-Za-z\-]*\s+){0,3}(?:Net Worth|Liquidity))[^.;$]{0,200}?"
    r"(?:less than|below|at least|not less than)[^$]{0,60}?(\$\s?\d[\d,]*(?:\.\d+)?)",
)


def extract_size(text: str) -> str:
    for m in re.finditer(_MONEY, text):
        if re.fullmatch(r"\D*0(?:\.0+)?", m.group(0)):
            continue
        window = text[max(0, m.start() - 160) : m.end() + 60]
        before = text[max(0, m.start() - 120) : m.start()]
        if _SIZE_CONTEXT.search(window) and not _SIZE_REJECT.search(
            before + text[m.end() : m.end() + 40]
        ):
            return m.group(0).strip()
    return UNRESOLVED


def extract_maturity(text: str) -> str:
    for key in _MATURITY_KEY.finditer(text):
        tail = text[key.end() : key.end() + 220]
        if _MATURITY_REJECT.search(text[max(0, key.start() - 60) : key.end()]):
            continue
        m = re.search(_DATE, tail)
        if m:
            return m.group(0)
        anniv = re.search(r"the (?:\w+ )?anniversary of the [A-Z][\w ]+? Date", tail)
        if anniv:
            return anniv.group(0)
    return UNRESOLVED


def extract_margin(text: str) -> str:
    for pattern in _MARGIN_PATTERNS:
        for m in pattern.finditer(text):
            context = text[max(0, m.start() - 80) : m.end() + 20]
            if not _MARGIN_REJECT.search(context):
                return m.group(1)
    return UNRESOLVED


def extract_lender(text: str) -> str:
    for anchor in _AGENT.finditer(text):
        window = text[max(0, anchor.start() - 220) : anchor.start()]
        names = list(_NAME.finditer(window))
        if names:
            return names[-1].group(1).strip(" ,")
    return UNRESOLVED


def extract_covenant(text: str) -> str:
    if _COVENANT_REJECT.search(text[:120]):
        return UNRESOLVED
    m = _RATIO.search(text)
    if not m:
        w = _WORTH.search(text)
        if w:
            return f"{w.group(1).strip()} | {w.group(2)}"
        return UNRESOLVED
    name = re.sub(r"^(?:The|the|A|An|Permit|Maintain|Section|SECTION)\s+", "", m.group(1)).strip()
    name = re.sub(r"^\d+(\.\d+)*\.?\s*", "", name)
    return f"{name} | {m.group(2)}"


class RulesExtractor:
    """Regex baseline with the same interface as the model-backed extractors."""

    name = "rules"

    def extract(self, text: str) -> Extraction:
        return Extraction(
            facility_size=extract_size(text),
            maturity=extract_maturity(text),
            interest_margin=extract_margin(text),
            lender=extract_lender(text),
            financial_covenants=extract_covenant(text),
        )
