# mermaid-html-converter

Uno script Python con interfaccia grafica che converte i blocchi di codice
`language-Mermaid` presenti in un file HTML esportato da Notion (o da qualsiasi
altro strumento che generi `<pre><code class="language-Mermaid">`) in elementi
`<div class="mermaid">` renderizzabili direttamente nel browser tramite
[Mermaid.js v10](https://mermaid.js.org/).

---

## Caratteristiche

- **Nessuna dipendenza esterna** — utilizza esclusivamente la libreria standard
  di Python (`re`, `html`, `tkinter`).
- **Interfaccia grafica** — selezione del file di input e della destinazione di
  output tramite finestre native del sistema operativo; barra di avanzamento e
  log testuale integrati.
- **Iniezione automatica dello script Mermaid** — inserisce il tag `<script
  type="module">` nel `<head>` del file HTML di output se non è già presente.
- **Sanitizzazione della sintassi** — corregge automaticamente tre categorie di
  errori che causano `Syntax error in text` in Mermaid v10 (dettagli nella
  sezione omonima).
- **Preservazione del file originale** — il file di input non viene mai
  modificato; l'output viene scritto in un file separato.

---

## Requisiti

| Componente | Versione minima |
|---|---|
| Python | 3.9 |
| tkinter | incluso nella distribuzione standard CPython |

> **Nota per Linux:** su alcune distribuzioni `tkinter` non è incluso nel
> pacchetto base di Python. Installarlo con:
> ```bash
> # Debian / Ubuntu
> sudo apt install python3-tk
>
> # Fedora / RHEL
> sudo dnf install python3-tkinter
> ```

---

## Installazione

```bash
git clone https://github.com/<utente>/mermaid-html-converter.git
cd mermaid-html-converter
```

Non è richiesto alcun passaggio di installazione aggiuntivo.

---

## Utilizzo

### Interfaccia grafica

```bash
python mermaid_converter.py
```

All'avvio compare la finestra principale:

1. **File HTML di input** — premere *Sfoglia…* e selezionare il file `.html`
   da convertire.
2. **File HTML di output** — il nome viene proposto automaticamente con suffisso
   `_with_mermaid`; è possibile modificarlo tramite il pulsante *Sfoglia…*.
3. Premere **▶ Converti**.
4. Il riquadro *Log* mostra il numero di blocchi convertiti e le
   sanitizzazioni applicate.

### Utilizzo programmatico

```python
from mermaid_converter import process_html

n_blocchi = process_html("lezioni.html", "lezioni_with_mermaid.html")
print(f"Blocchi convertiti: {n_blocchi}")
```

---

## Sanitizzazione della sintassi

Mermaid v10 è più rigido rispetto alle versioni precedenti. Lo script corregge
automaticamente i seguenti problemi al momento della conversione.

### 1 — Notazione `__testo__` (membro statico UML)

Mermaid v10 non riconosce i doppi underscore come indicatori di sottolineatura.
Il suffisso `$` è la sintassi corretta per i membri di classe (statici).

```
# Prima della sanitizzazione
__-singletonInstance : SingletonClass__

# Dopo la sanitizzazione
-singletonInstance$ : SingletonClass
```

### 2 — Nomi di classe che iniziano con cifra

Un identificatore come `class 2 { ... }` non è valido per il tokenizer di
Mermaid. Tutti i nomi problematici vengono rinominati aggiungendo il prefisso
`C_`; i riferimenti nelle relazioni e nelle note vengono aggiornati di
conseguenza.

```
# Prima della sanitizzazione
class 2 { ... }
Sensor <|-- 2

# Dopo la sanitizzazione
class C_2 { ... }
Sensor <|-- C_2
```

### 3 — Note duplicate sullo stesso nodo

Due o più istruzioni `note for NomeClasse` consecutive sullo stesso nodo
causano un errore di parsing. Viene conservata solo la prima occorrenza.

```
# Prima della sanitizzazione
note for SingletonClass "The Only Instance"
note for SingletonClass "It returns the Only Instance"

# Dopo la sanitizzazione
note for SingletonClass "The Only Instance"
```

---

## Struttura del progetto

```
mermaid-html-converter/
└── mermaid_converter.py   # Script principale (logica + UI)
└── README.md
```

---

## Limitazioni note

- Lo script gestisce un sottoinsieme delle possibili incompatibilità di sintassi
  tra Mermaid v9 e v10. Diagrammi con costrutti molto personalizzati potrebbero
  richiedere correzioni manuali aggiuntive.
- L'accesso alla CDN di Mermaid (`cdn.jsdelivr.net`) richiede una connessione
  internet al momento della visualizzazione del file HTML di output. Per
  ambienti offline è sufficiente sostituire l'URL dello script nella costante
  `MERMAID_SCRIPT` con un percorso locale.
- La sostituzione delle note duplicate conserva solo la **prima** occorrenza.
  Se il contenuto della seconda nota è rilevante, è necessario accorparle
  manualmente prima della conversione.

---

## Licenza

Distribuito sotto licenza MIT. Consultare il file `LICENSE` per i dettagli.
