#!/usr/bin/env bash
# Fail if any *.jsx / *.js file under frontend/src contains \uXXXX escape
# sequences for Turkish-alphabet characters. JS string literals decode these,
# but JSX text nodes and attribute values do NOT, causing visible breakage
# like "Y\u00f6netimi" instead of "Yönetimi".
#
# Pattern targets only the Turkish character codepoints:
#   ç Ç → \u00e7 \u00c7
#   ö Ö → \u00f6 \u00d6
#   ü Ü → \u00fc \u00dc
#   ğ Ğ → \u011f \u011e
#   ı   → \u0131
#   İ   → \u0130
#   ş Ş → \u015f \u015e
#
# Other escapes (em-dash \u2014, checkmark \u2713, emoji \u{1FXXX},
# combining diacritics \u0300-\u036f) are intentionally NOT flagged.
set -euo pipefail

ROOT="${1:-frontend/src}"
PATTERN='\\u(00[cdef]7|00[cdef]6|00[cdef]c|011[ef]|0130|0131|015[ef])'

if command -v rg >/dev/null 2>&1; then
  MATCHES=$(rg -ni --glob '*.jsx' --glob '*.js' "$PATTERN" "$ROOT" || true)
else
  MATCHES=$(grep -RnEi --include='*.jsx' --include='*.js' "$PATTERN" "$ROOT" || true)
fi

if [ -n "$MATCHES" ]; then
  echo "❌ Found Turkish-character \\uXXXX escapes in JSX/JS files."
  echo "   These render as literal text inside JSX. Replace with the actual character (ö, ı, ü, ç, ş, ğ, İ)."
  echo
  echo "$MATCHES"
  exit 1
fi

echo "✅ No Turkish-character unicode escapes found in $ROOT"
