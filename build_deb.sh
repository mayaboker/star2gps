#!/bin/bash
set -e

# Build script for creating Debian package with stdeb
# This script builds the package and adds systemd service support

echo "Building Debian package with stdeb..."

# Clean previous builds
rm -rf deb_dist dist build *.egg-info

# Build source distribution
python3 setup.py sdist

# Use stdeb to create Debian package structure
py2dsc dist/star2gps-*.tar.gz

# Find the generated debian directory
DEBIAN_DIR=$(find deb_dist -name "debian" -type d | head -1)
if [ -z "$DEBIAN_DIR" ]; then
    echo "Error: Could not find generated debian directory"
    exit 1
fi

echo "Found debian directory at: $DEBIAN_DIR"

# Copy systemd service file
if [ -f "debian/star2gps.service" ]; then
    cp debian/star2gps.service "$DEBIAN_DIR/"
    echo "Copied systemd service file"
fi

# Copy and make executable the postinst script
if [ -f "debian/postinst" ]; then
    cp debian/postinst "$DEBIAN_DIR/"
    chmod +x "$DEBIAN_DIR/postinst"
    echo "Copied postinst script"
fi

# Copy and make executable the prerm script
if [ -f "debian/prerm" ]; then
    cp debian/prerm "$DEBIAN_DIR/"
    chmod +x "$DEBIAN_DIR/prerm"
    echo "Copied prerm script"
fi

# Copy and make executable the postrm script
if [ -f "debian/postrm" ]; then
    cp debian/postrm "$DEBIAN_DIR/"
    chmod +x "$DEBIAN_DIR/postrm"
    echo "Copied postrm script"
fi

# Update control file to fix dependencies
CONTROL_FILE="$DEBIAN_DIR/control"
if [ -f "$CONTROL_FILE" ]; then
    # Create a backup
    cp "$CONTROL_FILE" "$CONTROL_FILE.bak"
    
    # Use Python to properly parse and fix the control file
    python3 - "$CONTROL_FILE" << 'PYTHON_SCRIPT'
import sys

control_file = sys.argv[1]

with open(control_file, 'r') as f:
    lines = f.readlines()

new_lines = []
in_pkg = False
depends_inserted = False

for line in lines:
    if line.startswith('Package: python3-star2gps'):
        in_pkg = True
        depends_inserted = False
        new_lines.append(line)
        continue

    if in_pkg:
        if line.startswith('Depends:') or line.startswith('Recommends:'):
            # Skip existing dependency declarations; we'll insert our own
            continue

        if line.startswith('Architecture:'):
            new_lines.append(line)
            if not depends_inserted:
                new_lines.append('Depends: ${misc:Depends}, ${python3:Depends}, python3-pip\n')
                depends_inserted = True
            continue

        if line.startswith('Description:'):
            if not depends_inserted:
                new_lines.append('Depends: ${misc:Depends}, ${python3:Depends}, python3-pip\n')
                depends_inserted = True
            new_lines.append(line)
            in_pkg = False
            continue

    new_lines.append(line)

with open(control_file, 'w') as f:
    f.writelines(new_lines)

print("Updated control file - removed systemd, normalized Depends field")
PYTHON_SCRIPT
    
    echo "Updated control file dependencies"
fi

# Update rules file to install service file
RULES_FILE="$DEBIAN_DIR/rules"
if [ -f "$RULES_FILE" ]; then
    # Check if we need to add service file installation
    if ! grep -q "star2gps.service" "$RULES_FILE"; then
        # Add override to install service file
        cat >> "$RULES_FILE" << 'EOF'

override_dh_install:
	dh_install
	install -D -m 644 debian/star2gps.service debian/python3-star2gps/lib/systemd/system/star2gps.service
EOF
        echo "Updated rules file to install service file"
    fi
fi

# Build the Debian package
cd "$(dirname "$DEBIAN_DIR")"
dpkg-buildpackage -rfakeroot -uc -us

echo ""
echo "Build complete! Debian package should be in the parent directory."
echo "To install: sudo dpkg -i ../python3-star2gps_*.deb"
echo "Or: sudo apt install ../python3-star2gps_*.deb"

