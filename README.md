# Viva Wallet → GPC Converter

Modern desktop application for converting Viva Wallet export files to GPC (ABO) format compatible with **POHODA** accounting software.

## 🎯 Purpose

Viva Wallet provides transaction exports in an HTML/XLS format. POHODA accounting software requires bank statements in the Czech **GPC (ABO)** standard. This tool bridges that gap — taking your Viva Wallet export and producing a POHODA-ready `.gpc` file that imports cleanly.

## ✨ Features

- **Modern GUI** — Clean, intuitive interface built with tkinter
- **Bilingual** — Full English/Czech language toggle
- **Smart defaults** — Auto-generates output filename from account details
- **Real-time validation** — Checks account number length, file existence
- **Detailed conversion log** — Shows all transaction totals and balance verification
- **Batch ready** — Run conversions one after another for multiple files

## 📦 Output Filename Convention

The app automatically suggests output files named:

```
<ACCOUNT_NUMBER>-<ACCOUNT_NAME>.gpc
```

Example: `0000541164116547-NERUDOVA46.gpc`

You can still manually edit the filename if needed.

## 🖥️ GUI Overview

![Main Interface]

The interface consists of:

1. **Language toggle** — Switch between English / Czech (top-right)
2. **Input file browser** — Select your Viva Wallet XLS/HTML export
3. **Output file browser** — Choose destination GPC filename
4. **Account details** — Account number (16 digits) and name (max 20 chars)
5. **Statement sequence** — Sequential number for this statement (usually 1)
6. **Convert button** — Triggers conversion and displays results
7. **Conversion log** — Scrollable area showing totals, dates, and balance check

## 📦 Installation

### Option A — Download Pre-built Executable (Windows)

1. Go to the [Releases page](https://github.com/majidka99/gpc-converter/releases)
2. Download `GPC_Converter_Setup_1.0.0.msi` (Windows installer)
3. Run the installer and follow prompts
4. Launch **GPC Converter** from Start Menu or Desktop

### Option B — Run from Source (Any OS)

#### Requirements
- Python 3.8 or higher
- Standard library only (no external packages needed)

#### Steps
```bash
# Clone the repository
git clone https://github.com/majidka99/gpc-converter.git
cd gpc-converter

# Run the GUI application
python3 gpc_converter_gui.py

# Or run the CLI version (edit INPUT_FILE/OUTPUT_FILE in script first)
python3 convert_to_gpc.py
```

**Note on Windows:** If Python is not installed, download it from [python.org](https://python.org) and during installation check **"Add Python to PATH"**. Tkinter is included by default with Windows Python installs.

### Option C — Build Standalone Executable from Source

To create a standalone `.exe` (no Python required to run):

#### Prerequisites
```bash
pip install pyinstaller
```

#### Build (Windows)
```bash
# From repository root
build.bat
```

The executable will be at `dist\GPC Converter\GPC Converter.exe`.

#### Build (Linux/macOS)
```bash
pyinstaller gpc_converter_gui.spec --clean
```

**Note:** The Windows `.exe` must be built on Windows (or via Wine) for best compatibility. Cross-compilation from Linux is not officially supported by PyInstaller.

## 📖 Usage Guide

### Step-by-step

1. **Launch the app** — `python3 gpc_converter_gui.py`
2. **Select input file** — Click "Browse" and pick your `Wallet_*.xls` or `.html` export
3. **Review output name** — Auto-filled as `ACCOUNTNUMBER-ACCOUNTNAME.gpc`; edit if desired
4. **Verify account details** — The account number (16 digits) and name must match your POHODA bank account setup
5. **Set statement number** — Usually `1` for a new statement; increment for subsequent statements
6. **Click "Convert to GPC"** — Wait for conversion to finish
7. **Check the log** — Verify transaction count and balance check shows `OK`

### CLI Alternative

For automation or command-line use, the original `convert_to_gpc.py` script is included. Edit the `INPUT_FILE` and `OUTPUT_FILE` constants at the top, then run:

```bash
python3 convert_to_gpc.py
```

## 🏦 POHODA Configuration

Before importing the generated `.gpc` file into POHODA:

1. Open **Agenda → Účetnictví → Banka**
2. Create a new bank account record:
   - **Číslo účtu**: `0000541164116547` (your 16-digit account)
   - **Kód banky**: `0570` (Viva Wallet / Airbank)
3. Use the **Import bank statement** function and select your `.gpc` file

## 📊 GPC Format Details

Each GPC record is exactly 128 characters + CRLF (130 bytes total).

### Record 074 — Statement header
```
[1-3]    "074"
[4-19]   Account number (16, zero-padded)
[20-39]  Account name (20, space-padded)
[40-45]  Opening balance date DDMMYY
[46-59]  Opening balance in haléře (14, zero-padded)
[60]     Opening balance sign (+/-)
[61-74]  Closing balance (14)
[75]     Closing balance sign
[76-89]  Total debits (14)
[90]     Debit sign ("-" if any, else "0")
[91-104] Total credits (14)
[105]    Credit sign ("0")
[106-108]Statement sequence (3)
[109-114]Closing/statement date DDMMYY
[115-128]Filler (14 spaces)
```

### Record 075 — Individual transactions
```
[1-3]    "075"
[4-19]   Own account number (16)
[20-35]  Counter-party account (16 zeros)
[36-48]  Document number (13 zeros)
[49-60]  Amount in haléře (12, absolute)
[61]     Type: 1=debit, 2=credit
[62-71]  VS — variable symbol (10 zeros)
[72-81]  KS — constant symbol (10 zeros)
[82-91]  SS — specific symbol (10 zeros)
[92-97]  Transaction date DDMMYY
[98-117] Counter-party name / description (20)
[118]    "0"
[119-122]Currency code "0203" (CZK)
[123-128]Maturity date DDMMYY
```

**Haléře**: Amounts are stored as *heller* (Czech cents) without decimal point.  
Example: `12345.67 CZK` → `"00000001234567"`

## 🧮 Balance Verification

The app computes:
- **Opening balance** = oldest transaction balance − oldest transaction amount
- **Closing balance** = newest transaction balance (directly from file)
- **Net** = total credits − total debits

A successful import into POHODA passes the `net == closing − opening` check. The GUI reports both values in the log.

## 🎨 Customization

Adapt the conversion to other banks by modifying:

- `ACCOUNT_NUMBER` and `ACCOUNT_NAME` — your POHODA bank account details
- `parse_amount()` — if your export uses different thousand/decimal separators
- `make_074()` / `make_075()` — if you need different field placements or formats

## 📜 License

This tool is provided as‑is for personal and business use with Viva Wallet exports.

## 🙋 Support

For issues, questions, or feature requests, please open an issue in the repository.

---

*Generated GPC files are compatible with POHODA 9+ and Czech Banking Association ABO standard.*
