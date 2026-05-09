---
name: STEP File Unicode / Cyrillic Decoding
description: ISO 10303-21 STEP files encode non-ASCII as \X2\<UTF-16BE hex>\X0\ — decode by splitting the hex into 4-char chunks per code point
type: feedback
---

# STEP File Unicode / Cyrillic Decoding

**Extracted:** 2026-04-13
**Context:** Parsing STP/STEP files (ISO 10303-21) that contain non-ASCII text (Cyrillic, CJK, etc.)

## Problem
STEP files encode non-ASCII characters in a special format. Searching for Cyrillic text directly (e.g. "Платик") in an STP file returns nothing — the text is encoded.

## Solution
ISO 10303-21 uses `\X2\<UTF-16BE hex pairs>\X0\` encoding for Unicode characters outside ASCII.

Each character is encoded as a 4-digit hex code (UTF-16BE code point):

```
\X2\041F043B043004420438043A\X0\
      ^^^^ ^^^^ ^^^^ ^^^^ ^^^^ ^^^^
       П    л    а    т    и    к
```

Decoding: split hex string into 4-char chunks, convert each to Unicode code point.

```python
import re

def decode_step_unicode(text: str) -> str:
    def replace_match(m):
        hex_str = m.group(1)
        chars = [chr(int(hex_str[i:i+4], 16)) for i in range(0, len(hex_str), 4)]
        return ''.join(chars)
    return re.sub(r'\\X2\\([0-9A-Fa-f]+)\\X0\\', replace_match, text)

# Example
decode_step_unicode(r"2\X2\0412041C\X0\.680.12.61.204")
# → "2ВМ.680.12.61.204"
```

Common Cyrillic ranges: `0410-042F` (А-Я uppercase), `0430-044F` (а-я lowercase).

## When to Use
- Parsing STEP/STP files with Cyrillic or other non-ASCII content
- Searching for Russian text inside STEP geometry files
- Building STP parsers that need to extract metadata (part names, descriptions)