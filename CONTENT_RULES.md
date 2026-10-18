# Content rules for TaxFreeTrusts

Saved 2026-10-17. Every agent, script, or person who adds or edits a page on this site follows these rules. They come from Nicholas Dulait's "Claude is killing your SEO" checklist, adapted to Hanok's privacy and copy rules.

## Every new page

1. **Byline and author box.** Show the byline "TaxFreeTrusts" near the top and an author box at the end that links to [/about/](/about/). The box says what the desk does using facts already on the site. No headshot or personal name unless this file says so.
2. **Schema.** Organization schema stays sitewide. Each article or guide carries `Article` (or `BlogPosting`) JSON-LD with `author` = Organization "TaxFreeTrusts" (url /about), `publisher` = Organization "TaxFreeTrusts", `datePublished`, and `dateModified`.
3. **Three related links.** Link at least 3 existing pages on the same topic with descriptive anchor text (the anchor names the page's subject, never "click here" or "read more"). Link only to URLs that return 200 today.
4. **Two-question test.** Before publishing, answer both in the PR description: would a searcher who landed here from Google actually read it, and is it more useful than the 9 other results on that query? If either answer is no, improve the page or skip it. Skipping is a success.

## Lists, comparisons, and "best" pages

5. **Never rank ourselves first.** Order every best, top, comparison, or alternatives list by the criteria stated on the page. Our own site, product, or any company in the same owner network (including Cornerstone and its partners) goes where those criteria put it, with a one-line ownership note, or stays off the list.
6. **Praise comes from others.** Do not call our own product the best or the top pick on this site.

## Pace and place pages

7. **Pace.** Until Google Search Console shows clicks on this site, add no more than 3 to 4 new pages per week. Refreshing an existing URL is better than a new slug.
8. **No fill-in-the-blank place pages.** A state or city page ships only when it carries facts specific to that place (a cited fee, statute, agency, dataset, or local listing). If the only difference is the place name, update the hub page instead.

## Privacy (hard rules)

9. Never show Jeff's location: no city, state, ZIP, street, or region tied to him, in copy, meta, schema, alt text, llms.txt, or comments.
10. Do not name Jeff on this site. A non-identifying description of who runs the desk is fine only when that fact is already on the site.
11. Contact and legal pages show the brand name and the site's existing contact email or form. No physical address. Never invent a mailbox.

## Copy

12. Write in Jeff's voice and lead with the answer. No em dashes or en dashes. No "honest" or "honestly" framing. No caveat blocks or "what this is not" sections; state a limitation in one line only when it is essential.
13. Never invent a fact, number, rating, review count, or result. If a figure is not on a public page we can link, leave it out.
14. **Education only.** Guides are not legal advice; keep the existing one-line note. Dollar figures come from the statute, IRS page, or court site linked beside them.
15. **State pages.** `tools/build_states.py` generates states/. Edit the generator, not only the HTML.
