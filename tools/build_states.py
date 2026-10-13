#!/usr/bin/env python3
"""Build /states pages and the probate calculator from verified research JSON."""
import json
import re
from pathlib import Path

ROOT = Path("/workspace")
OUT = ROOT / "states"
RESEARCH_DIRS = [Path("/tmp/research"), ROOT / "research"]
MANUAL = ROOT / "data" / "manual.json"

ORDER = [
    ("Alabama", "alabama"), ("Alaska", "alaska"), ("Arizona", "arizona"),
    ("Arkansas", "arkansas"), ("California", "california"), ("Colorado", "colorado"),
    ("Connecticut", "connecticut"), ("Delaware", "delaware"),
    ("District of Columbia", "district-of-columbia"), ("Florida", "florida"),
    ("Georgia", "georgia"), ("Hawaii", "hawaii"), ("Idaho", "idaho"),
    ("Illinois", "illinois"), ("Indiana", "indiana"), ("Iowa", "iowa"),
    ("Kansas", "kansas"), ("Kentucky", "kentucky"), ("Louisiana", "louisiana"),
    ("Maine", "maine"), ("Maryland", "maryland"), ("Massachusetts", "massachusetts"),
    ("Michigan", "michigan"), ("Minnesota", "minnesota"), ("Mississippi", "mississippi"),
    ("Missouri", "missouri"), ("Montana", "montana"), ("Nebraska", "nebraska"),
    ("Nevada", "nevada"), ("New Hampshire", "new-hampshire"), ("New Jersey", "new-jersey"),
    ("New Mexico", "new-mexico"), ("New York", "new-york"),
    ("North Carolina", "north-carolina"), ("North Dakota", "north-dakota"),
    ("Ohio", "ohio"), ("Oklahoma", "oklahoma"), ("Oregon", "oregon"),
    ("Pennsylvania", "pennsylvania"), ("Rhode Island", "rhode-island"),
    ("South Carolina", "south-carolina"), ("South Dakota", "south-dakota"),
    ("Tennessee", "tennessee"), ("Texas", "texas"), ("Utah", "utah"),
    ("Vermont", "vermont"), ("Virginia", "virginia"), ("Washington", "washington"),
    ("West Virginia", "west-virginia"), ("Wisconsin", "wisconsin"), ("Wyoming", "wyoming"),
]

BRAND = '<a class="brand" href="/" aria-label="TaxFreeTrusts home"><svg viewBox="0 0 32 32" aria-hidden="true" focusable="false"><circle cx="16" cy="16" r="14.6" fill="none" stroke="currentColor" stroke-width="1.6"/><circle cx="16" cy="16" r="11.9" fill="none" stroke="currentColor" stroke-width=".7" stroke-dasharray="1.2 1.1"/><path fill="currentColor" d="M9.2 8.6h13.6v2.6h-4.1a3.9 3.9 0 0 1-.5 6.2l1.3 7.2h-7l1.3-7.2a3.9 3.9 0 0 1-.5-6.2H9.2z"/></svg><span>TaxFreeTrusts</span></a>'

DROP_SENTENCE = re.compile(
    r"integer used|smallEstateLimit|opened page|pages opened|page that was opened|"
    r"page extract|was not displayed|was not copied|pages that were opened|"
    r"on the code site on",
    re.I,
)

WORDS = {
    "two and one-half": 2.5, "two and a half": 2.5, "one-half of 1": 0.5,
    "one-half of one": 0.5, "ten": 10, "nine": 9, "eight": 8, "seven": 7,
    "six": 6, "five": 5, "four": 4, "three": 3, "two": 2, "one": 1,
}


def clean(text):
    if not text:
        return ""
    text = (text.replace("\u2014", ", ").replace("\u2013", "-")
            .replace("\u00a7", "section ").replace("\u2019", "'")
            .replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
            .replace("\u00a0", " ").replace("\u00bd", " 1/2"))
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n\s*", " ", text).strip()
    if re.search(r"\bhonest\b", text, re.I) or re.search(r"\bJeff\b", text):
        raise SystemExit("banned word in copy")
    if "\u2014" in text or "\u2013" in text:
        raise SystemExit("dash left in copy")
    return text


def public_prose(text):
    text = clean(text)
    if not text:
        return ""
    parts = re.split(r"(?<=[.])\s+", text)
    kept = [p for p in parts if p and not DROP_SENTENCE.search(p)]
    return " ".join(kept).strip()


def esc(text):
    return (text.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def money(n):
    return f"${n:,.0f}" if float(n).is_integer() else f"${n:,.2f}"


def above_rate(note):
    if not note:
        return None
    if re.search(r"reasonable amount to be determined by the court", note, re.I) and not re.search(r"\d", note[:40]):
        # still look for a percent that applies above the last bracket
        pass
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:%|percent|per cent)", note, re.I)
    if m:
        return float(m.group(1)) / 100.0
    for phrase, num in WORDS.items():
        if re.search(phrase + r"\s*(?:percent|per cent)", note, re.I):
            return num / 100.0
    return None


def fee_role(fees):
    t = (fees or "").lower()
    if "not in excess" in t or "may not exceed" in t or "shall not exceed" in t or "not to exceed" in t:
        return "Statutory maximum"
    if "minimum compensation" in t or "sets minimum" in t:
        return "Statutory minimum"
    if "presumed" in t and "reasonable" in t:
        return "Presumed reasonable"
    if "percent" in t or "%" in t:
        return "Statutory commission"
    return "Reasonable compensation"


def tax_card(row):
    kind = row.get("taxKind")
    raw = row.get("taxDetail") or ""
    detail = raw.lower()
    if not raw.strip():
        return None
    # A second tax was not on the page we used. Do not print a short label for it.
    if "separate official page on an estate tax" in detail:
        return None
    if "no longer has an estate tax or inheritance tax" in detail and "still subject" in detail:
        return None
    if (
        "no longer has an estate tax" in detail
        or "no state estate transfer tax is due" in detail
        or "not currently imposed or collected" in detail
        or "there is no longer an estate tax" in detail
        or ("pick-up tax" in detail and "no longer" in detail)
    ):
        return "No current estate tax"
    # Illinois mentions the federal credit and also has its own exclusion.
    own_exclusion = "imposes an estate tax" in detail and "exclusion" in detail
    pickup = (
        "equal to the maximum allowable federal credit" in detail
        or "maximum federal estate tax credit" in detail
    )
    if pickup and not own_exclusion:
        return "Tied to a federal credit"
    if kind == "none" or "no estate tax" in detail or ("does not have an inheritance tax" in detail and "no estate" in detail):
        if kind == "inheritance":
            return "Inheritance tax"
        if "eliminated" in detail or "repeal" in detail or "no longer" in detail or "not required" in detail or kind == "none":
            return "No current estate tax"
    if kind == "both":
        return "Estate and inheritance tax"
    if kind == "inheritance":
        return "Inheritance tax"
    if kind == "estate":
        return "Estate tax"
    return None


def community_card(row):
    if not row.get("communityDetail"):
        return None
    d = row.get("communityDetail").lower()
    c = row.get("community")
    if "marital property" in d:
        return "Marital property"
    if c == "community":
        return "Community property"
    if c == "opt-in" and "may hold" in d:
        return "May be held as community property"
    if c == "opt-in":
        return "Opt-in community property"
    if c == "common-law":
        return "Separate property"
    return "Spouses' property"


def formulas_for(row):
    out = []
    ff = row.get("feeFormula")
    if ff and ff.get("brackets"):
        note = clean(ff.get("aboveNote") or "")
        out.append({
            "label": fee_role(row.get("fees")),
            "base": clean(ff.get("base") or "the value described in the statute"),
            "kind": "marginal",
            "brackets": ff["brackets"],
            "aboveRate": above_rate(note),
            "aboveNote": note,
        })
    if row.get("slug") == "florida":
        out.append({
            "label": "Attorney fee presumed reasonable. Not a mandatory fee.",
            "base": "the compensable value of the estate, the inventory value of the probate estate assets and the income earned during administration",
            "kind": "fl-atty",
            "brackets": [],
            "aboveRate": None,
            "aboveNote": "Section 733.6171 says there is not a mandatory statutory attorney fee. The schedule is what the statute calls presumed reasonable for ordinary services.",
        })
    return out


def load_rows():
    by = {}
    for folder in RESEARCH_DIRS:
        if not folder.exists():
            continue
        for path in sorted(folder.glob("*.json")):
            if path.name == "manual.json":
                continue
            data = json.loads(path.read_text())
            if isinstance(data, dict):
                data = [data]
            for row in data:
                by[row["slug"]] = row
    if MANUAL.exists():
        for row in json.loads(MANUAL.read_text()):
            by[row["slug"]] = row
    return by


def sources_of(row):
    seen = set()
    items = []
    for key in ("processSource", "feesSource", "smallEstateSource", "taxSource", "communitySource"):
        src = row.get(key) or {}
        url = src.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        items.append({"title": clean(src.get("title") or url), "url": url})
    if row.get("slug") == "california":
        extra = [
            ("California Courts, adjusted small-estate amounts", "https://selfhelp.courts.ca.gov/probate/simple-transfer"),
            ("Judicial Council, Probate Code section 890 adjusted amounts", "https://courts.ca.gov/system/files/file/probate-code-890-adjusted-amounts.pdf"),
        ]
        for title, url in extra:
            if url not in seen:
                items.append({"title": title, "url": url})
                seen.add(url)
    if row.get("slug") == "florida":
        for title, url in (
            ("2026 Florida Statutes section 735.201", "https://www.flsenate.gov/Laws/Statutes/2026/735.201"),
            ("2026 Florida Statutes section 733.6171", "https://www.flsenate.gov/Laws/Statutes/2026/733.6171"),
        ):
            if url not in seen:
                items.append({"title": title, "url": url})
                seen.add(url)
    if row.get("slug") == "washington":
        url = "https://dor.wa.gov/taxes-rates/other-taxes/estate-tax-tables"
        if url not in seen:
            items.append({"title": "Washington Department of Revenue, estate tax tables", "url": url})
    return items


def gaps_for(row):
    gaps = []
    if not public_prose(row.get("process")):
        gaps.append("probate process")
    if not public_prose(row.get("fees")):
        gaps.append("statutory or typical fees")
    if not public_prose(row.get("smallEstate")) and row.get("smallEstateLimit") is None:
        gaps.append("small-estate affidavit limit")
    if not public_prose(row.get("taxDetail")):
        gaps.append("estate or inheritance tax")
    if not public_prose(row.get("communityDetail")):
        gaps.append("community property status")
    detail = (row.get("taxDetail") or "") + " " + (row.get("smallEstate") or "")
    if re.search(
        r"does not mention an inheritance tax|inheritance tax not|"
        r"whether an inheritance tax exists|does not say there is no inheritance tax",
        detail,
        re.I,
    ):
        if "inheritance tax" not in " ".join(gaps):
            gaps.append("inheritance tax, not stated on the estate-tax page")
    if re.search(r"separate official page on an estate tax", row.get("taxDetail") or "", re.I):
        gaps.append("estate tax, not on the inheritance-tax page")
    return gaps


def para(text):
    text = public_prose(text)
    if not text:
        return ""
    return f"<p>{esc(text)}</p>"


def section(title, text, source):
    body = para(text)
    if not body:
        return ""
    src = ""
    if source and source.get("url"):
        src = f'<p class="sources">Source: <a href="{esc(source["url"])}">{esc(clean(source.get("title") or "Statute or court page"))}</a></p>'
    return f"<h2>{esc(title)}</h2>\n{body}\n{src}\n"


def fact_cards(row):
    cards = []
    if row.get("courtName"):
        court = clean(row["courtName"])
        if court[:1].islower():
            court = court[:1].upper() + court[1:]
        cards.append(("Court", court, "Where the estate is opened."))
    limit = row.get("smallEstateLimit")
    if isinstance(limit, (int, float)):
        cards.append(("Small-estate figure", money(limit), "Only if the statute's conditions are met. Read the section below."))
    tc = tax_card(row)
    if tc:
        cards.append(("Tax", tc, "See the tax section for the exemption or the repeal."))
    cc = community_card(row)
    if cc:
        cards.append(("Spouses", cc, "See the property section for the statute's words."))
    if not cards:
        return ""
    bits = []
    for k, strong, rest in cards:
        bits.append(f'<div class="fact"><span class="k">{esc(k)}</span><strong>{esc(strong)}</strong><p>{esc(rest)}</p></div>')
    return '<div class="fact-grid">' + "".join(bits) + "</div>"


def faqs(row):
    name = row["name"]
    items = []
    items.append((
        f"Does a living trust avoid probate in {name}?",
        "A revocable living trust holds the assets you title in the trustee's name. The successor trustee handles those assets. Property still titled in your own name can be a probate matter. A pour-over will can send leftover assets into the trust, and those leftover assets may still pass through probate first."
    ))
    if public_prose(row.get("smallEstate")):
        items.append((f"What is the small-estate procedure in {name}?", public_prose(row["smallEstate"])))
    if public_prose(row.get("fees")):
        items.append((f"How are probate fees set in {name}?", public_prose(row["fees"])))
    if public_prose(row.get("taxDetail")):
        items.append((f"Does {name} tax an estate or an inheritance?", public_prose(row["taxDetail"])))
    if public_prose(row.get("communityDetail")):
        items.append((f"How does {name} treat property of spouses?", public_prose(row["communityDetail"])))
    return items


def json_ld(row, url):
    name = row["name"]
    crumbs = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://taxfreetrusts.com/"},
            {"@type": "ListItem", "position": 2, "name": "States", "item": "https://taxfreetrusts.com/states"},
            {"@type": "ListItem", "position": 3, "name": name, "item": url},
        ],
    }
    faq = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in faqs(row)
        ],
    }
    blob = json.dumps([crumbs, faq], ensure_ascii=True).replace("<", "\\u003c")
    return f'<script type="application/ld+json">{blob}</script>'


def chrome(current_learn=False):
    learn = ' aria-current="page"' if current_learn else ""
    nav = f'''<header class="site-head"><div class="wrap">{BRAND}
<nav class="nav-desk" aria-label="Main"><a href="/pricing">Plans and prices</a><a href="/learn-living-trust"{learn}>Learn</a><a href="/about">About</a><a href="/support">Support</a><a class="btn btn-ink btn-small" href="/start">Start the planner</a></nav>
<details class="nav-mob"><summary>Menu</summary><nav aria-label="Main, mobile"><ul><li><a href="/pricing">Plans and prices</a></li><li><a href="/learn-living-trust"{learn}>Learn</a></li><li><a href="/about">About</a></li><li><a href="/support">Support</a></li><li><a href="/start">Start the planner</a></li></ul></nav></details>
</div></header>'''
    foot = f'''<footer class="site-foot"><div class="wrap"><div class="foot-grid">
<div>{BRAND}<p style="margin-top:14px;max-width:24em">A draft desk for wills and living trusts. Five questions, posted prices, a packet you print, sign and fund.</p></div>
<div><h2>Packets</h2><ul><li><a href="/pricing">Plans and prices</a></li><li><a href="/start">Start the planner</a></li></ul></div>
<div><h2>Learn</h2><ul><li><a href="/learn-living-trust">Living trusts</a></li><li><a href="/learn-fund">Funding a trust</a></li><li><a href="/learn-taxes">Trusts and taxes</a></li><li><a href="/states">Probate by state</a></li></ul></div>
<div><h2>The desk</h2><ul><li><a href="/about">About</a></li><li><a href="/support">Support</a></li><li><a href="mailto:plan@taxfreetrusts.com">plan@taxfreetrusts.com</a></li><li><a href="/privacy">Privacy</a></li><li><a href="/terms">Terms</a></li></ul></div>
</div><div class="foot-line"><span>Education and document drafts. Not legal or tax advice.</span><span>&copy; 2026 TaxFreeTrusts.com</span></div></div></footer>'''
    return nav, foot


def head(title, desc, url, ld=""):
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="theme-color" content="#101412">
<link rel="canonical" href="{esc(url)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{esc(url)}">
<meta property="og:image" content="https://taxfreetrusts.com/icon-512.png">
<meta property="og:image:alt" content="TaxFreeTrusts seal">
<meta property="og:site_name" content="TaxFreeTrusts">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="https://taxfreetrusts.com/icon-512.png">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" href="/favicon-32x32.png" type="image/png" sizes="32x32">
<link rel="icon" href="/favicon-16x16.png" type="image/png" sizes="16x16">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<link rel="stylesheet" href="/fonts.css">
<link rel="stylesheet" href="/site.css">
{ld}
</head>'''


def page_for(row):
    name = row["name"]
    slug = row["slug"]
    url = f"https://taxfreetrusts.com/states/{slug}"
    desc = f"Living trust or probate in {name}: the court path, fees, small-estate rule, tax, and spouses' property, each point linked to a statute or a court site."
    if len(desc) > 160:
        desc = f"Living trust or probate in {name}, with the statute or court page linked for each point we could verify."
    ld = json_ld(row, url)
    nav, foot = chrome()
    gaps = gaps_for(row)
    gap_html = ""
    if gaps:
        gap_html = f'<p class="gap-note">Not stated here, because we did not verify it from a statute or a court site: {esc(", ".join(gaps))}.</p>'
    faq_html = "".join(
        f"<details><summary>{esc(q)}</summary><div class=\"ans\"><p>{esc(a)}</p></div></details>"
        for q, a in faqs(row)
    )
    src_html = "".join(f'<li><a href="{esc(s["url"])}">{esc(s["title"])}</a></li>' for s in sources_of(row))
    forms = formulas_for(row)
    base_hint = forms[0]["base"] if forms else "a figure you want to compare with the small-estate amount on this page"
    calc = f'''<form class="calc" data-state="{esc(slug)}" action="#calc-{esc(slug)}">
<p class="eyebrow">Calculator</p>
<h2 id="calc-{esc(slug)}">Probate cost</h2>
<p>Enter a dollar amount. The result uses only a statutory schedule on this page. It leaves out court filing fees, extraordinary services, and any amount the statute leaves to the judge.</p>
<div class="field"><label for="estate-{esc(slug)}">Amount to test</label>
<span class="hint" style="display:block;font-weight:400;color:var(--muted);font-size:14.5px;margin:0 0 8px">{esc(base_hint)}</span>
<input id="estate-{esc(slug)}" name="estate" inputmode="decimal" autocomplete="off"></div>
<button class="btn btn-ink" type="submit">Calculate</button>
<div class="calc-out" role="status" aria-live="polite"></div>
</form>'''
    body = f'''{head(f"Living trust vs probate in {name} | TaxFreeTrusts", desc, url, ld)}
<body>
<a class="skip" href="#main">Skip to content</a>
{nav}
<main id="main">
<section class="page-head has-seal"><div class="wrap">
<p class="crumb"><a href="/">Home</a> / <a href="/states">States</a> / {esc(name)}</p>
<p class="eyebrow">Living trust or probate</p>
<h1>{esc(name)}</h1>
<p class="lede">What a funded revocable living trust changes, and the {esc(name)} probate rules we could verify from a statute or a court site.</p>
</div></section>
<div class="wrap article-grid"><article class="prose">
{fact_cards(row)}
<h2>Living trust or probate</h2>
<p>A revocable living trust holds assets you title in the trustee's name. You can serve as trustee while you are able. At death, the successor trustee handles those assets. Property you leave in your own name can still go through the probate court. A pour-over will sends leftover assets into the trust, and those leftover assets may pass through probate first.</p>
{section("The probate path", row.get("process"), row.get("processSource"))}
{section("Fees", row.get("fees"), row.get("feesSource"))}
{calc}
{section("Small estate", row.get("smallEstate"), row.get("smallEstateSource"))}
{section("Estate or inheritance tax", row.get("taxDetail"), row.get("taxSource"))}
{section("Property of spouses", row.get("communityDetail"), row.get("communitySource"))}
{gap_html}
<h2>Questions</h2>
<div class="faq">{faq_html}</div>
<h2>Sources</h2>
<ul class="sources">{src_html}</ul>
</article>
<aside><div class="aside-card">
<p class="eyebrow">Planner</p>
<h2>Start with {esc(name)} filled in</h2>
<p class="muted">Five questions. The state field opens on {esc(name)}.</p>
<a class="btn btn-ink btn-block" href="/start?state={esc(slug)}">Start the planner</a>
<p style="margin:14px 0 0"><a href="/pricing">Living trust packet, $349</a></p>
<p style="margin:14px 0 0"><a href="/states">All states</a></p>
</div></aside>
</div>
</main>
{foot}
<script src="/payments.js"></script>
<script src="/probate-calc.js"></script>
<script src="/motion.js"></script>
</body>
</html>
'''
    return body, forms, gaps


def hub(rows):
    url = "https://taxfreetrusts.com/states"
    desc = "Probate and living trusts in all 50 states and the District of Columbia, with statute and court sources."
    crumbs = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://taxfreetrusts.com/"},
            {"@type": "ListItem", "position": 2, "name": "States", "item": url},
        ],
    }
    faq_pairs = [
        ("What is on each state page?", "Each page covers the probate path, fees, the small-estate procedure, estate or inheritance tax, and how spouses hold property, but only where a statute or a court site states the point. A missing point is left off the page."),
        ("Does the calculator invent a fee?", "No. It multiplies a statutory schedule when the page has one. If the statute says reasonable compensation and gives no percentage, the calculator does not invent a dollar fee."),
    ]
    faq = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in faq_pairs
        ],
    }
    ld = json.dumps([crumbs, faq], ensure_ascii=True).replace("<", "\\u003c")
    nav, foot = chrome()
    links = []
    for name, slug in ORDER:
        row = rows[slug]
        bits = []
        if isinstance(row.get("smallEstateLimit"), (int, float)):
            bits.append(money(row["smallEstateLimit"]))
        card = tax_card(row)
        if card:
            bits.append(card)
        small = f'<small>{esc(" · ".join(bits))}</small>' if bits else ""
        links.append(f'<li><a href="/states/{slug}">{esc(name)}{small}</a></li>')
    options = "".join(f'<option value="{slug}">{esc(name)}</option>' for name, slug in ORDER)
    faq_html = "".join(f"<details><summary>{esc(q)}</summary><div class=\"ans\"><p>{esc(a)}</p></div></details>" for q, a in faq_pairs)
    return f'''{head("Probate by state | TaxFreeTrusts", desc, url, f'<script type="application/ld+json">{ld}</script>')}
<body>
<a class="skip" href="#main">Skip to content</a>
{nav}
<main id="main">
<section class="page-head has-seal"><div class="wrap">
<p class="crumb"><a href="/">Home</a> / States</p>
<p class="eyebrow">Living trust or probate</p>
<h1>Probate by state</h1>
<p class="lede">Fifty states and the District of Columbia. Each page keeps a point only when a statute or a court site states it.</p>
</div></section>
<div class="wrap" style="padding-top:clamp(36px,5vw,64px);padding-bottom:clamp(64px,8vw,100px)">
<form class="calc" data-state="alabama" action="#calc-hub">
<p class="eyebrow">Calculator</p>
<h2 id="calc-hub">Probate cost</h2>
<p>Pick a state and enter an amount. The result uses that state's statutory schedule when we verified one. It leaves out filing fees and anything the statute leaves to the judge.</p>
<div class="field"><label for="calc-state">State</label>
<select id="calc-state" name="state">{options}</select></div>
<div class="field"><label for="estate-hub">Amount to test</label>
<input id="estate-hub" name="estate" inputmode="decimal" autocomplete="off"></div>
<button class="btn btn-ink" type="submit">Calculate</button>
<div class="calc-out" role="status" aria-live="polite"></div>
<p style="margin:14px 0 0"><a id="calc-link" href="/states/alabama">Open the Alabama page</a></p>
</form>
<h2>The states</h2>
<ul class="state-dir">{''.join(links)}</ul>
<h2>Questions</h2>
<div class="faq">{faq_html}</div>
</div>
</main>
{foot}
<script src="/payments.js"></script>
<script src="/probate-calc.js"></script>
<script src="/motion.js"></script>
</body>
</html>
'''


CALC_JS = r'''
(function () {
  function money(n) {
    return n.toLocaleString("en-US", {style: "currency", currency: "USD"});
  }
  function marginal(value, brackets, aboveRate) {
    var fee = 0, prev = 0, i, cap, slice;
    for (i = 0; i < brackets.length; i++) {
      cap = brackets[i].upTo;
      slice = Math.min(value, cap) - prev;
      if (slice > 0) fee += slice * brackets[i].rate;
      prev = cap;
      if (value <= cap) return {fee: fee, partial: false};
    }
    if (value > prev) {
      if (aboveRate == null) return {fee: fee, partial: true, prev: prev};
      fee += (value - prev) * aboveRate;
    }
    return {fee: fee, partial: false};
  }
  function flAttorney(v) {
    var fee = v <= 40000 ? 1500 : v <= 70000 ? 2250 : 3000;
    if (v <= 100000) return {fee: fee, partial: false};
    var steps = [[1000000, 0.03], [3000000, 0.025], [5000000, 0.02], [10000000, 0.015]];
    var prev = 100000, i, cap, slice;
    fee = 3000;
    for (i = 0; i < steps.length; i++) {
      cap = steps[i][0];
      slice = Math.min(v, cap) - prev;
      if (slice > 0) fee += slice * steps[i][1];
      prev = cap;
      if (v <= cap) return {fee: fee, partial: false};
    }
    fee += (v - prev) * 0.01;
    return {fee: fee, partial: false};
  }
  function runFormula(value, f) {
    if (f.kind === "fl-atty") return flAttorney(value);
    return marginal(value, f.brackets || [], f.aboveRate);
  }
  function render(form, slug, value) {
    var data = (window.PROBATE_CALC || {})[slug] || {};
    var out = form.querySelector(".calc-out");
    var lines = [];
    if (!(value >= 0)) {
      out.innerHTML = "<p>Enter an amount of zero or more.</p>";
      return;
    }
    (data.formulas || []).forEach(function (f) {
      var result = runFormula(value, f);
      var text = "<p><span class=\"k\" style=\"font:500 12px/1.2 var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted)\">" + f.label + "</span><strong>" + money(result.fee) + "</strong></p>";
      text += "<p>" + f.base + ".</p>";
      if (result.partial) text += "<p>Above " + money(result.prev) + ", the statute does not set a percentage. That part is not in this figure.</p>";
      if (f.aboveNote) text += "<p>" + f.aboveNote + "</p>";
      lines.push(text);
    });
    if (!data.formulas || !data.formulas.length) {
      lines.push("<p><strong>No percentage to multiply.</strong></p><p>The sources on this page do not give a single statutory percentage of one estate value.</p>");
    }
    if (typeof data.limit === "number") {
      var side = value <= data.limit ? "at or under" : "over";
      lines.push("<p>That amount is " + side + " the " + money(data.limit) + " figure on this page. The statute still has conditions. The number alone does not decide the procedure.</p>");
    }
    out.innerHTML = lines.join("");
  }
  document.querySelectorAll("form.calc").forEach(function (form) {
    var select = form.querySelector("select");
    function slug() {
      return select ? select.value : form.getAttribute("data-state");
    }
    function go(event) {
      if (event) event.preventDefault();
      var input = form.querySelector("input");
      var raw = (input.value || "").replace(/[^0-9.]/g, "");
      render(form, slug(), raw === "" ? NaN : Number(raw));
      var link = document.getElementById("calc-link");
      if (link && select) {
        var label = select.options[select.selectedIndex].text;
        link.href = "/states/" + select.value;
        link.textContent = "Open the " + label + " page";
      }
    }
    form.addEventListener("submit", go);
    if (select) select.addEventListener("change", go);
  });
})();
'''


def sitemap(urls):
    core = [
        "https://taxfreetrusts.com/",
        "https://taxfreetrusts.com/pricing",
        "https://taxfreetrusts.com/start",
        "https://taxfreetrusts.com/learn-living-trust",
        "https://taxfreetrusts.com/learn-fund",
        "https://taxfreetrusts.com/learn-taxes",
        "https://taxfreetrusts.com/about",
        "https://taxfreetrusts.com/support",
        "https://taxfreetrusts.com/privacy",
        "https://taxfreetrusts.com/terms",
        "https://taxfreetrusts.com/states",
    ]
    locs = core + urls
    body = "\n".join(f"  <url><loc>{u}</loc></url>" for u in locs)
    text = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "\n</urlset>\n"
    if "llms.txt" in text or "trusts.json" in text or ".html" in text:
        raise SystemExit("sitemap still has a redirecting or excluded URL")
    (ROOT / "sitemap.xml").write_text(text)


def main():
    rows = load_rows()
    missing = [slug for _, slug in ORDER if slug not in rows]
    if missing:
        raise SystemExit("missing states: " + ", ".join(missing))
    OUT.mkdir(exist_ok=True)
    calc = {}
    gap_report = {}
    state_urls = []
    for name, slug in ORDER:
        row = rows[slug]
        row["name"] = name
        row["slug"] = slug
        html_text, forms, gaps = page_for(row)
        if "\u2014" in html_text or "\u2013" in html_text:
            raise SystemExit("dash in " + slug)
        if re.search(r"\bhonest\b", html_text, re.I) or "Jeff" in html_text:
            raise SystemExit("banned word in " + slug)
        (OUT / f"{slug}.html").write_text(html_text)
        calc[slug] = {
            "name": name,
            "limit": row.get("smallEstateLimit") if isinstance(row.get("smallEstateLimit"), (int, float)) else None,
            "formulas": forms,
        }
        if gaps:
            gap_report[name] = gaps
        state_urls.append(f"https://taxfreetrusts.com/states/{slug}")
    hub_html = hub(rows)
    (OUT / "index.html").write_text(hub_html)
    js = "window.PROBATE_CALC = " + json.dumps(calc, ensure_ascii=True) + ";\n" + CALC_JS
    (ROOT / "probate-calc.js").write_text(js)
    sitemap(state_urls)
    (ROOT / "data" / "gaps.json").write_text(json.dumps(gap_report, indent=2) + "\n")
    print(f"pages {len(ORDER)} gaps {len(gap_report)}")
    for name, gaps in gap_report.items():
        print(f"  {name}: {', '.join(gaps)}")


if __name__ == "__main__":
    main()
