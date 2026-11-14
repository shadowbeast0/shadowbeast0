"""Draw neon GitHub stat cards for the profile README.

Replaces the public github-readme-stats / activity-graph servers (which were shut down)
with cards rendered from GitHub's own GraphQL API. Runs daily in GitHub Actions.

Usage:  GH_TOKEN=... python scripts/cards.py shadowbeast0
Writes: cards/stats.svg, cards/streak.svg, cards/langs.svg
"""
import datetime as dt
import json
import os
import sys
import urllib.request
from html import escape

LOGIN = sys.argv[1] if len(sys.argv) > 1 else "shadowbeast0"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
OUT = os.path.join(os.path.dirname(__file__), "..", "cards")

# languages that are markup/config rather than code
IGNORED = {"HTML", "CSS", "TeX", "Makefile", "CMake", "Shell", "Dockerfile", "QMake", "Lex", "Gnuplot", "Less", "SCSS", "Batchfile", "PowerShell"}

QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    followers { totalCount }
    pullRequests { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100, orderBy: {field: STARGAZERS, direction: DESC}) {
      totalCount
      nodes {
        stargazerCount
        forkCount
        languages(first: 12, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } }
      }
    }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date } }
      }
    }
  }
}
"""


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": "profile-cards"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(f"GraphQL error: {data['errors']}")
    return data["data"]["user"]


def streaks(days):
    """Current and longest daily streaks from the contribution calendar (today may still be empty)."""
    counts = [d["contributionCount"] for d in days]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    cur, i = 0, len(counts) - 1
    if i >= 0 and counts[i] == 0:
        i -= 1  # don't break the streak just because today isn't over
    while i >= 0 and counts[i]:
        cur += 1
        i -= 1
    return cur, longest


def fmt(n):
    return f"{n / 1000:.1f}k" if n >= 1000 else str(n)


# ---------- shared look: dark panel, neon frame, manga speed lines ----------
FONT = "'Segoe UI Black','Arial Black','Segoe UI',Ubuntu,'Helvetica Neue',sans-serif"
MONO = "'Cascadia Code','Fira Code',Consolas,'SF Mono',monospace"


def frame(w, h, title, kanji, body, accent="#FF2E88"):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#140A26"/><stop offset="1" stop-color="#07040F"/></linearGradient>
  <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{accent}"/><stop offset=".5" stop-color="#8B5CF6"/><stop offset="1" stop-color="#22F0FF"/></linearGradient>
  <filter id="glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="2.4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <pattern id="dots" width="6" height="6" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r=".8" fill="#ffffff" opacity=".05"/></pattern>
</defs>
<style>
  .t{{font:900 italic 19px {FONT};letter-spacing:1.5px;fill:#fff}}
  .k{{font:900 64px 'Yu Gothic','Noto Sans JP','Hiragino Sans',sans-serif;fill:none;stroke:#8B5CF6;stroke-opacity:.28;stroke-width:1.4}}
  .l{{font:600 12.5px {MONO};fill:#B8AEDC}}
  .v{{font:900 italic 18px {FONT};fill:#fff}}
  .s{{font:600 11px {MONO};fill:#7E74A6}}
  .grow{{animation:grow 1.4s cubic-bezier(.2,.9,.2,1) both}}
  .fade{{animation:fade .8s ease-out both}}
  .pulse{{animation:pulse 2.4s ease-in-out infinite}}
  .scan{{animation:scan 4s linear infinite}}
  @keyframes grow{{from{{transform:scaleX(0)}}}}
  @keyframes fade{{from{{opacity:0;transform:translateY(6px)}}}}
  @keyframes pulse{{50%{{opacity:.45}}}}
  @keyframes scan{{from{{transform:translateX(-{w}px)}}to{{transform:translateX({w}px)}}}}
</style>
<rect x="2" y="2" width="{w - 4}" height="{h - 4}" rx="14" fill="url(#bg)"/>
<rect x="2" y="2" width="{w - 4}" height="{h - 4}" rx="14" fill="url(#dots)"/>
<rect class="scan" x="0" y="2" width="70" height="{h - 4}" fill="#fff" opacity=".035"/>
<text class="k" x="{w - 78}" y="70">{kanji}</text>
<rect x="2" y="2" width="{w - 4}" height="{h - 4}" rx="14" fill="none" stroke="url(#edge)" stroke-width="2.5" filter="url(#glow)"/>
<text class="t" x="24" y="38">{escape(title)}</text>
<rect x="24" y="46" width="64" height="3" rx="1.5" fill="{accent}" filter="url(#glow)"/>
{body}
</svg>"""


def stats_card(u):
    repos = u["repositories"]["nodes"]
    cc = u["contributionsCollection"]
    rows = [
        ("★", "Total stars", sum(r["stargazerCount"] for r in repos), "#FFD60A"),
        ("⟳", "Commits (past year)", cc["totalCommitContributions"] + cc["restrictedContributionsCount"], "#FF2E88"),
        ("⇄", "Pull requests", u["pullRequests"]["totalCount"], "#22F0FF"),
        ("▣", "Public repos", u["repositories"]["totalCount"], "#8B5CF6"),
        ("◉", "Followers", u["followers"]["totalCount"], "#7ED957"),
    ]
    top = max(v for _, _, v, _ in rows) or 1
    body = ""
    for i, (icon, label, val, col) in enumerate(rows):
        y = 78 + i * 26
        width = max(6, 150 * val / top)
        body += f"""<g class="fade" style="animation-delay:{i * 0.12:.2f}s">
  <text x="24" y="{y}" font-size="15" fill="{col}" filter="url(#glow)">{icon}</text>
  <text class="l" x="46" y="{y}">{escape(label)}</text>
  <rect x="236" y="{y - 10}" width="150" height="10" rx="5" fill="#ffffff" opacity=".07"/>
  <rect class="grow" style="transform-origin:236px 0;animation-delay:{0.3 + i * 0.12:.2f}s" x="236" y="{y - 10}" width="{width:.1f}" height="10" rx="5" fill="{col}" filter="url(#glow)"/>
  <text class="v" x="470" y="{y + 1}" text-anchor="end">{fmt(val)}</text>
</g>"""
    return frame(495, 215, "POWER LEVELS", "力", body)


def streak_card(u):
    cal = u["contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    cur, longest = streaks(days)
    first = dt.date.fromisoformat(days[0]["date"]).strftime("%b %Y") if days else ""
    cols = [
        (f"{fmt(cal['totalContributions'])}", "Contributions", f"since {first}", "#22F0FF"),
        (str(cur), "Current streak", "days in a row", "#FF2E88"),
        (str(longest), "Longest streak", "days, past year", "#FFD60A"),
    ]
    body = ""
    for i, (v, l, s, col) in enumerate(cols):
        cx = 92 + i * 156
        ring = f'<circle cx="{cx}" cy="122" r="40" fill="none" stroke="{col}" stroke-opacity=".18" stroke-width="7"/>'
        ring += f'<circle class="pulse" cx="{cx}" cy="122" r="40" fill="none" stroke="{col}" stroke-width="3.5" stroke-dasharray="190 62" transform="rotate(-90 {cx} 122)" filter="url(#glow)"/>'
        flame = f'<text x="{cx}" y="76" text-anchor="middle" font-size="18" class="pulse">🔥</text>' if i == 1 else ""
        body += f"""<g class="fade" style="animation-delay:{i * 0.15:.2f}s">{ring}{flame}
  <text x="{cx}" y="131" text-anchor="middle" font-weight="900" font-style="italic" font-size="26" fill="#fff" font-family="{FONT}">{v}</text>
  <text class="l" x="{cx}" y="186" text-anchor="middle" fill="{col}">{l}</text>
  <text class="s" x="{cx}" y="203" text-anchor="middle">{s}</text>
</g>"""
    return frame(495, 215, "STREAK", "炎", body, accent="#22F0FF")


def langs_card(u):
    sizes, colors = {}, {}
    for r in u["repositories"]["nodes"]:
        for e in r["languages"]["edges"]:
            n = e["node"]["name"]
            if n in IGNORED:
                continue
            # square root keeps huge notebook/output files from drowning out everything else
            sizes[n] = sizes.get(n, 0) + e["size"] ** 0.5
            colors[n] = e["node"]["color"] or "#8B5CF6"
    total = sum(sizes.values()) or 1
    top = sorted(sizes.items(), key=lambda kv: -kv[1])[:6]
    body, x = "", 24
    # one stacked neon bar across the top
    for n, s in top:
        w = 447 * s / total
        body += f'<rect class="grow" style="transform-origin:24px 0" x="{x:.1f}" y="64" width="{max(w, 2):.1f}" height="12" fill="{colors[n]}"/>'
        x += w
    body = f'<g filter="url(#glow)"><clipPath id="bar"><rect x="24" y="64" width="447" height="12" rx="6"/></clipPath><g clip-path="url(#bar)">{body}</g></g>'
    for i, (n, s) in enumerate(top):
        col, row = i % 2, i // 2
        bx, by = 24 + col * 230, 108 + row * 34
        body += f"""<g class="fade" style="animation-delay:{0.4 + i * 0.1:.2f}s">
  <circle cx="{bx + 7}" cy="{by - 4}" r="6" fill="{colors[n]}" filter="url(#glow)"/>
  <text class="l" x="{bx + 22}" y="{by}" fill="#E9E4FF">{escape(n)}</text>
  <text class="s" x="{bx + 210}" y="{by}" text-anchor="end">{100 * s / total:.1f}%</text>
</g>"""
    return frame(495, 215, "LANGUAGE LOADOUT", "術", body, accent="#8B5CF6")


def main():
    if not TOKEN:
        raise SystemExit("Set GH_TOKEN (or GITHUB_TOKEN) to read GitHub's GraphQL API.")
    u = fetch()
    os.makedirs(OUT, exist_ok=True)
    for name, svg in (("stats", stats_card(u)), ("streak", streak_card(u)), ("langs", langs_card(u))):
        with open(os.path.join(OUT, f"{name}.svg"), "w", encoding="utf-8") as f:
            f.write(svg)
        print("wrote", name)


if __name__ == "__main__":
    main()
