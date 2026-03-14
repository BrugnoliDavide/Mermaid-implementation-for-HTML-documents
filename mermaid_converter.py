"""
mermaid_converter.py  —  v3.0
Converte i blocchi <pre><code class="language-Mermaid"> di un file HTML
in <div class="mermaid"> renderizzabili da Mermaid.js v10.

Problemi di sintassi corretti automaticamente:
  A) __testo__       → testo$         (membro statico UML)
  B) %% dentro {}    → rimosso        (commento in class body)
  C) ......          → rimosso        (attributo solo punti)
  D) ...()           → rimosso        (metodo con nome solo punti)
  E) method() : Type → method() Type  (tipo ritorno con colon)
  F) Arrow : <vuoto> → Arrow          (relazione con colon finale)
  G) class 2         → class C_2      (nome classe inizia con cifra)
  H) note duplicata  → conservata prima occorrenza
  I) A <--o B        → A o-- B        (freccia combinata non standard)
  Z) righe vuote >1  → al massimo una
"""

import os
import re
import html as html_mod
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


# ---------------------------------------------------------------------------
# Costanti
# ---------------------------------------------------------------------------

MERMAID_KEYWORDS = (
    "graph", "flowchart", "classDiagram", "sequenceDiagram",
    "stateDiagram", "erDiagram", "gantt", "pie", "mindmap",
    "timeline", "gitGraph", "quadrantChart", "requirementDiagram", "C4Context",
)

MERMAID_SCRIPT = """\
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";
  mermaid.initialize({ startOnLoad: true, theme: "default" });
</script>
"""


# ---------------------------------------------------------------------------
# Sanitizzatore
# ---------------------------------------------------------------------------

def sanitize_mermaid(text: str) -> str:
    """
    Applica tutte le correzioni di sintassi necessarie per Mermaid v10.
    Vedere docstring del modulo per l'elenco completo (A–Z).
    """
    lines = text.splitlines()

    # ------------------------------------------------------------------
    # Passo 1 — fix dipendenti dalla posizione nel class body (A B C D)
    #
    # ATTENZIONE: i { e } dentro righe %% NON devono incrementare il
    # contatore depth (es: commenti con codice Java al loro interno).
    # ------------------------------------------------------------------
    result = []
    depth = 0
    for line in lines:
        stripped = line.strip()
        is_comment = stripped.startswith('%%')

        # Aggiorna depth solo su righe che non sono commenti
        if not is_comment:
            depth += stripped.count('{') - stripped.count('}')

        in_body = depth > 0

        # A) __testo__ → testo$  (notazione sottolineato/statico UML)
        if stripped.startswith("__") and stripped.endswith("__") and len(stripped) > 4:
            inner = stripped[2:-2].strip()
            inner = re.sub(r'^([+\-#~]?\s*)(\w+)', r'\1\2$', inner)
            indent = len(line) - len(line.lstrip())
            line = " " * indent + inner
            stripped = line.strip()

        if in_body:
            # B) commento %% dentro il corpo di una classe
            if is_comment:
                continue
            # C) attributo composto solo da punti (es: "......")
            if re.match(r'^[.]+$', stripped):
                continue
            # D) metodo il cui nome è solo punti (es: "....()")
            if re.match(r'^[+\-#~]?\s*\.+\s*\(', stripped):
                continue

        result.append(line)
    lines = result

    # ------------------------------------------------------------------
    # Passo 2 — fix per singola riga (E F I)
    # ------------------------------------------------------------------
    result = []
    for line in lines:
        # E) tipo di ritorno con ':' → senza ':'
        #    Pattern: MatchGroup(metodo con ()) seguito da ' : TipoMaiuscolo'
        #    Il gruppo [^)]* garantisce di non toccare i ':' dentro i parametri.
        line = re.sub(
            r'(\w+\s*\([^)]*\))\s*:\s*([A-Z]\w*)',
            r'\1 \2',
            line
        )

        # F) ':' finale senza label su righe di relazione
        #    Una riga di relazione Mermaid contiene sempre '--' oppure '..'
        if re.search(r'(?:--|\.\.)', line):
            line = re.sub(r'(\b\w+\b)\s*:\s*$', r'\1', line)

        # I) frecce combinate non standard
        #    "A <--o B" → "A o-- B"   (scambia lati, mantiene il diamante)
        #    "A <--* B" → "A *-- B"
        line = re.sub(
            r'(\b\w+\b)\s+<--([o*])\s+(\b\w+\b)',
            lambda m: f'{m.group(1)} {m.group(2)}-- {m.group(3)}',
            line
        )

        result.append(line)
    lines = result

    # ------------------------------------------------------------------
    # Passo 3 — nomi classe che iniziano con cifra (G)
    # ------------------------------------------------------------------
    text_tmp = "\n".join(lines)
    invalid_names = list(dict.fromkeys(
        re.findall(r'\bclass\s+(\d\w*)\b', text_tmp)
    ))
    for old in invalid_names:
        text_tmp = re.sub(r'\b' + re.escape(old) + r'\b', 'C_' + old, text_tmp)
    lines = text_tmp.splitlines()

    # ------------------------------------------------------------------
    # Passo 4 — note duplicate sullo stesso nodo (H)
    # ------------------------------------------------------------------
    seen_notes: set = set()
    result = []
    for line in lines:
        m = re.match(r'\s*note\s+for\s+(\S+)', line, re.IGNORECASE)
        if m:
            key = m.group(1).lower().strip('"')
            if key in seen_notes:
                continue
            seen_notes.add(key)
        result.append(line)
    lines = result

    # ------------------------------------------------------------------
    # Passo 5 — righe vuote multiple → al massimo una (Z)
    # ------------------------------------------------------------------
    result, prev_empty = [], False
    for line in lines:
        is_empty = not line.strip()
        if is_empty and prev_empty:
            continue
        result.append(line)
        prev_empty = is_empty

    return "\n".join(result)


# ---------------------------------------------------------------------------
# Conversione blocchi
# ---------------------------------------------------------------------------

def replace_mermaid(match: re.Match) -> str:
    """
    Converte un blocco <pre><code class="language-Mermaid"> in
    <div class="mermaid">. Restituisce il blocco originale se il
    contenuto non è riconoscibile come diagramma Mermaid valido.
    """
    raw: str = match.group(1)
    raw = raw.replace("<br/>", "\n").replace("<br>", "\n")
    decoded: str = html_mod.unescape(raw).replace("\u00a0", " ")

    lines = [l.rstrip() for l in decoded.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    if len(lines) < 2:
        return match.group(0)

    if not lines[0].strip().startswith(MERMAID_KEYWORDS):
        return match.group(0)

    cleaned = sanitize_mermaid("\n".join(lines))
    return f'<div class="mermaid">\n{cleaned}\n</div>'


# ---------------------------------------------------------------------------
# Elaborazione file HTML
# ---------------------------------------------------------------------------

def process_html(input_path: str, output_path: str) -> int:
    """
    Elabora il file HTML in input_path e scrive il risultato in output_path.
    Restituisce il numero di blocchi Mermaid effettivamente convertiti.
    """
    with open(input_path, "r", encoding="utf-8") as fh:
        content = fh.read()

    # Inietta lo script Mermaid nel <head> (una sola volta)
    if "mermaid.esm.min.mjs" not in content:
        content = re.sub(
            r"(</head>)", MERMAID_SCRIPT + r"\1",
            content, count=1, flags=re.IGNORECASE
        )

    # Sostituisce tutti i blocchi <pre><code class="language-Mermaid|mermaid">
    pattern = (
        r'<pre[^>]*>\s*'
        r'<code[^>]*class="language-[Mm]ermaid"[^>]*>'
        r'(.*?)'
        r'</code>\s*</pre>'
    )
    counter = [0]

    def counting_replace(m: re.Match) -> str:
        r = replace_mermaid(m)
        if r != m.group(0):
            counter[0] += 1
        return r

    content = re.sub(
        pattern, counting_replace, content,
        flags=re.DOTALL | re.IGNORECASE
    )

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(content)

    return counter[0]


# ---------------------------------------------------------------------------
# Interfaccia grafica
# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mermaid HTML Converter  v3.0")
        self.resizable(False, False)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        PAD = {"padx": 10, "pady": 6}

        frm_in = ttk.LabelFrame(self, text="File HTML di input", padding=8)
        frm_in.grid(row=0, column=0, sticky="ew", **PAD)
        self.var_input = tk.StringVar()
        ttk.Entry(frm_in, textvariable=self.var_input, width=58).grid(
            row=0, column=0, padx=(0, 6))
        ttk.Button(frm_in, text="Sfoglia…",
                   command=self._browse_input).grid(row=0, column=1)

        frm_out = ttk.LabelFrame(self, text="File HTML di output", padding=8)
        frm_out.grid(row=1, column=0, sticky="ew", **PAD)
        self.var_output = tk.StringVar()
        ttk.Entry(frm_out, textvariable=self.var_output, width=58).grid(
            row=0, column=0, padx=(0, 6))
        ttk.Button(frm_out, text="Sfoglia…",
                   command=self._browse_output).grid(row=0, column=1)

        frm_log = ttk.LabelFrame(self, text="Log", padding=8)
        frm_log.grid(row=2, column=0, sticky="ew", **PAD)
        self.txt_log = tk.Text(
            frm_log, height=8, width=70, state="disabled",
            font=("Courier", 9), background="#f8f8f8"
        )
        self.txt_log.grid(row=0, column=0)
        sb = ttk.Scrollbar(frm_log, command=self.txt_log.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.txt_log.configure(yscrollcommand=sb.set)

        frm_ctrl = ttk.Frame(self, padding=(10, 4))
        frm_ctrl.grid(row=3, column=0, sticky="ew")
        self.progress = ttk.Progressbar(
            frm_ctrl, mode="indeterminate", length=340)
        self.progress.grid(row=0, column=0, padx=(0, 10))
        ttk.Button(frm_ctrl, text="▶  Converti",
                   command=self._run, width=14).grid(row=0, column=1)

        self.var_status = tk.StringVar(
            value="In attesa di un file da elaborare.")
        ttk.Label(self, textvariable=self.var_status,
                  foreground="#555").grid(
            row=4, column=0, sticky="w", padx=10, pady=(2, 10))

    # ------------------------------------------------------------------
    # Callback
    # ------------------------------------------------------------------
    def _browse_input(self):
        path = filedialog.askopenfilename(
            title="Seleziona file HTML",
            filetypes=[("File HTML", "*.html *.htm"),
                       ("Tutti i file", "*.*")])
        if not path:
            return
        self.var_input.set(path)
        base, ext = os.path.splitext(path)
        self.var_output.set(f"{base}_with_mermaid{ext}")
        self.var_status.set("File selezionato. Pronto per la conversione.")
        self._log_clear()

    def _browse_output(self):
        initial = self.var_output.get() or self.var_input.get()
        path = filedialog.asksaveasfilename(
            title="Salva file convertito",
            initialfile=os.path.basename(initial),
            defaultextension=".html",
            filetypes=[("File HTML", "*.html *.htm"),
                       ("Tutti i file", "*.*")])
        if path:
            self.var_output.set(path)

    def _run(self):
        input_path = self.var_input.get().strip()
        output_path = self.var_output.get().strip()

        if not input_path:
            messagebox.showwarning(
                "Attenzione", "Selezionare prima un file di input.")
            return
        if not os.path.isfile(input_path):
            messagebox.showerror(
                "Errore", f"Il file non esiste:\n{input_path}")
            return
        if not output_path:
            messagebox.showwarning(
                "Attenzione", "Specificare il percorso del file di output.")
            return

        self._log_clear()
        self.progress.start(12)
        self.var_status.set("Elaborazione in corso…")
        self.update_idletasks()

        try:
            n = process_html(input_path, output_path)
            self._log_append(
                f"Conversione completata.\n"
                f"  Blocchi convertiti  : {n}\n"
                f"  Correzioni applicate: A B C D E F G H I Z\n"
                f"  Output              : {output_path}"
            )
            self.var_status.set(
                f"✔ Completato — {n} blocco/i  →  "
                f"{os.path.basename(output_path)}"
            )
            messagebox.showinfo(
                "Conversione completata",
                f"Blocchi convertiti: {n}\n\nFile salvato in:\n{output_path}"
            )
        except Exception as exc:
            self._log_append(f"ERRORE: {exc}")
            self.var_status.set(f"✖ Errore: {exc}")
            messagebox.showerror(
                "Errore durante l'elaborazione", str(exc))
        finally:
            self.progress.stop()

    # ------------------------------------------------------------------
    # Log
    # ------------------------------------------------------------------
    def _log_append(self, text: str):
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", text + "\n")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def _log_clear(self):
        self.txt_log.configure(state="normal")
        self.txt_log.delete("1.0", "end")
        self.txt_log.configure(state="disabled")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = App()
    app.mainloop()
