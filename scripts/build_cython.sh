#!/bin/bash
#############################################################
# Build all Cython modules for pizero_bikecomputer
# This script compiles .pyx files to .so shared libraries
# Run this after installation to avoid runtime compilation delays
#############################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Building Cython modules for pizero_bikecomputer..."
echo "Project directory: $PROJECT_DIR"

cd "$PROJECT_DIR"

# Check if we're in a virtual environment
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    echo "⚠️  Warning: No virtual environment detected."
    echo "   It's recommended to run this inside the virtual environment:"
    echo "   source ~/.venv/bin/activate"
    echo ""
    read -p "Continue anyway? [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Exiting."
        exit 0
    fi
fi

# Check for required packages
if ! python3 -c "import Cython" 2>/dev/null; then
    echo "❌ Cython is not installed."
    echo "   Install with: pip install Cython"
    exit 1
fi

if ! python3 -c "import numpy" 2>/dev/null; then
    echo "❌ NumPy is not installed."
    echo "   Install with: pip install numpy"
    exit 1
fi

# Function to build a single Cython module
build_module() {
    local pyx_file="$1"
    local module_dir="$(dirname "$pyx_file")"
    local module_name="$(basename "$pyx_file" .pyx)"
    
    echo ""
    echo "Building: $pyx_file"
    
    cd "$module_dir"
    
    # Determine compiler flags based on module type
    local extra_flags=""
    if [[ "$module_name" == "mip_helper_pigpio" ]]; then
        extra_flags="-DMIP_DISPLAY_BACKEND_PIGPIO=1"
    elif [[ "$module_name" == "mip_helper_spidev" ]]; then
        extra_flags="-DMIP_DISPLAY_BACKEND_SPIDEV=1"
    fi
    
    # Check for NEON support on ARM
    local arch="$(uname -m)"
    if [[ "$arch" == "aarch64" ]]; then
        extra_flags="$extra_flags -DNEON_64=1"
    fi
    
    # Build the module
    python3 << EOF
import sys
from distutils.core import setup, Extension
from Cython.Build import cythonize
import numpy

ext_modules = cythonize(
    Extension(
        "${module_name}",
        ["${module_name}.pyx"],
        extra_compile_args=["-O3", "-std=c++17"] if "${module_name}".endswith("_pigpio") or "${module_name}".endswith("_spidev") else ["-O3"],
        extra_link_args=[],
        language="c++" if "${module_name}".endswith("_pigpio") or "${module_name}".endswith("_spidev") else "c",
    ),
    compiler_directives={'language_level': '3'},
)

setup(
    name="${module_name}",
    ext_modules=ext_modules,
    include_dirs=[numpy.get_include()],
    script_args=['build_ext', '--inplace']
)
EOF

    if [[ $? -eq 0 ]]; then
        echo "✅ Built: $module_name"
        # Move .so file to current directory if it was placed in build/
        if [[ -d "build" ]]; then
            find build -name "${module_name}*.so" -exec mv {} . \; 2>/dev/null || true
        fi
    else
        echo "❌ Failed to build: $module_name"
        return 1
    fi
    
    cd "$PROJECT_DIR"
}

# Build all Cython modules
echo ""
echo "=== Display Modules ==="
build_module "modules/display/cython/mip_helper.pyx"
build_module "modules/display/cython/mip_helper_pigpio.pyx"
build_module "modules/display/cython/mip_helper_spidev.pyx"

echo ""
echo "=== Logger Modules ==="
build_module "modules/logger/cython/logger_fit.pyx"

echo ""
echo "=== Utility Modules ==="
build_module "modules/utils/_crdp.pyx"

echo ""
echo "=== Cleanup ==="
# Clean up build artifacts
find modules -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
find modules -type f -name "*.c" -o -name "*.cpp" | while read f; do
    # Only delete .c/.cpp files if corresponding .so exists
    base="${f%.*}"
    if ls "${base}"*.so 1> /dev/null 2>&1; then
        rm -f "$f"
        echo "Cleaned: $f"
    fi
done

echo ""
echo "✅ All Cython modules built successfully!"
echo ""
echo "Built .so files:"
find modules -name "*.so" -type f | while read f; do
    echo "  - $f ($(du -h "$f" | cut -f1))"
done
