# KURDISH LANGUAGE SKILL
## For AI Agents: Text Extraction, OCR Correction, and Keyboard Mapping

---

## HOW TO USE THIS SKILL

When any task involves Kurdish text — whether from images, user input, databases, or documents — read this file first. It defines the rules your agent must follow to avoid character substitution errors, encoding mistakes, and script confusion.

---

## PART 1: LANGUAGE IDENTIFICATION

There are **two distinct Kurdish writing systems**. You must identify which one you are working with before processing any text.

| Variety | Script | Primary Region | Example |
|---|---|---|---|
| Kurdish Sorani (Central Kurdish) | Arabic-based | Iraqi Kurdistan, Iran | `سڵاو` |
| Kurdish Kurmanji (Northern Kurdish) | Latin-based | Turkey, Syria, parts of Iraq | `Silav` |

**Rule:** Never mix these two scripts. If an image contains `سڵاو`, it is Sorani. If it contains `Silav`, it is Kurmanji. If you are unsure, ask before processing.

---

## PART 2: FULL ALPHABET REFERENCE

### 2A — Kurdish Sorani Alphabet (Arabic-based script)

This is the primary alphabet used in Iraqi Kurdistan, including universities, government documents, and official records.

| # | Letter | Unicode | Name | Common Misread As |
|---|---|---|---|---|
| 1 | ا | U+0627 | Alef | — |
| 2 | ب | U+0628 | Be | — |
| 3 | پ | U+067E | Pe (Kurdish-specific) | ب |
| 4 | ت | U+062A | Te | — |
| 5 | ج | U+062C | Jim | — |
| 6 | چ | U+0686 | Che (Kurdish-specific) | ج |
| 7 | ح | U+062D | He | — |
| 8 | خ | U+062E | Xhe | — |
| 9 | د | U+062F | Dal | — |
| 10 | ر | U+0631 | Re | — |
| 11 | ڕ | U+0695 | Re (Kurdish-specific, trilled R) | ر |
| 12 | ز | U+0632 | Ze | — |
| 13 | ژ | U+0698 | Zhe (Kurdish-specific) | ز |
| 14 | س | U+0633 | Sin | — |
| 15 | ش | U+0634 | Shin | — |
| 16 | ع | U+0639 | Ain | — |
| 17 | غ | U+063A | Ghain | — |
| 18 | ف | U+0641 | Fe | — |
| 19 | ڤ | U+06A4 | Ve (Kurdish-specific) | ف |
| 20 | ق | U+0642 | Qaf | — |
| 21 | ک | U+06A9 | Kaf (Kurdish form) | ك (Arabic kaf U+0643) |
| 22 | گ | U+06AF | Gaf (Kurdish-specific) | ک or ك |
| 23 | ل | U+0644 | Lam | — |
| 24 | ڵ | U+06B5 | Lla (Kurdish-specific, lateral L) | ل |
| 25 | م | U+0645 | Mim | — |
| 26 | ن | U+0646 | Nun | — |
| 27 | ه | U+0647 | He | — |
| 28 | ە | U+06D5 | Ae (Kurdish-specific vowel) | ه or ة |
| 29 | و | U+0648 | Waw | — |
| 30 | ۆ | U+06C6 | O (Kurdish-specific vowel) | و |
| 31 | ی | U+06CC | Ye | ي (Arabic ya U+064A) |
| 32 | ێ | U+06CE | Ee (Kurdish-specific vowel) | ي or ى |
| 33 | ئ | U+0626 | Hamza-Ye (word-initial glottal) | ن or ا |

**CRITICAL NOTE — The 8 Kurdish-Specific Characters:**
These 8 characters exist in Kurdish Sorani but do NOT exist in standard Arabic. When you see them in an image, you must output them exactly. Never substitute them for their Arabic lookalikes:

```
پ  (Pe)     → NEVER substitute with ب
چ  (Che)    → NEVER substitute with ج
ڕ  (trilled Re) → NEVER substitute with ر
ژ  (Zhe)    → NEVER substitute with ز
ڤ  (Ve)     → NEVER substitute with ف
گ  (Gaf)    → NEVER substitute with ک or ك
ڵ  (Lla)    → NEVER substitute with ل
ێ  (Ee)     → NEVER substitute with ي or ى
ۆ  (O)      → NEVER substitute with و
ە  (Ae)     → NEVER substitute with ه or ة
```

---

### 2B — Arabic Alphabet (for comparison and disambiguation)

When working with text that might be Arabic, not Kurdish, use this reference to distinguish.

| Letter | Unicode | Name | Kurdish Equivalent |
|---|---|---|---|
| ا | U+0627 | Alef | ا (shared) |
| ب | U+0628 | Ba | ب (shared) |
| ت | U+062A | Ta | ت (shared) |
| ث | U+062B | Tha | — (not used in Kurdish) |
| ج | U+062C | Jim | ج (shared) |
| ح | U+062D | Ha | ح (shared) |
| خ | U+062E | Kha | خ (shared) |
| د | U+062F | Dal | د (shared) |
| ذ | U+0630 | Dhal | — (not used in Kurdish) |
| ر | U+0631 | Ra | ر (shared, but Kurdish also has ڕ) |
| ز | U+0632 | Zay | ز (shared) |
| س | U+0633 | Sin | س (shared) |
| ش | U+0634 | Shin | ش (shared) |
| ص | U+0635 | Sad | — (not used in Kurdish) |
| ض | U+0636 | Dad | — (not used in Kurdish) |
| ط | U+0637 | Tah | — (not used in Kurdish) |
| ظ | U+0638 | Dhah | — (not used in Kurdish) |
| ع | U+0639 | Ain | ع (shared) |
| غ | U+063A | Ghain | غ (shared) |
| ف | U+0641 | Fa | ف (shared) |
| ق | U+0642 | Qaf | ق (shared) |
| ك | U+0643 | Kaf (Arabic) | → Kurdish uses ک (U+06A9) instead |
| ل | U+0644 | Lam | ل (shared, but Kurdish also has ڵ) |
| م | U+0645 | Mim | م (shared) |
| ن | U+0646 | Nun | ن (shared) |
| ه | U+0647 | Ha | ه (shared) |
| و | U+0648 | Waw | و (shared, but Kurdish also has ۆ) |
| ي | U+064A | Ya (Arabic) | → Kurdish uses ی (U+06CC) and ێ (U+06CE) |
| ى | U+0649 | Alef Maqsura | → Kurdish uses ێ (U+06CE) instead |
| ة | U+0629 | Ta Marbuta | — (not used in Kurdish, sometimes confused with ە) |

**Key Rule:** If the document is from Iraqi Kurdistan (universities, government, local data), assume Kurdish Sorani, NOT Arabic. Apply Kurdish character rules.

---

### 2C — English / Latin Alphabet

| Uppercase | Lowercase | Unicode Range |
|---|---|---|
| A–Z | a–z | U+0041–U+005A / U+0061–U+007A |

Kurdish Kurmanji uses the Latin alphabet with these additional characters:

| Letter | Unicode | Note |
|---|---|---|
| Ç / ç | U+00C7 / U+00E7 | Common in Kurmanji |
| Ş / ş | U+015E / U+015F | Common in Kurmanji |
| Ê / ê | U+00CA / U+00EA | Common in Kurmanji |
| Î / î | U+00CE / U+00EE | Common in Kurmanji |
| Û / û | U+00DB / U+00FB | Common in Kurmanji |
| X / x | Standard | Used as Kh sound in Kurmanji |

---

## PART 3: OCR CORRECTION RULES

When extracting text from images containing Kurdish Sorani, apply these corrections after extraction. These represent the most statistically common substitution errors made by general-purpose vision models.

### 3A — Python Correction Function

```python
import re

# Character-level substitution map
# Format: (wrong_output, correct_kurdish, context_note)
KURDISH_OCR_CORRECTIONS = {
    # Arabic Kaf → Kurdish Kaf (almost always safe)
    '\u0643': '\u06A9',  # ك → ک

    # Arabic Ya → Kurdish Ye (apply carefully, context-dependent)
    '\u064A': '\u06CC',  # ي → ی

    # Alef Maqsura → Kurdish Ee vowel
    '\u0649': '\u06CE',  # ى → ێ

    # Arabic Ta Marbuta → Kurdish Ae vowel
    '\u0629': '\u06D5',  # ة → ە
}

# Word-start patterns (very reliable corrections)
WORD_START_CORRECTIONS = [
    # ئ misread as ن at word start
    (r'(?<!\S)ن([اێەوۆی])', r'ئ\1'),
    # ئ misread as ا at word start (less common but occurs)
    (r'(?<!\S)ا(?=[^لرندتسشبمفقکگحخعغ])', r'ئ'),
]

def correct_kurdish_ocr(text: str) -> str:
    """
    Apply post-OCR corrections to Kurdish Sorani text.
    Run this on any text extracted from images before further processing.
    """
    # Step 1: Character-level substitutions
    for wrong, correct in KURDISH_OCR_CORRECTIONS.items():
        text = text.replace(wrong, correct)

    # Step 2: Word-start pattern corrections
    for pattern, replacement in WORD_START_CORRECTIONS:
        text = re.sub(pattern, replacement, text)

    return text


def validate_kurdish_text(text: str) -> dict:
    """
    Check if extracted text contains suspicious Arabic-only characters
    that should not appear in Kurdish Sorani text.
    Returns a report of potential issues.
    """
    arabic_only_chars = {
        '\u062B': 'ث (Tha — not used in Kurdish)',
        '\u0630': 'ذ (Dhal — not used in Kurdish)',
        '\u0635': 'ص (Sad — not used in Kurdish)',
        '\u0636': 'ض (Dad — not used in Kurdish)',
        '\u0637': 'ط (Tah — not used in Kurdish)',
        '\u0638': 'ظ (Dhah — not used in Kurdish)',
        '\u0643': 'ك (Arabic Kaf — Kurdish uses ک instead)',
        '\u064A': 'ي (Arabic Ya — Kurdish uses ی instead)',
        '\u0629': 'ة (Ta Marbuta — Kurdish uses ە instead)',
    }

    issues = {}
    for char, description in arabic_only_chars.items():
        count = text.count(char)
        if count > 0:
            issues[char] = {'description': description, 'count': count}

    return {
        'has_issues': len(issues) > 0,
        'issues': issues,
        'recommendation': 'Run correct_kurdish_ocr() to fix substitutions' if issues else 'Text looks clean'
    }
```

### 3B — JavaScript Correction Function

```javascript
const KURDISH_OCR_CORRECTIONS = {
  '\u0643': '\u06A9',  // ك → ک
  '\u064A': '\u06CC',  // ي → ی
  '\u0649': '\u06CE',  // ى → ێ
  '\u0629': '\u06D5',  // ة → ە
};

function correctKurdishOCR(text) {
  // Character-level corrections
  let corrected = text;
  for (const [wrong, correct] of Object.entries(KURDISH_OCR_CORRECTIONS)) {
    corrected = corrected.split(wrong).join(correct);
  }

  // Word-start ئ corrections
  corrected = corrected.replace(/(?<!\S)ن([اێەوۆی])/g, 'ئ$1');

  return corrected;
}

function validateKurdishText(text) {
  const arabicOnlyChars = ['ث', 'ذ', 'ص', 'ض', 'ط', 'ظ', 'ك', 'ي', 'ة'];
  const found = arabicOnlyChars.filter(char => text.includes(char));
  return {
    hasIssues: found.length > 0,
    suspiciousChars: found,
    recommendation: found.length > 0 ? 'Run correctKurdishOCR()' : 'Text looks clean'
  };
}
```

### 3C — Known University Names Dictionary

University names are a **closed, enumerable set**. Hard-coding them as ground truth is the most reliable way to fix entity-level errors that regex cannot catch (e.g., `ناکری` → `ئاکرێ`). This handles the case where word-start `ئ` is misread as `ن` inside a known proper noun.

Run this **after** `correct_kurdish_ocr()` and **before** structural extraction.

```python
KURDISH_UNIVERSITY_NAMES = {
    # Misread variants → correct Kurdish name
    'زانکۆی ناکری':                          'زانکۆی ئاکرێ',       # University of Akre
    'زانکۆی ناکرێ':                          'زانکۆی ئاکرێ',
    'نیکۆی ئاکرێ':                           'زانکۆی ئاکرێ',
    'زانکۆی هەولێر':                         'زانکۆی هەولێر',      # University of Erbil
    'پەیمانگای پۆلیتەکنیکی هەولێر':          'پەیمانگای پۆلیتەکنیکی هەولێر',  # EPU
    'زانکۆی سەڵاحەدین':                      'زانکۆی سەڵاحەدین',   # Salahaddin University
    'زانکۆی دهۆک':                           'زانکۆی دهۆک',        # University of Duhok
    'زانکۆی سلێمانی':                        'زانکۆی سلێمانی',     # University of Sulaimani
    'زانکۆی کەرکوک':                         'زانکۆی کەرکوک',      # University of Kirkuk
    'زانکۆی رەوەندوز':                       'زانکۆی رەوەندوز',    # University of Rawanduz
    'زانکۆی گەرمیان':                        'زانکۆی گەرمیان',     # University of Garmian
    'زانکۆی کۆیە':                           'زانکۆی کۆیە',        # University of Koya
    'زانکۆی زاخۆ':                           'زانکۆی زاخۆ',        # University of Zakho
    'زانکۆی حەڵەبجە':                        'زانکۆی حەڵەبجە',     # University of Halabja
    'زانکۆی ڕاپەرین':                        'زانکۆی ڕاپەرین',     # University of Raparin
    'پەیمانگای تەکنیکی کەرکوک':              'پەیمانگای تەکنیکی کەرکوک',
    'پەیمانگای پۆلیتەکنیکی سلێمانی':        'پەیمانگای پۆلیتەکنیکی سلێمانی',
    'پەیمانگای پۆلیتەکنیکی دهۆک':           'پەیمانگای پۆلیتەکنیکی دهۆک',
}

def correct_university_name(text: str) -> str:
    """
    Replace known OCR misreads of KRG university names with their correct forms.
    Run AFTER correct_kurdish_ocr() — character-level fixes must come first.
    This handles entity-level errors (proper nouns) that regex cannot fix.
    """
    for wrong, correct in KURDISH_UNIVERSITY_NAMES.items():
        text = text.replace(wrong, correct)
    return text
```

**Why this works:** University names are finite and known. Unlike free text, a wrong university name has exactly one correct form. This dictionary encodes that ground truth directly, making errors deterministic to fix rather than probabilistic to guess.

---

## PART 4: PROMPT TEMPLATES FOR AI AGENTS

### 4A — Image OCR Prompt (for Claude, GPT-4V, or any vision model)

Use this exact prompt structure when sending Kurdish document images to a vision model:

```
You are extracting text from a Kurdish Sorani university document.

LANGUAGE CONTEXT:
- This document is written in Kurdish Sorani (Central Kurdish), NOT Arabic
- Kurdish Sorani uses the Arabic script but has unique characters
- The document is from Iraqi Kurdistan / Erbil Polytechnic University region

CRITICAL CHARACTER RULES — never substitute these:
- پ (U+067E) is NOT ب
- چ (U+0686) is NOT ج  
- ڕ (U+0695) is NOT ر — this is the trilled Kurdish R
- ژ (U+0698) is NOT ز
- ڤ (U+06A4) is NOT ف
- گ (U+06AF) is NOT ک or ك
- ڵ (U+06B5) is NOT ل — this is the lateral Kurdish L
- ێ (U+06CE) is NOT ي or ى — this is the Kurdish Ee vowel
- ۆ (U+06C6) is NOT و — this is the Kurdish O vowel
- ە (U+06D5) is NOT ه or ة — this is the Kurdish Ae vowel
- ک (U+06A9) is NOT ك — always use the Kurdish form
- ئ (U+0626) at word starts is a glottal stop, NOT ن or ا

EXTRACTION RULES:
1. Extract all text exactly as written — preserve every character
2. Maintain the original layout and line breaks
3. For tables, preserve the row/column structure using | separators
4. If a character is unclear, mark it with [?] rather than guessing
5. Do not translate, summarize, or interpret — only extract

OUTPUT FORMAT:
Return the raw extracted text only, with no commentary.
```

### 4B — Text Validation Prompt (for checking extracted output)

```
I have extracted the following text from a Kurdish Sorani document.
Please review it and identify any characters that appear to be
incorrect Arabic substitutions for Kurdish characters.

Look specifically for:
- ك instead of ک
- ي or ى instead of ی or ێ
- ة instead of ە
- ن at word beginnings where ئ is expected
- ر where ڕ might be correct (trilled R contexts)
- ل where ڵ might be correct

Text to review:
[PASTE TEXT HERE]

Return: a list of suspected errors with their position and suggested correction.
```

### 4C — Structured University Data Extraction Prompt

For your specific use case (university names, colleges, majors, grades):

```
Extract the following structured data from this Kurdish Sorani university document image.
Apply all Kurdish character rules (see rules above).

Return the data as JSON with this structure:
{
  "university_name": "",
  "college": "",
  "department": "",
  "study_plan": [
    {
      "course_code": "",
      "course_name_kurdish": "",
      "course_name_arabic": "",
      "credit_hours": 0,
      "grade": ""
    }
  ],
  "student_info": {
    "name": "",
    "stage": "",
    "academic_year": ""
  }
}

Kurdish character rules apply. Mark uncertain characters with [?].
```

---

## PART 5: KEYBOARD LAYOUT REFERENCE

### 5A — Kurdish Sorani Keyboard (Standard Iraqi Layout)

This documents the standard Kurdish keyboard used on Windows and Android in Iraq.

```
Row 1 (numbers): same as English
Row 2: ق  و  ە  ر  ت  ێ  ئ  ی  پ  [  ]
Row 3: ا  س  د  ف  گ  ه  ج  ک  ل  ؛
Row 4: ز  خ  چ  ڤ  ب  ن  م  ،  .  /
```

**Characters requiring special access (Alt/long-press):**
- `ڕ` — trilled R (often missing or hard to reach on standard layouts)
- `ڵ` — lateral L (often missing on standard layouts)
- `ژ` — Zhe
- `ش` — Shin
- `ث`, `ذ`, `ص`, `ض`, `ط`, `ظ` — Arabic-only letters (should not be needed for Kurdish)

### 5B — Numeric and Symbol Mapping

Kurdish documents use Eastern Arabic numerals in formal contexts:

| Western | Eastern Arabic | Unicode |
|---|---|---|
| 0 | ٠ | U+0660 |
| 1 | ١ | U+0661 |
| 2 | ٢ | U+0662 |
| 3 | ٣ | U+0663 |
| 4 | ٤ | U+0664 |
| 5 | ٥ | U+0665 |
| 6 | ٦ | U+0666 |
| 7 | ٧ | U+0667 |
| 8 | ٨ | U+0668 |
| 9 | ٩ | U+0669 |

When extracting grades or course codes from Kurdish university documents, both numeral systems may appear. Normalize to Western Arabic numerals (0–9) for database storage.

---

## PART 6: TEXT DIRECTION AND RENDERING RULES

### 6A — BiDi (Bidirectional Text) Rules

Kurdish Sorani and Arabic are RTL (right-to-left). English and Kurmanji are LTR.

When working with mixed-direction text in code:

```python
# Always wrap RTL strings with Unicode directional markers for display
RTL_MARK = '\u200F'   # Right-to-Left Mark
LTR_MARK = '\u200E'   # Left-to-Right Mark

def wrap_rtl(text: str) -> str:
    return RTL_MARK + text + RTL_MARK

# For HTML, use the dir attribute
# <p dir="rtl">سڵاو</p>
# <span dir="ltr">English text inside RTL context</span>
```

### 6B — Common Invisible Characters to Watch For

These characters sometimes appear in copy-pasted Kurdish text and cause invisible bugs:

| Character | Unicode | Name | Issue |
|---|---|---|---|
| ‌ | U+200C | Zero Width Non-Joiner | Breaks letter connections |
| ‍ | U+200D | Zero Width Joiner | Forces letter connections |
| ‏ | U+200F | RTL Mark | Direction control |
| ‎ | U+200E | LTR Mark | Direction control |
| ­ | U+00AD | Soft Hyphen | Invisible hyphen |

```python
def strip_invisible_chars(text: str) -> str:
    """Remove invisible Unicode control characters from Kurdish text."""
    invisible = ['\u200C', '\u200D', '\u200F', '\u200E', '\u00AD', '\uFEFF']
    for char in invisible:
        text = text.replace(char, '')
    return text
```

---

## PART 7: QUICK DECISION TREE FOR AGENTS

When you receive Kurdish text or a Kurdish document image, follow this sequence:

```
1. IDENTIFY SCRIPT
   ├── Arabic-based characters? → Kurdish Sorani rules apply
   └── Latin characters?        → Kurdish Kurmanji rules apply (treat like European Latin)

2. IF SORANI — CHECK FOR SUBSTITUTION ERRORS
   ├── Run validateKurdishText()
   ├── If issues found → Run correctKurdishOCR()
   └── If no issues    → Proceed

3. FIX ENTITY-LEVEL ERRORS
   └── Run correct_university_name()  ← catches ناکری→ئاکرێ and similar proper noun misreads

4. EXTRACT STRUCTURED DATA
   ├── Use the university extraction prompt (Part 4C)
   ├── Normalize numerals to Western Arabic (0–9)
   └── Strip invisible characters (Part 6B)

5. VALIDATE OUTPUT
   ├── Spot-check: does the text contain ث ذ ص ض ط ظ?
   │   └── If yes → likely Arabic contamination, re-run correction
   ├── Spot-check: does ئ appear at word starts?
   │   └── If ن appears instead → run word-start correction
   └── Spot-check: does the university name match a known KRG university?
       └── If not → check KURDISH_UNIVERSITY_NAMES dict (Part 3C)
```

---

## PART 8: TESSERACT OCR SETUP (for server-side extraction)

For highest-accuracy Kurdish Sorani OCR, use Tesseract with the Kurdish language pack before passing text to an AI model.

```bash
# Install
sudo apt install tesseract-ocr tesseract-ocr-ckb

# Single image extraction
tesseract input.png output -l ckb

# With preprocessing for better accuracy (requires ImageMagick)
convert input.png -density 300 -depth 8 -strip -background white \
  -alpha off preprocessed.png
tesseract preprocessed.png output -l ckb --psm 6
```

### 8A — Windows Configuration

On Windows, `pytesseract` cannot find the Tesseract binary automatically. Configure the path explicitly:

```python
import sys
import pytesseract

# Configure path depending on OS
if sys.platform == "win32":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# On Linux/Mac, no config needed if installed via apt/brew
```

Download the Windows installer from: https://github.com/UB-Mannheim/tesseract/wiki
Install the Kurdish Sorani language pack (`ckb`) during setup, or copy `ckb.traineddata` to `C:\Program Files\Tesseract-OCR\tessdata\`.

### 8B — Full Extraction Pipeline

```python
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter

def extract_kurdish_text(image_path: str) -> str:
    """
    Extract Kurdish Sorani text from image with preprocessing and correction.
    Best pipeline for university documents.
    """
    # Open and preprocess
    img = Image.open(image_path)

    # Increase contrast for better OCR
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)

    # Convert to grayscale
    img = img.convert('L')

    # Extract with Kurdish language model
    raw_text = pytesseract.image_to_string(
        img,
        lang='ckb',
        config='--psm 6 --oem 3'
    )

    # Apply post-processing corrections
    corrected = strip_invisible_chars(raw_text)
    corrected = correct_kurdish_ocr(corrected)
    corrected = correct_university_name(corrected)

    return corrected
```

### 8C — Kurdish NLP Library (Advanced Normalization)

For normalization beyond character-level OCR correction, use the `kurdish` package. It handles zero-width characters, Arabic letter variants, punctuation, and numeral conversion in one pass.

```bash
pip install kurdish
```

```python
from kurdish import normalize

def normalize_kurdish_text(text: str) -> str:
    """
    Full normalization pipeline for Kurdish Sorani text.
    Full pipeline order:
      1. strip_invisible_chars   — remove ZW and BiDi control characters
      2. correct_kurdish_ocr     — fix character-level substitutions (ك→ک etc.)
      3. correct_university_name — fix entity-level proper noun misreads
      4. normalize_kurdish       — normalize variants, punctuation, numerals
    """
    text = strip_invisible_chars(text)       # Part 6B — remove invisible chars
    text = correct_kurdish_ocr(text)          # Part 3A — fix substitution errors
    text = correct_university_name(text)      # Part 3C — fix university name misreads
    text = normalize.normalize_kurdish(text)  # kurdish lib — full normalization
    return text
```

**Note:** `hazm` is Persian/Farsi only and does NOT support Kurdish Sorani. Use `kurdish` instead.

---

## PART 9: DATABASE STORAGE RULES (EPU / PostgreSQL)

This section is specific to storing Kurdish Sorani text in the EPU MIS database.

### 9A — PostgreSQL (used in this project)

PostgreSQL handles Unicode natively. No special column-level config is needed, but always verify the database was created with UTF-8 encoding:

```sql
-- Verify encoding (should return UTF8)
SHOW server_encoding;

-- Or check from pg_database:
SELECT datname, pg_encoding_to_char(encoding)
FROM pg_database
WHERE datname = 'your_db_name';
```

If the result is not `UTF8`, the database must be recreated — `ALTER DATABASE` cannot change encoding after creation.

```sql
-- Safe check before any Kurdish text insert (run once at app startup)
-- If this fails, Kurdish chars like ڕ and ێ will silently corrupt
DO $$
BEGIN
  IF current_setting('server_encoding') != 'UTF8' THEN
    RAISE EXCEPTION 'Database encoding is not UTF8. Kurdish text will corrupt.';
  END IF;
END;
$$;
```

### 9B — MySQL / MariaDB (if ever migrated)

MySQL's `utf8` charset is only 3 bytes and will **silently corrupt** Kurdish-specific characters like `ڕ` (U+0695) and `ێ` (U+06CE). Always use `utf8mb4`:

```sql
-- Fix existing columns
ALTER TABLE students MODIFY COLUMN name VARCHAR(255)
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

ALTER TABLE subjects MODIFY COLUMN name VARCHAR(255)
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Or fix the entire database at once
ALTER DATABASE your_db_name CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

**Rule:** Never use `utf8` in MySQL for Kurdish text. Always `utf8mb4`.

### 9C — Python Insert Best Practices

Always normalize Kurdish text before inserting into the database:

```python
from kurdish import normalize

def sanitize_kurdish_for_db(text: str) -> str:
    """
    Full pipeline: strip invisible chars → fix OCR substitutions → normalize.
    Call this on any Kurdish text coming from user input, form submissions,
    or document uploads before storing in the database.
    """
    if not text:
        return text
    text = strip_invisible_chars(text)       # remove ZW chars
    text = correct_kurdish_ocr(text)          # fix Arabic substitutions
    text = correct_university_name(text)      # fix university proper noun misreads
    text = normalize.normalize_kurdish(text)  # normalize variants
    return text.strip()

# Usage in Flask route / db.py:
# student_name = sanitize_kurdish_for_db(request.form['name'])
# execute_query("INSERT INTO students (name) VALUES (%s)", (student_name,))
```

---

## SUMMARY: THE 5 RULES EVERY AGENT MUST FOLLOW

1. **Iraqi Kurdish documents are Sorani, not Arabic** — apply Kurdish character set, not Arabic character set.
2. **Never substitute the 10 Kurdish-specific characters** (پ چ ڕ ژ ڤ گ ڵ ێ ۆ ە) with their Arabic lookalikes.
3. **Always use ک (U+06A9), not ك (U+0643)** — this single rule fixes a huge percentage of errors.
4. **Run the corrector after every OCR extraction** — do not trust raw model output for Kurdish text.
5. **Mark unclear characters as [?]** — an honest unknown is better than a confident wrong character.
