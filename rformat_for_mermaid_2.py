import os
import re
import html


MERMAID_KEYWORDS = (
    "graph",
    "flowchart",
    "classDiagram",
    "sequenceDiagram",
    "stateDiagram",
    "erDiagram",
    "gantt",
    "pie"
)


def process_html(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # --------------------------------------------------
    # 1. Inserimento Mermaid nel <head> (una sola volta)
    # --------------------------------------------------
    if "mermaid.esm.min.mjs" not in content:
        mermaid_script = """
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";
  mermaid.initialize({
    startOnLoad: true,
    theme: "default"
  });
</script>
"""
        content = re.sub(
            r"(</head>)",
            mermaid_script + r"\1",
            content,
            flags=re.IGNORECASE
        )

    # --------------------------------------------------
    # 2. Conversione sicura blocchi Mermaid
    # --------------------------------------------------
def replace_mermaid(match):
    raw = match.group(1)

    raw = raw.replace("<br>", "\n").replace("<br/>", "\n")
    decoded = html.unescape(raw)
    decoded = decoded.replace("\u00a0", " ")

    lines = [line.rstrip() for line in decoded.splitlines()]

    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    if len(lines) < 2:
        return match.group(0)

    first = lines[0].strip()
    if not first.startswith(MERMAID_KEYWORDS):
        return match.group(0)

    cleaned = "\n".join(lines)
    return f'<div class="mermaid">\n{cleaned}\n</div>'




    content = re.sub(
        r'<pre[^>]*>\s*<code class="language-mermaid"[^>]*>(.*?)</code>\s*</pre>',
        replace_mermaid,
        content,
        flags=re.DOTALL | re.IGNORECASE
    )

    # --------------------------------------------------
    # 3. Scrittura file di output
    # --------------------------------------------------
    new_path = file_path.replace(".html", "_with_mermaid.html")
    with open(new_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✔ File generato: {new_path}")


def process_all_html_files():
    for name in os.listdir():
        if name.endswith(".html") and not name.endswith("_with_mermaid.html"):
            print(f"Elaborazione: {name}")
            process_html(name)


if __name__ == "__main__":
    process_all_html_files()
