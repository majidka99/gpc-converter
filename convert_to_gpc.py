#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert Viva Wallet HTML-XLS export to GPC (ABO) format for POHODA import.

Follows the Czech ABO / GPC standard (as documented by FIO bank / Czech Banking
Association). Each record is exactly 128 characters + CRLF = 130 bytes.

Record 074 layout (bytes 1-128):
  1-3    "074"
  4-19   Account number (16, zero-padded left)
  20-39  Account name   (20, space-padded right)
  40-45  Old-balance date DDMMYY
  46-59  Old balance (haléře, 14, zero-padded)
  60     Old balance sign  "+" or "-"
  61-74  New balance (14)
  75     New balance sign
  76-89  Total debits (14)
  90     Debit sign  "-" if debits > 0, else "0"
  91-104 Total credits (14)
  105    Credit sign "0"
  106-108 Statement seq (3)
  109-114 Accounting date DDMMYY
  115-128 14 spaces filler

Record 075 layout (bytes 1-128):
  1-3    "075"
  4-19   Own account number (16)
  20-35  Counter-party account (16, zeros if unknown)
  36-48  Document number (13, zeros)
  49-60  Amount in haléře (12, absolute value, zero-padded)
  61     Type: 1=debit  2=credit  4=storno-debit  5=storno-credit
  62-71  VS  variable symbol (10)
  72-81  KS  constant symbol (10, format BBBBKSYM)
  82-91  SS  specific symbol (10)
  92-97  Valuta / value date DDMMYY
  98-117 Counter-party name / description (20, space-padded right)
  118    "0"
  119-122 "0203"  (CZK currency code)
  123-128 Maturity date DDMMYY

POHODA setup required BEFORE import:
  Agenda → Účetnictví → Banka → New account
    Číslo účtu : 0000541164116547
    Kód banky  : 0570
"""

from html.parser import HTMLParser
import html as html_module
import sys

# ── Configuration ──────────────────────────────────────────────────────────────
INPUT_FILE     = "Wallet_21.04.2026(1).xls"
OUTPUT_FILE    = "Wallet_21.04.2026.gpc"

# From IBAN GR04 | 057 (bank) | 0000 (branch) | 0000541164116547 (account, 16 chars)
ACCOUNT_NUMBER = "0000541164116547"   # 16-char number – must match POHODA bank account
ACCOUNT_NAME   = "NERUDOVA46"         # max 20 chars
STATEMENT_SEQ  = 1
# ───────────────────────────────────────────────────────────────────────────────


def normalize_account_number(account: str) -> str:
    """Validate and pad an account number to the 16-char GPC field."""
    cleaned = account.strip()
    if not cleaned.isdigit():
        raise ValueError("Account number must contain digits only.")
    if len(cleaned) > 16:
        raise ValueError("Account number must be 16 digits or fewer.")
    return cleaned.rjust(16, "0")


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
    """Parse Czech-formatted amount → integer haléře (cents).
    Thousand separator is non-breaking space \\xa0; decimal separator is comma."""
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
    """Build a 074 header record (exactly 128 chars) per Czech ABO standard.

    Byte map:
      1-3    "074"
      4-19   account (16, zero-padded)
      20-39  name    (20, space-padded right)
      40-45  old-balance date DDMMYY
      46-59  old balance (14, haléře)
      60     old balance sign
      61-74  new balance (14)
      75     new balance sign
      76-89  total debits (14)
      90     debit sign  "-" if >0, else "0"
      91-104 total credits (14)
      105    credit sign "0"
      106-108 seq (3)
      109-114 accounting / closing date DDMMYY
      115-128 filler (14 spaces)
    """
    account_field = normalize_account_number(account)
    old_sign  = "+" if old_bal  >= 0 else "-"
    new_sign  = "+" if new_bal  >= 0 else "-"
    dbt_sign  = "-" if debit_sum > 0 else "0"
    crd_sign  = "0"

    rec = (
        "074"                            # [1-3]   (3)
        + account_field                   # [4-19]  (16)
        + name[:20].ljust(20)            # [20-39] (20)
        + fmt_date(start_date)           # [40-45] (6)
        + fmt_amount(old_bal)            # [46-59] (14)
        + old_sign                       # [60]    (1)
        + fmt_amount(new_bal)            # [61-74] (14)
        + new_sign                       # [75]    (1)
        + fmt_amount(debit_sum)          # [76-89] (14)
        + dbt_sign                       # [90]    (1)
        + fmt_amount(credit_sum)         # [91-104](14)
        + crd_sign                       # [105]   (1)
        + str(seq).rjust(3, "0")         # [106-108](3)
        + fmt_date(end_date)             # [109-114](6)
        + " " * 14                       # [115-128](14)
    )
    assert len(rec) == 128, f"074 length is {len(rec)}, expected 128"
    return rec


def make_075(account, date_str, amount_hel, desc) -> str:
    """Build a 075 transaction record (exactly 128 chars) per Czech ABO standard.

    Byte map:
      1-3    "075"
      4-19   own account (16)
      20-35  counter account (16, zeros = unknown)
      36-48  document number (13, zeros)
      49-60  amount haléře (12, absolute)
      61     type: 1=debit  2=credit
      62-71  VS (10, zeros)
      72-81  KS (10, zeros)
      82-91  SS (10, zeros)
      92-97  valuta date DDMMYY
      98-117 counter-party name / description (20)
      118    "0"
      119-122 "0203" (CZK)
      123-128 maturity date DDMMYY
    """
    account_field = normalize_account_number(account)
    tx_type = "2" if amount_hel >= 0 else "1"
    note    = desc[:20].ljust(20)

    rec = (
        "075"                            # [1-3]   (3)
        + account_field                   # [4-19]  (16)
        + "0" * 16                       # [20-35] counter account (16)
        + "0" * 13                       # [36-48] doc number (13)
        + fmt_amount_12(amount_hel)      # [49-60] amount (12)
        + tx_type                        # [61]    type (1)
        + "0" * 10                       # [62-71] VS (10)
        + "0" * 10                       # [72-81] KS (10)
        + "0" * 10                       # [82-91] SS (10)
        + fmt_date(date_str)             # [92-97] valuta (6)
        + note                           # [98-117] name/desc (20)
        + "0"                            # [118]   literal (1)
        + "0203"                         # [119-122] CZK (4)
        + fmt_date(date_str)             # [123-128] maturity (6)
    )
    assert len(rec) == 128, f"075 length is {len(rec)}, expected 128"
    return rec


def main():
    normalized_account = normalize_account_number(ACCOUNT_NUMBER)

    # ── Parse HTML/XLS file ────────────────────────────────────────────────────
    with open(INPUT_FILE, encoding="utf-8") as f:
        content = f.read()

    parser = TableParser()
    parser.feed(content)

    # rows[0] = header row, rows[1:] = data (newest transaction first)
    data_rows = parser.rows[1:]
    if not data_rows:
        print("ERROR: No data rows found.", file=sys.stderr)
        sys.exit(1)

    # Columns:
    #  0  ID transakce
    #  1  Datum příspěvku   (posting date  DD.MM.YYYY)
    #  2  Čas příspěvku     (posting time  HH:MM:SS)
    #  3  Datum transakce   (transaction date DD.MM.YYYY)
    #  4  Popis             (description)
    #  5  Číslo karty       (card number, usually empty)
    #  6  Měna              (currency)
    #  7  Částka            (amount, CZ format)
    #  8  Zůstatek          (balance after transaction)
    #  9  K dispozici       (available)
    # 10  Držení            (on hold)

    # ── Calculate balances ─────────────────────────────────────────────────────
    # data_rows[0]  = newest  (closing balance is here)
    # data_rows[-1] = oldest  (opening balance derived from here)

    closing_balance = parse_amount(data_rows[0][8])

    oldest_amount  = parse_amount(data_rows[-1][7])
    oldest_balance = parse_amount(data_rows[-1][8])
    opening_balance = oldest_balance - oldest_amount

    # ── Calculate totals ───────────────────────────────────────────────────────
    total_credits = 0
    total_debits  = 0
    for row in data_rows:
        amt = parse_amount(row[7])
        if amt >= 0:
            total_credits += amt
        else:
            total_debits += abs(amt)

    # ── Statement period ───────────────────────────────────────────────────────
    # data_rows is newest-first; reverse for chronological order
    data_rows_chrono = list(reversed(data_rows))
    start_date = data_rows_chrono[0][3]   # oldest transaction date
    end_date   = data_rows[0][3]          # newest transaction date

    # ── Build GPC records ──────────────────────────────────────────────────────
    lines = []

    # 074 – header
    lines.append(make_074(
        account    = normalized_account,
        start_date = start_date,
        end_date   = end_date,
        old_bal    = opening_balance,
        new_bal    = closing_balance,
        debit_sum  = total_debits,
        credit_sum = total_credits,
        seq        = STATEMENT_SEQ,
        name       = ACCOUNT_NAME,
    ))

    # 075 – transactions in chronological order (oldest first)
    for row in data_rows_chrono:
        lines.append(make_075(
            account    = normalized_account,
            date_str   = row[3],          # Datum transakce
            amount_hel = parse_amount(row[7]),
            desc       = row[4],          # Popis
        ))

    # ── Write output ───────────────────────────────────────────────────────────
    with open(OUTPUT_FILE, "wb") as f:
        for line in lines:
            f.write(line.encode("cp1250", errors="replace"))
            f.write(b"\r\n")

    # ── Summary ────────────────────────────────────────────────────────────────
    print(f"✓  Generated: {OUTPUT_FILE}")
    print(f"   Transactions : {len(data_rows)}")
    print(f"   Period       : {start_date} – {end_date}")
    print(f"   Opening bal  : {opening_balance/100:>14,.2f} CZK")
    print(f"   Closing bal  : {closing_balance/100:>14,.2f} CZK")
    print(f"   Total credits: {total_credits/100:>14,.2f} CZK")
    print(f"   Total debits : {total_debits/100:>14,.2f} CZK")
    net = total_credits - total_debits
    print(f"   Net          : {net/100:>14,.2f} CZK")
    expected_net = closing_balance - opening_balance
    if net == expected_net:
        print("   Balance check: OK ✓")
    else:
        print(f"   Balance check: MISMATCH (expected net {expected_net/100:.2f})")


if __name__ == "__main__":
    main()
