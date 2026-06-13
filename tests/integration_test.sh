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

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Integration Test: PDF Generation Pipeline"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ──────────────────────────────────────────────────────────────────────────────
# 1. Setup: Verify dependencies
# ──────────────────────────────────────────────────────────────────────────────
echo ""
echo "1️⃣  Checking dependencies..."

if ! python3 -c "import reportlab" 2>/dev/null; then
    echo "❌ ERROR: reportlab not installed"
    echo "   Run: pip install -r requirements.txt"
    exit 1
fi
echo "   ✓ reportlab installed"

# ──────────────────────────────────────────────────────────────────────────────
# 2. Setup: Prepare test data
# ──────────────────────────────────────────────────────────────────────────────
echo ""
echo "2️⃣  Preparing test data..."

if [ ! -f "profile.json" ]; then
    echo "   Creating profile.json from example..."
    cp profile.example.json profile.json
else
    echo "   ✓ profile.json already exists"
fi

mkdir -p roles
if [ ! -f "roles/example_role.json" ]; then
    echo "   Creating test role config..."
    cp roles.example/example_role.json roles/example_role.json
else
    echo "   ✓ roles/example_role.json already exists"
fi

mkdir -p generated
echo "   ✓ generated/ directory ready"

# ──────────────────────────────────────────────────────────────────────────────
# 3. Run: Generate PDFs
# ──────────────────────────────────────────────────────────────────────────────
echo ""
echo "3️⃣  Generating PDFs..."

python3 src/generate_application.py --role example_role

# ──────────────────────────────────────────────────────────────────────────────
# 4. Verify: Check outputs
# ──────────────────────────────────────────────────────────────────────────────
echo ""
echo "4️⃣  Verifying outputs..."

# Find generated PDF files (output_prefix may vary based on role config)
CV_FILES=(generated/*_CV.pdf)
CL_FILES=(generated/*_CoverLetter.pdf)

if [ ! -f "${CV_FILES[0]}" ]; then
    echo "❌ ERROR: CV PDF not found in generated/"
    ls -la generated/
    exit 1
fi
echo "   ✓ CV PDF exists: ${CV_FILES[0]}"

if [ ! -f "${CL_FILES[0]}" ]; then
    echo "❌ ERROR: Cover Letter PDF not found in generated/"
    ls -la generated/
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
