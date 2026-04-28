#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modern GUI application for converting Viva Wallet HTML-XLS export to GPC (ABO) format.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from html.parser import HTMLParser
import html as html_module
import sys
import os

# ── Core conversion functions ────────────────────────────────────────────────────

class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self._row = []
        self._cell = ""
        self._in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag in ("td", "th"):
            self._in_cell = True
            self._cell = ""

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self._row.append(self._cell.strip())
            self._in_cell = False
        elif tag == "tr":
            if self._row:
                self.rows.append(self._row)
            self._row = []

    def handle_data(self, data):
        if self._in_cell:
            self._cell += data

    def handle_entityref(self, name):
        if self._in_cell:
            self._cell += html_module.unescape("&" + name + ";")

    def handle_charref(self, name):
        if self._in_cell:
            if name.startswith("x"):
                self._cell += chr(int(name[1:], 16))
            else:
                self._cell += chr(int(name))


def parse_amount(s: str) -> int:
    """Parse Czech-formatted amount → integer haléře (cents)."""
    cleaned = s.replace("\xa0", "").replace("\u00a0", "").replace("\u202f", "")
    cleaned = cleaned.replace(" ", "").replace(",", ".")
    if not cleaned or cleaned in ("---", ""):
        return 0
    return round(float(cleaned) * 100)


def fmt_date(date_str: str) -> str:
    """'DD.MM.YYYY'  →  'DDMMYY'"""
    d, m, y = date_str.split(".")
    return d + m + y[2:]


def fmt_amount(haléře: int) -> str:
    """Absolute haléře value → 14-char right-justified zero-padded string."""
    return str(abs(haléře)).rjust(14, "0")


def fmt_amount_12(haléře: int) -> str:
    """Absolute haléře value → 12-char right-justified zero-padded string."""
    return str(abs(haléře)).rjust(12, "0")


def make_074(account, start_date, end_date, old_bal, new_bal,
             debit_sum, credit_sum, seq, name) -> str:
    """Build a 074 header record (exactly 128 chars)."""
    old_sign  = "+" if old_bal  >= 0 else "-"
    new_sign  = "+" if new_bal  >= 0 else "-"
    dbt_sign  = "-" if debit_sum > 0 else "0"
    crd_sign  = "0"

    rec = (
        "074"
        + account.rjust(16, "0")
        + name[:20].ljust(20)
        + fmt_date(start_date)
        + fmt_amount(old_bal)
        + old_sign
        + fmt_amount(new_bal)
        + new_sign
        + fmt_amount(debit_sum)
        + dbt_sign
        + fmt_amount(credit_sum)
        + crd_sign
        + str(seq).rjust(3, "0")
        + fmt_date(end_date)
        + " " * 14
    )
    assert len(rec) == 128, f"074 length is {len(rec)}, expected 128"
    return rec


def make_075(account, date_str, amount_hel, desc) -> str:
    """Build a 075 transaction record (exactly 128 chars)."""
    tx_type = "2" if amount_hel >= 0 else "1"
    note    = desc[:20].ljust(20)

    rec = (
        "075"
        + account.rjust(16, "0")
        + "0" * 16
        + "0" * 13
        + fmt_amount_12(amount_hel)
        + tx_type
        + "0" * 10
        + "0" * 10
        + "0" * 10
        + fmt_date(date_str)
        + note
        + "0"
        + "0203"
        + fmt_date(date_str)
    )
    assert len(rec) == 128, f"075 length is {len(rec)}, expected 128"
    return rec


def convert_file(input_path, output_path, account_number, account_name, statement_seq):
    """Perform the conversion and return a summary dict."""
    with open(input_path, encoding="utf-8") as f:
        content = f.read()

    parser = TableParser()
    parser.feed(content)

    data_rows = parser.rows[1:]
    if not data_rows:
        raise ValueError("No data rows found in the input file.")

    closing_balance = parse_amount(data_rows[0][8])
    oldest_amount  = parse_amount(data_rows[-1][7])
    oldest_balance = parse_amount(data_rows[-1][8])
    opening_balance = oldest_balance - oldest_amount

    total_credits = 0
    total_debits  = 0
    for row in data_rows:
        amt = parse_amount(row[7])
        if amt >= 0:
            total_credits += amt
        else:
            total_debits += abs(amt)

    data_rows_chrono = list(reversed(data_rows))
    start_date = data_rows_chrono[0][3]
    end_date   = data_rows[0][3]

    lines = []
    lines.append(make_074(
        account    = account_number,
        start_date = start_date,
        end_date   = end_date,
        old_bal    = opening_balance,
        new_bal    = closing_balance,
        debit_sum  = total_debits,
        credit_sum = total_credits,
        seq        = statement_seq,
        name       = account_name,
    ))

    for row in data_rows_chrono:
        lines.append(make_075(
            account    = account_number,
            date_str   = row[3],
            amount_hel = parse_amount(row[7]),
            desc       = row[4],
        ))

    with open(output_path, "wb") as f:
        for line in lines:
            f.write(line.encode("cp1250", errors="replace"))
            f.write(b"\r\n")

    return {
        "transactions": len(data_rows),
        "start_date": start_date,
        "end_date": end_date,
        "opening_balance": opening_balance,
        "closing_balance": closing_balance,
        "total_credits": total_credits,
        "total_debits": total_debits,
    }


# ── Modern GUI ───────────────────────────────────────────────────────────────────

class ModernStyle:
    """Modern color palette and styling constants."""
    PRIMARY   = "#2563eb"      # Blue
    PRIMARY_D = "#1e40af"      # Darker blue
    SECONDARY = "#64748b"      # Slate
    SUCCESS   = "#10b981"      # Green
    BG        = "#f8fafc"      # Light gray
    CARD_BG   = "#ffffff"      # White
    TEXT      = "#1e293b"      # Dark slate
    TEXT_L    = "#64748b"      # Light text
    BORDER    = "#e2e8f0"      # Light border

    FONT_FAMILY = "Segoe UI"
    FONT_SIZE   = 10


# ── Translation strings ──────────────────────────────────────────────────────────

TRANSLATIONS = {
    "en": {
        "title": "Viva Wallet → GPC Converter",
        "subtitle": "Convert Viva Wallet exports to POHODA GPC format",
        "input_label": "📄 Input File",
        "input_btn": "Browse",
        "output_label": "💾 Output File",
        "output_btn": "Browse",
        "account_label": "🏦 Account Number (16 digits)",
        "name_label": "🏢 Account Name (max 20 chars)",
        "seq_label": "🔢 Statement #",
        "convert_btn": "Convert to GPC",
        "log_label": "📋 Conversion Log",
        "convert_msg": "⏳ Converting: {}",
        "output_msg": "📁 Output    : {}",
        "error_file": "Please select a valid input file.",
        "error_output": "Please specify an output file.",
        "error_acc_num": "Account number must be exactly 16 digits.",
        "error_acc_name": "Account name is required (max 20 chars).",
        "error_seq": "Statement sequence must be a number.",
        "conversion_error": "Conversion Error",
        "success_title": "Success",
        "success_msg": "✅ File converted successfully!",
        # Log labels
        "tx": "Transactions",
        "period": "Period",
        "open_bal": "Opening bal",
        "close_bal": "Closing bal",
        "credits": "Total credits",
        "debits": "Total debits",
        "net": "Net",
        "balance_ok": "✅ Balance check: OK",
        "balance_mismatch": "⚠️  Balance check: MISMATCH (expected {:.2f})",
        # Toggle
        "lang_toggle": "🇨🇿 Česky / 🇺🇸 English",
    },
    "cs": {
        "title": "Převodník Viva Wallet → GPC",
        "subtitle": "Převod exportů Viva Wallet do formátu GPC pro POHODU",
        "input_label": "📄 Vstupní soubor",
        "input_btn": "Procházet",
        "output_label": "💾 Výstupní soubor",
        "output_btn": "Procházet",
        "account_label": "🏦 Číslo účtu (16 číslic)",
        "name_label": "🏢 Název účtu (max 20 znaků)",
        "seq_label": "�Číslo výpisu",
        "convert_btn": "Převést do GPC",
        "log_label": "📋 Převodní log",
        "convert_msg": "⏳ Převáděj: {}",
        "output_msg": "📁 Výstup    : {}",
        "error_file": "Vyberte platný vstupní soubor.",
        "error_output": "Zadejte výstupní soubor.",
        "error_acc_num": "Číslo účtu musí mít přesně 16 číslic.",
        "error_acc_name": "Název účtu je povinný (max 20 znaků).",
        "error_seq": "Číslo výpisu musí být číslo.",
        "conversion_error": "Chyba převodu",
        "success_title": "Hotovo",
        "success_msg": "✅ Soubor byl úspěšně převeden!",
        # Log labels
        "tx": "Transakce",
        "period": "Období",
        "open_bal": "Poč. zůstatek",
        "close_bal": "Závěrečný zůst.",
        "credits": "Celkem příjmy",
        "debits": "Celkem výdaje",
        "net": "Rozdíl",
        "balance_ok": "✅ Kontrola zůstatku: OK",
        "balance_mismatch": "⚠️  Kontrola zůstatku: NESOUHLAS (očekáván {:.2f})",
        # Toggle
        "lang_toggle": "🇨🇿 Česky / 🇺🇸 English",
    }
}


class GPCConverterGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.lang = tk.StringVar(value="en")
        self._update_translations()

        self.title(self.t["title"])
        self.configure(bg=ModernStyle.BG)
        self.resizable(False, False)
        self.minsize(580, 540)

        # Variables
        self.input_file     = tk.StringVar()
        self.output_file    = tk.StringVar()
        self.account_number = tk.StringVar(value="0000541164116547")
        self.account_name   = tk.StringVar(value="NERUDOVA46")
        self.statement_seq  = tk.StringVar(value="1")

        # Trace account changes to auto-update output filename
        self.account_number.trace_add("write", self._update_output_name)
        self.account_name.trace_add("write", self._update_output_name)

        self._configure_styles()
        self._build_ui()

    def tr(self, key):
        return self.t[key]

    def _update_translations(self):
        """Refresh translation dict based on current language."""
        self.t = TRANSLATIONS[self.lang.get()]

    def _configure_styles(self):
        """Configure ttk styles for a modern look."""
        style = ttk.Style()
        if sys.platform == "win32":
            style.theme_use("vista")
        elif sys.platform == "darwin":
            style.theme_use("aqua")
        else:
            style.theme_use("clam")

        # Frame styles
        style.configure("Card.TFrame", background=ModernStyle.CARD_BG, relief="flat")
        style.configure("Section.TFrame", background=ModernStyle.BG)
        style.configure("Lang.TFrame", background=ModernStyle.BG)

        # Label styles
        style.configure("Heading.TLabel", 
                       background=ModernStyle.BG,
                       foreground=ModernStyle.TEXT,
                       font=(ModernStyle.FONT_FAMILY, 16, "bold"))
        style.configure("Subheading.TLabel",
                       background=ModernStyle.BG,
                       foreground=ModernStyle.TEXT_L,
                       font=(ModernStyle.FONT_FAMILY, 9))
        style.configure("FieldLabel.TLabel",
                       background=ModernStyle.CARD_BG,
                       foreground=ModernStyle.TEXT,
                       font=(ModernStyle.FONT_FAMILY, ModernStyle.FONT_SIZE, "bold"))
        style.configure("Success.TLabel",
                       background=ModernStyle.CARD_BG,
                       foreground=ModernStyle.SUCCESS,
                       font=(ModernStyle.FONT_FAMILY, ModernStyle.FONT_SIZE, "bold"))
        style.configure("Lang.TLabel",
                       background=ModernStyle.BG,
                       foreground=ModernStyle.SECONDARY,
                       font=(ModernStyle.FONT_FAMILY, ModernStyle.FONT_SIZE))

        # Entry styles
        style.configure("Modern.TEntry",
                       fieldbackground="white",
                       borderwidth=1,
                       relief="solid",
                       padding=6)

        # Button styles
        style.configure("Primary.TButton",
                       foreground="white",
                       background=ModernStyle.PRIMARY,
                       font=(ModernStyle.FONT_FAMILY, ModernStyle.FONT_SIZE, "bold"),
                       padding=10)
        style.map("Primary.TButton",
                 background=[("active", ModernStyle.PRIMARY_D)])

        style.configure("Secondary.TButton",
                       foreground=ModernStyle.TEXT,
                       background=ModernStyle.CARD_BG,
                       font=(ModernStyle.FONT_FAMILY, ModernStyle.FONT_SIZE),
                       padding=6)

        style.configure("Lang.TButton",
                       foreground=ModernStyle.SECONDARY,
                       background=ModernStyle.BG,
                       font=(ModernStyle.FONT_FAMILY, ModernStyle.FONT_SIZE, "bold"),
                       padding=4)
        style.map("Lang.TButton",
                 foreground=[("active", ModernStyle.PRIMARY)])

    def _build_ui(self):
        """Build the main UI layout."""
        # Main container
        main = ttk.Frame(self, style="Section.TFrame")
        main.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Top bar with language toggle
        self._build_top_bar(main)

        # Title & subtitle
        ttk.Label(main, text=self.tr("title"), style="Heading.TLabel").grid(
            row=1, column=0, columnspan=2, sticky="w", padx=20, pady=(10, 5))
        ttk.Label(main, text=self.tr("subtitle"), style="Subheading.TLabel").grid(
            row=2, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 20))

        # Card container
        card = ttk.Frame(main, style="Card.TFrame", relief="flat")
        card.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=20, pady=10)

        self._build_card_fields(card)

        # Status/Result area
        self._build_status_area(main)

        # Convert button (centered below card)
        btn_frame = ttk.Frame(main, style="Section.TFrame")
        btn_frame.grid(row=5, column=0, columnspan=2, pady=20)
        self.convert_btn = ttk.Button(btn_frame, text=self.tr("convert_btn"),
                                      style="Primary.TButton",
                                      command=self._convert)
        self.convert_btn.pack(ipadx=30)

    def _build_top_bar(self, parent):
        """Build top bar with language toggle."""
        top = ttk.Frame(parent, style="Lang.TFrame")
        top.grid(row=0, column=0, columnspan=2, sticky="ne", padx=20, pady=10)

        self.lang_btn = ttk.Button(top, text=self.tr("lang_toggle"),
                                   style="Lang.TButton",
                                   command=self._toggle_language)
        self.lang_btn.pack()

    def _build_card_fields(self, parent):
        """Build the input fields inside a card-like container."""
        pad = {"padx": 20, "pady": 15}
        label_pad = {"padx": 20, "pady": (15, 5)}

        row = 0

        # Input file
        ttk.Label(parent, text=self.tr("input_label"), style="FieldLabel.TLabel").grid(
            row=row, column=0, sticky="w", **label_pad)
        input_frame = ttk.Frame(parent, style="Card.TFrame")
        input_frame.grid(row=row, column=1, sticky="we", **pad)
        ttk.Entry(input_frame, textvariable=self.input_file, width=45,
                 style="Modern.TEntry").pack(side="left")
        ttk.Button(input_frame, text=self.tr("input_btn"), style="Secondary.TButton",
                  command=self._browse_input).pack(side="left", padx=5)
        parent.columnconfigure(1, weight=1)

        row += 1

        # Output file
        ttk.Label(parent, text=self.tr("output_label"), style="FieldLabel.TLabel").grid(
            row=row, column=0, sticky="w", **label_pad)
        output_frame = ttk.Frame(parent, style="Card.TFrame")
        output_frame.grid(row=row, column=1, sticky="we", **pad)
        ttk.Entry(output_frame, textvariable=self.output_file, width=45,
                 style="Modern.TEntry").pack(side="left")
        ttk.Button(output_frame, text=self.tr("output_btn"), style="Secondary.TButton",
                  command=self._browse_output).pack(side="left", padx=5)

        row += 1

        # Account number
        ttk.Label(parent, text=self.tr("account_label"), style="FieldLabel.TLabel").grid(
            row=row, column=0, sticky="w", **label_pad)
        ttk.Entry(parent, textvariable=self.account_number, width=30,
                 style="Modern.TEntry").grid(row=row, column=1, sticky="w", **pad)

        row += 1

        # Account name
        ttk.Label(parent, text=self.tr("name_label"), style="FieldLabel.TLabel").grid(
            row=row, column=0, sticky="w", **label_pad)
        ttk.Entry(parent, textvariable=self.account_name, width=30,
                 style="Modern.TEntry").grid(row=row, column=1, sticky="w", **pad)

        row += 1

        # Statement sequence
        ttk.Label(parent, text=self.tr("seq_label"), style="FieldLabel.TLabel").grid(
            row=row, column=0, sticky="w", **label_pad)
        ttk.Entry(parent, textvariable=self.statement_seq, width=10,
                 style="Modern.TEntry").grid(row=row, column=1, sticky="w", **pad)

    def _build_status_area(self, parent):
        """Build the scrollable status/results area."""
        ttk.Label(parent, text=self.tr("log_label"), style="FieldLabel.TLabel").grid(
            row=6, column=0, sticky="nw", padx=20, pady=(10, 5))

        frame = ttk.Frame(parent, style="Card.TFrame")
        frame.grid(row=7, column=0, columnspan=2, sticky="nsew", padx=20, pady=5)
        parent.rowconfigure(7, weight=1)

        self.log = scrolledtext.ScrolledText(
            frame, width=60, height=12, wrap="word",
            borderwidth=0, highlightthickness=0,
            bg="white", fg=ModernStyle.TEXT,
            font=(ModernStyle.FONT_FAMILY, ModernStyle.FONT_SIZE),
            padx=10, pady=10)
        self.log.pack(fill="both", expand=True, padx=2, pady=2)
        self.log.config(state="disabled")

    def _browse_input(self):
        filetypes = [
            ("Excel/HTML files", "*.xls *.xlsx *.html *.htm"),
            ("All files", "*.*"),
        ]
        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            self.input_file.set(path)
            # Auto-generate output name from account number and name
            self._update_output_name()

    def _browse_output(self):
        filetypes = [("GPC files", "*.gpc"), ("All files", "*.*")]
        path = filedialog.asksaveasfilename(filetypes=filetypes, defaultextension=".gpc")
        if path:
            self.output_file.set(path)

    def _update_output_name(self, *args):
        """Auto-generate output filename from account number and name."""
        # Only auto-generate if output wasn't manually set
        # or if it matches the auto-generate pattern
        current = self.output_file.get().strip()
        if not current or current.endswith(".gpc"):
            acc_num = self.account_number.get().strip()
            acc_name = self.account_name.get().strip()
            if acc_num and acc_name:
                safe_name = acc_name.replace(" ", "_")
                self.output_file.set(f"{acc_num}-{safe_name}.gpc")

    def _toggle_language(self):
        """Switch between English and Czech."""
        new_lang = "cs" if self.lang.get() == "en" else "en"
        self.lang.set(new_lang)
        self._update_translations()
        self._reload_ui()

    def _reload_ui(self):
        """Reload all UI text for current language."""
        self.title(self.t["title"])
        self.lang_btn.config(text=self.t["lang_toggle"])
        # Rebuild UI to update all labels
        for widget in self.winfo_children():
            widget.destroy()
        self._build_ui()
        # Variables remain intact because they are instance attributes

    def _log(self, msg):
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.config(state="disabled")
        self.update()

    def _convert(self):
        input_path  = self.input_file.get().strip()
        output_path = self.output_file.get().strip()
        acc_num     = self.account_number.get().strip()
        acc_name    = self.account_name.get().strip()
        seq_str     = self.statement_seq.get().strip()

        if not input_path or not os.path.exists(input_path):
            messagebox.showerror(self.t["conversion_error"], self.t["error_file"])
            return
        if not output_path:
            messagebox.showerror(self.t["conversion_error"], self.t["error_output"])
            return
        if len(acc_num) != 16 or not acc_num.isdigit():
            messagebox.showerror(self.t["conversion_error"], self.t["error_acc_num"])
            return
        if not acc_name:
            messagebox.showerror(self.t["conversion_error"], self.t["error_acc_name"])
            return
        try:
            seq = int(seq_str)
        except ValueError:
            messagebox.showerror(self.t["conversion_error"], self.t["error_seq"])
            return

        # Clear log
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")
        self._log(self.t["convert_msg"].format(os.path.basename(input_path)))
        self._log(self.t["output_msg"].format(os.path.basename(output_path)))
        self._log("")

        # Disable button during conversion
        self.convert_btn.config(state="disabled")
        self.update()

        try:
            result = convert_file(input_path, output_path, acc_num, acc_name, seq)
        except Exception as e:
            messagebox.showerror(self.t["conversion_error"], str(e))
            self._log(f"❌ ERROR: {e}")
            self.convert_btn.config(state="normal")
            return

        # Re-enable button
        self.convert_btn.config(state="normal")

        # Success message with color-coded output
        self._log("✅ " + self.t["success_msg"])
        self._log(f"📊 {self.t['tx']:<15}: {result['transactions']}")
        self._log(f"📅 {self.t['period']:<15}: {result['start_date']} – {result['end_date']}")
        self._log(f"💰 {self.t['open_bal']:<15}: {result['opening_balance']/100:>14,.2f} CZK")
        self._log(f"💰 {self.t['close_bal']:<15}: {result['closing_balance']/100:>14,.2f} CZK")
        self._log(f"⬆️  {self.t['credits']:<15}: {result['total_credits']/100:>14,.2f} CZK")
        self._log(f"⬇️  {self.t['debits']:<15}: {result['total_debits']/100:>14,.2f} CZK")
        net = result['total_credits'] - result['total_debits']
        self._log(f"📈 {self.t['net']:<15}: {net/100:>14,.2f} CZK")

        expected_net = result['closing_balance'] - result['opening_balance']
        if net == expected_net:
            self._log(self.t["balance_ok"])
        else:
            self._log(self.t["balance_mismatch"].format(expected_net/100))

        messagebox.showinfo(self.t["success_title"], self.t["success_msg"])


def main():
    app = GPCConverterGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
