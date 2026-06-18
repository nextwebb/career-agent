#!/bin/bash
# integration_test.sh — Real PDF generation integration test
#
# This test validates the entire CV/CL generation pipeline:
# 1. Creates test profile and role configs
# 2. Runs the PDF generation script
# 3. Verifies PDF outputs exist and are valid
#
# Run: bash tests/integration_test.sh

set -e  # Exit on first error
set -u  # Exit on undefined variable

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"
TMP_WORKSPACE="$(mktemp -d)"
trap 'rm -rf "$TMP_WORKSPACE"' EXIT

PYTHON_BIN=""
for candidate in python python3 python3.12 python3.11 python3.10; do
    if command -v "$candidate" >/dev/null 2>&1; then
        if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
            PYTHON_BIN="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "❌ ERROR: Python 3.10+ is required"
    exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Integration Test: PDF Generation Pipeline"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ──────────────────────────────────────────────────────────────────────────────
# 1. Setup: Verify dependencies
# ──────────────────────────────────────────────────────────────────────────────
echo ""
echo "1️⃣  Checking dependencies..."

if ! "$PYTHON_BIN" -c "import reportlab" 2>/dev/null; then
    echo "❌ ERROR: reportlab not installed"
    echo "   Run: pip install -r requirements.txt"
    exit 1
fi
echo "   ✓ reportlab installed"

if ! "$PYTHON_BIN" -c "import pypdf" 2>/dev/null; then
    echo "❌ ERROR: pypdf not installed"
    echo "   Run: pip install -r requirements.txt"
    exit 1
fi
echo "   ✓ pypdf installed"

# ──────────────────────────────────────────────────────────────────────────────
# 2. Setup: Prepare test data
# ──────────────────────────────────────────────────────────────────────────────
echo ""
echo "2️⃣  Preparing test data..."

mkdir -p "$TMP_WORKSPACE/roles" "$TMP_WORKSPACE/generated"
cp tests/fixtures/non_pii/profile.synthetic.json "$TMP_WORKSPACE/profile.json"
cp tests/fixtures/non_pii/roles/synthetic_quality_gate_pass.json \
    "$TMP_WORKSPACE/roles/synthetic_quality_gate_pass.json"
echo "   ✓ synthetic non-PII workspace ready: $TMP_WORKSPACE"

# ──────────────────────────────────────────────────────────────────────────────
# 3. Run: Generate PDFs
# ──────────────────────────────────────────────────────────────────────────────
echo ""
echo "3️⃣  Generating PDFs..."

(
    cd "$TMP_WORKSPACE"
    "$PYTHON_BIN" "$ROOT_DIR/src/generate_application.py" --role synthetic_quality_gate_pass \
        | tee "$TMP_WORKSPACE/generate.log"
)

if ! grep -q "Quality gates:" "$TMP_WORKSPACE/generate.log"; then
    echo "❌ ERROR: quality gate summary not found"
    exit 1
fi

if grep -q "FAIL" "$TMP_WORKSPACE/generate.log"; then
    echo "❌ ERROR: synthetic pass fixture failed quality gates"
    cat "$TMP_WORKSPACE/generate.log"
    exit 1
fi

# ──────────────────────────────────────────────────────────────────────────────
# 4. Verify: Check outputs
# ──────────────────────────────────────────────────────────────────────────────
echo ""
echo "4️⃣  Verifying outputs..."

# Find generated PDF files (output_prefix may vary based on role config)
CV_FILES=("$TMP_WORKSPACE"/generated/*_CV.pdf)
CL_FILES=("$TMP_WORKSPACE"/generated/*_CoverLetter.pdf)

if [ ! -f "${CV_FILES[0]}" ]; then
    echo "❌ ERROR: CV PDF not found in generated/"
    ls -la "$TMP_WORKSPACE/generated/"
    exit 1
fi
echo "   ✓ CV PDF exists: ${CV_FILES[0]}"

if [ ! -f "${CL_FILES[0]}" ]; then
    echo "❌ ERROR: Cover Letter PDF not found in generated/"
    ls -la "$TMP_WORKSPACE/generated/"
    exit 1
fi
echo "   ✓ Cover Letter PDF exists: ${CL_FILES[0]}"

# Check file sizes (PDFs should be > 1KB)
CV_SIZE=$(stat -f%z "${CV_FILES[0]}" 2>/dev/null || stat -c%s "${CV_FILES[0]}" 2>/dev/null)
CL_SIZE=$(stat -f%z "${CL_FILES[0]}" 2>/dev/null || stat -c%s "${CL_FILES[0]}" 2>/dev/null)

if [ "$CV_SIZE" -lt 1024 ]; then
    echo "❌ ERROR: CV PDF too small ($CV_SIZE bytes) - likely corrupt"
    exit 1
fi
echo "   ✓ CV PDF size: $CV_SIZE bytes"

if [ "$CL_SIZE" -lt 512 ]; then
    echo "❌ ERROR: Cover Letter PDF too small ($CL_SIZE bytes) - likely corrupt"
    exit 1
fi
echo "   ✓ Cover Letter PDF size: $CL_SIZE bytes"

# Verify PDF magic bytes (should start with %PDF)
if ! head -c 4 "${CV_FILES[0]}" | grep -q "%PDF"; then
    echo "❌ ERROR: CV file is not a valid PDF"
    exit 1
fi
echo "   ✓ CV is valid PDF format"

if ! head -c 4 "${CL_FILES[0]}" | grep -q "%PDF"; then
    echo "❌ ERROR: Cover Letter file is not a valid PDF"
    exit 1
fi
echo "   ✓ Cover Letter is valid PDF format"

# ──────────────────────────────────────────────────────────────────────────────
# 5. Success
# ──────────────────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ All integration tests passed!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Generated files:"
echo "  • ${CV_FILES[0]}"
echo "  • ${CL_FILES[0]}"
echo ""
