---
name: Reverse-Engineering GUID-Based XML Formats
description: Build a GUID→meaning dictionary for proprietary XML (CAD/CAM/PLM) by grepping Class GUIDs and correlating with sibling Value attributes
type: feedback
---

# Reverse-Engineering GUID-Based XML Formats

**Extracted:** 2026-04-13
**Context:** Analyzing proprietary XML formats where field/class identifiers are GUIDs with no documentation

## Problem
Enterprise software (CAD/CAM/PLM) often exports XML where objects and fields are identified by opaque GUIDs instead of human-readable names. Without a reference dictionary, the structure is unreadable.

## Solution
Build a GUID→meaning dictionary by correlating GUIDs with their sibling values:

1. **Grep for all unique Class GUIDs** — these identify object types (operation, transition, equipment, etc.)
2. **For each Class GUID, read the surrounding content** — the human-readable `Value` attributes reveal what the object represents
3. **Build a mapping table** with confidence levels:
   - Multiple examples with same pattern = high confidence
   - Single example = mark as guess with `❓`
4. **Cross-validate with multiple files** — same GUID should mean the same thing across documents

### Technique
```bash
# Step 1: Find all Class GUIDs
grep '"Class"' file.xml | sort -u

# Step 2: For each GUID, find surrounding values
grep -A 20 'Class">GUID_HERE' file.xml | grep 'Value">'
```

### Output format
Present as a table with: GUID (truncated) | Guess | Evidence — so domain experts can confirm/deny.

## When to Use
- Analyzing exports from enterprise software (Вертикаль, Windchill, Teamcenter, etc.)
- No API documentation available
- Need to generate compatible XML programmatically
- Ask domain experts to validate the mapping table before coding