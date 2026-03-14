"""
mermaid_converter.py
Converte i blocchi <pre><code class="language-Mermaid"> presenti in un file HTML
in elementi <div class="mermaid"> renderizzabili dalla libreria Mermaid.js.
"""

import os
import re
import html
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


# ---------------------------------------------------------------------------
# Costanti
# ---------------------------------------------------------------------------

MERMAID_KEYWORDS = (
    "graph",
    "flowchart",
    "classDiagram",
    "sequenceDiagram",
    "stateDiagram",
    "erDiagram",
    "gantt",
    "pie",
    "mindmap",
    "timeline",
    "gitGraph",
    "quadrantChart",
    "requirementDiagram",
    "C4Context",
)

MERMAID_SCRIPT = """\
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";
  mermaid.initialize({ startOnLoad: true, theme: "default" });
</script>
"""

# ---------------------------------------------------------------------------
# Logica di conversione
# ---------------------------------------------------------------------------

def replace_mermaid(match: re.Match) -> str:
    """
    Riceve il contenuto grezzo di un blocco <code class="language-Mermaid">
    e restituisce il corrispondente <div class="mermaid">.
    In caso di contenuto non riconoscibile come diagramma Mermaid valido
    restituisce il blocco originale invariato.
    """
    raw: str = match.group(1)

    # Normalizzazione a-capo codificati come tag HTML
    raw = raw.replace("<br/>", "\n").replace("<br>", "\n")

    # Decodifica entità HTML (&lt; → <, &gt; → >, &amp; → & ecc.)
    decoded: str = html.unescape(raw)

    # Rimozione di spazi non-breaking (U+00A0) residui
    decoded = decoded.replace("\u00a0", " ")

    # Pulizia righe e rimozione righe vuote iniziali/finali
    lines = [line.rstrip() for line in decoded.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    if len(lines) < 2:
        return match.group(0)

    # Verifica che la prima riga non vuota sia un keyword Mermaid valido
    first = lines[0].strip()
    if not first.startswith(MERMAID_KEYWORDS):
        return match.group(0)

    cleaned = "\n".join(lines)
    return f'<div class="mermaid">\n{cleaned}\n</div>'


def process_html(input_path: str, output_path: str) -> int:
    """
    Elabora il file HTML indicato da input_path e scrive il risultato
    in output_path. Restituisce il numero di blocchi Mermaid convertiti.
    """
    with open(input_path, "r", encoding="utf-8") as fh:
        content = fh.read()

    # 1. Inserimento dello script Mermaid nel <head> (una sola volta)
    if "mermaid.esm.min.mjs" not in content:
        content = re.sub(
            r"(</head>)",
            MERMAID_SCRIPT + r"\1",
            content,
            count=1,
            flags=re.IGNORECASE,
        )

    # 2. Sostituzione blocchi <pre><code class="language-Mermaid|mermaid">
    #    Il flag IGNORECASE gestisce sia "Mermaid" sia "mermaid".
    pattern = (
        r'<pre[^>]*>\s*'
        r'<code[^>]*class="language-[Mm]ermaid"[^>]*>'
        r'(.*?)'
        r'</code>\s*</pre>'
    )

    counter = [0]  # lista mutabile per aggirare la closure su int

    def counting_replace(m: re.Match) -> str:
        result = replace_mermaid(m)
        if result != m.group(0):
            counter[0] += 1
        return result

    content = re.sub(
        pattern,
        counting_replace,
        content,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # 3. Scrittura del file di output
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(content)

    return counter[0]


# ---------------------------------------------------------------------------
# Interfaccia grafica (tkinter)
# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mermaid HTML Converter")
        self.resizable(False, False)
        self._build_ui()

    # ------------------------------------------------------------------
    # Costruzione widget
    # ------------------------------------------------------------------

    def _build_ui(self):
        PAD = {"padx": 10, "pady": 6}

        # --- File di input ---
        frm_in = ttk.LabelFrame(self, text="File HTML di input", padding=8)
        frm_in.grid(row=0, column=0, sticky="ew", **PAD)

        self.var_input = tk.StringVar()
        ttk.Entry(frm_in, textvariable=self.var_input, width=54).grid(
            row=0, column=0, padx=(0, 6)
        )
        ttk.Button(frm_in, text="Sfoglia…", command=self._browse_input).grid(
            row=0, column=1
        )

        # --- File di output ---
        frm_out = ttk.LabelFrame(self, text="File HTML di output", padding=8)
        frm_out.grid(row=1, column=0, sticky="ew", **PAD)

        self.var_output = tk.StringVar()
        ttk.Entry(frm_out, textvariable=self.var_output, width=54).grid(
            row=0, column=0, padx=(0, 6)
        )
        ttk.Button(frm_out, text="Sfoglia…", command=self._browse_output).grid(
            row=0, column=1
        )

        # --- Barra di avanzamento + pulsante ---
        frm_ctrl = ttk.Frame(self, padding=(10, 4))
        frm_ctrl.grid(row=2, column=0, sticky="ew")

        self.progress = ttk.Progressbar(frm_ctrl, mode="indeterminate", length=320)
        self.progress.grid(row=0, column=0, padx=(0, 10))

        ttk.Button(
            frm_ctrl, text="▶  Converti", command=self._run, width=14
        ).grid(row=0, column=1)

        # --- Etichetta di stato ---
        self.var_status = tk.StringVar(value="In attesa di un file da elaborare.")
        ttk.Label(
            self, textvariable=self.var_status, foreground="#555"
        ).grid(row=3, column=0, sticky="w", padx=10, pady=(2, 10))

    # ------------------------------------------------------------------
    # Callback
    # ------------------------------------------------------------------

    def _browse_input(self):
        path = filedialog.askopenfilename(
            title="Seleziona file HTML",
            filetypes=[("File HTML", "*.html *.htm"), ("Tutti i file", "*.*")],
        )
        if not path:
            return
        self.var_input.set(path)

        # Propone automaticamente un nome per l'output
        base, ext = os.path.splitext(path)
        self.var_output.set(f"{base}_with_mermaid{ext}")
        self.var_status.set("File selezionato. Pronto per la conversione.")

    def _browse_output(self):
        initial = self.var_output.get() or self.var_input.get()
        path = filedialog.asksaveasfilename(
            title="Salva file HTML convertito",
            initialfile=os.path.basename(initial),
            defaultextension=".html",
            filetypes=[("File HTML", "*.html *.htm"), ("Tutti i file", "*.*")],
        )
        if path:
            self.var_output.set(path)

    def _run(self):
        input_path = self.var_input.get().strip()
        output_path = self.var_output.get().strip()

        # Validazione
        if not input_path:
            messagebox.showwarning("Attenzione", "Selezionare prima un file di input.")
            return
        if not os.path.isfile(input_path):
            messagebox.showerror("Errore", f"Il file non esiste:\n{input_path}")
            return
        if not output_path:
            messagebox.showwarning("Attenzione", "Specificare il percorso del file di output.")
            return

        self.progress.start(12)
        self.var_status.set("Elaborazione in corso…")
        self.update_idletasks()

        try:
            n = process_html(input_path, output_path)
            self.var_status.set(
                f"✔ Completato: {n} blocco/i Mermaid convertito/i  →  {os.path.basename(output_path)}"
            )
            messagebox.showinfo(
                "Conversione completata",
                f"Blocchi Mermaid convertiti: {n}\n\nFile salvato in:\n{output_path}",
            )
        except Exception as exc:
            self.var_status.set(f"✖ Errore: {exc}")
            messagebox.showerror("Errore durante l'elaborazione", str(exc))
        finally:
            self.progress.stop()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = App()
    app.mainloop()