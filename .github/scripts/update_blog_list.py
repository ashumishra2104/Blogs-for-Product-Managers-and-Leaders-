"""
update_blog_list.py
-------------------
Reads all .md blog files from this repo (sorted by most recent git commit),
takes the top 7, and rewrites the BLOG-LIST section in ashumishra2104's
profile README between the comment markers:

    <!-- BLOG-LIST:START -->
    ...table rows...
    <!-- BLOG-LIST:END -->

Requires secret: PROFILE_REPO_TOKEN  (a fine-grained or classic PAT with
`repo` scope on the ashumishra2104/ashumishra2104 repo)
"""

import os
import re
import subprocess
import base64
import requests

# ── Config ────────────────────────────────────────────────────────────────────
PROFILE_OWNER = "ashumishra2104"
PROFILE_REPO  = "ashumishra2104"
BLOG_OWNER    = "ashumishra2104"
BLOG_REPO     = "Blogs-for-Product-Managers-and-Leaders-"
BLOG_BRANCH   = "main"
MAX_BLOGS     = 7
TOKEN         = os.environ["PROFILE_REPO_TOKEN"]

API_BASE      = "https://api.github.com"
HEADERS       = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_md_files_sorted_by_commit():
    """Return list of (filename, commit_date) tuples sorted newest-first."""
    # git log gives us each file's last-commit date
    result = subprocess.run(
        ["git", "log", "--name-only", "--pretty=format:%ci", "--diff-filter=A", BLOG_BRANCH],
        capture_output=True, text=True, check=True
    )
    lines = result.stdout.strip().split("\n")

    file_dates = {}   # filename -> first appearance date (= when it was added)
    current_date = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Lines with a date look like: 2026-03-26 17:00:00 +0000
        if re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", line):
            current_date = line
        elif line.endswith(".md") and line != "README.md":
            if line not in file_dates:   # Keep first occurrence = newest add
                file_dates[line] = current_date

    # Sort by date descending
    sorted_files = sorted(file_dates.items(), key=lambda x: x[1], reverse=True)
    return sorted_files


def filename_to_title(filename):
    """Convert snake_case filename to a readable Title."""
    name = filename.replace(".md", "")
    # Replace underscores/hyphens with spaces, title-case each word
    words = re.split(r"[_\-]+", name)
    # Preserve short connectors in lower-case
    connectors = {"a", "an", "the", "of", "in", "for", "and", "or", "to",
                  "vs", "vs.", "from", "with", "at", "by", "on", "is",
                  "what", "how", "when", "why", "who"}
    titled = []
    for i, w in enumerate(words):
        if i == 0 or w.lower() not in connectors:
            titled.append(w.capitalize())
        else:
            titled.append(w.lower())
    return " ".join(titled)


THEME_MAP = {
    "ai_in_the_last_7_days": "AI News & PM Strategy",
    "coding_for_pms":        "Technical Skills for PMs",
    "from_transistors":      "Computing History & Strategy",
    "india_vs_pakistan":     "System Design",
    "llm_evals":             "AI Evaluation",
    "sql_vs_nosql":          "Data Architecture",
    "attention_mechanisms":  "AI/ML Fundamentals",
}

def guess_theme(filename):
    """Heuristically assign a theme tag from the filename."""
    f = filename.lower()
    for key, theme in THEME_MAP.items():
        if key in f:
            return theme
    # Generic fallback
    if "agent" in f or "llm" in f or "gpt" in f or "ai" in f:
        return "AI / ML"
    if "pm" in f or "product" in f or "manager" in f:
        return "PM Strategy"
    if "data" in f or "sql" in f or "database" in f:
        return "Data & Infrastructure"
    return "Product Management"


def build_blog_table(sorted_files):
    """Build the markdown table rows for top MAX_BLOGS files."""
    top = sorted_files[:MAX_BLOGS]
    rows = []
    rows.append("| \U0001f5d3\ufe0f | Title | Theme |")
    rows.append("|----|-------|-------|")
    for i, (fname, _) in enumerate(top):
        icon  = "\U0001f195" if i == 0 else "\U0001f4cc"
        title = filename_to_title(fname)
        theme = guess_theme(fname)
        url   = (
            f"https://github.com/{BLOG_OWNER}/{BLOG_REPO}"
            f"/blob/{BLOG_BRANCH}/{fname}"
        )
        rows.append(f"| {icon} | [**{title}**]({url}) | {theme} |")
    return "\n".join(rows)


def update_profile_readme(new_table):
    """Fetch, patch, and push the profile README."""
    url = f"{API_BASE}/repos/{PROFILE_OWNER}/{PROFILE_REPO}/contents/README.md"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()
    sha = data["sha"]
    content = base64.b64decode(data["content"]).decode("utf-8")

    # Replace between markers
    pattern = r"(<!-- BLOG-LIST:START -->).*?(<!-- BLOG-LIST:END -->)"
    replacement = f"<!-- BLOG-LIST:START -->\n{new_table}\n<!-- BLOG-LIST:END -->"
    new_content, count = re.subn(pattern, replacement, content, flags=re.DOTALL)

    if count == 0:
        print("ERROR: BLOG-LIST markers not found in profile README!")
        raise SystemExit(1)

    if new_content == content:
        print("No changes needed — blog list is already up to date.")
        return

    encoded = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")
    payload = {
        "message": "\U0001f916 Auto-update: refresh recent blogs list",
        "content": encoded,
        "sha": sha,
        "branch": "main",
    }
    put_resp = requests.put(url, headers=HEADERS, json=payload)
    put_resp.raise_for_status()
    print(f"\u2705 Profile README updated with {MAX_BLOGS} latest blogs.")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Fetching sorted blog file list...")
    sorted_files = get_md_files_sorted_by_commit()
    print(f"Found {len(sorted_files)} blog files.")
    for f, d in sorted_files[:MAX_BLOGS]:
        print(f"  {d}  {f}")

    table = build_blog_table(sorted_files)
    print("\nGenerated table:")
    print(table)

    update_profile_readme(table)
