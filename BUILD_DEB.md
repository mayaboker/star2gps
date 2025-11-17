# Building Debian Package with stdeb

This guide explains how to build a Debian package for star2gps that installs as a systemd service.

## Prerequisites

1. Install required tools:
```bash
sudo apt-get install python3-stdeb python3-all dh-python debhelper
```

2. Activate your virtual environment (if using one):
```bash
source env3.10/bin/activate
```

## Building the Package

### Option 1: Using the Build Script (Recommended)

Simply run the provided build script:

```bash
./build_deb.sh
```

This script will:
1. Clean previous builds
2. Create a source distribution
3. Use stdeb to generate Debian package structure
4. Add systemd service file and scripts
5. Update Debian control and rules files
6. Build the final .deb package

### Option 2: Manual Build

1. Create source distribution:
```bash
python3 setup.py sdist
```

2. Use stdeb to create Debian package:
```bash
py2dsc dist/star2gps-*.tar.gz
```

3. Find the generated debian directory:
```bash
DEBIAN_DIR=$(find deb_dist -name "debian" -type d | head -1)
```

4. Copy service files and scripts:
```bash
cp debian/star2gps.service $DEBIAN_DIR/
cp debian/postinst $DEBIAN_DIR/ && chmod +x $DEBIAN_DIR/postinst
cp debian/prerm $DEBIAN_DIR/ && chmod +x $DEBIAN_DIR/prerm
cp debian/postrm $DEBIAN_DIR/ && chmod +x $DEBIAN_DIR/postrm
```

5. Update control file to add systemd dependency:
```bash
sed -i 's/^Depends: \(.*\)$/Depends: \1, systemd/' $DEBIAN_DIR/control
```

6. Update rules file to install service:
```bash
cat >> $DEBIAN_DIR/rules << 'EOF'

override_dh_install:
	dh_install
	install -D -m 644 debian/star2gps.service debian/python3-star2gps/lib/systemd/system/star2gps.service
EOF
```

7. Build the package:
```bash
cd $(dirname $DEBIAN_DIR)
dpkg-buildpackage -rfakeroot -uc -us
```

## Installing the Package

After building, install the package:

**Recommended method** (automatically resolves dependencies):
```bash
sudo apt install ../python3-star2gps_*.deb
```

**Alternative method** (if using dpkg directly, dependencies must be installed first):
```bash
# Install Python dependencies first
sudo apt-get update
sudo apt-get install python3-pip python3-setuptools

# Then install the package
sudo dpkg -i ../python3-star2gps_*.deb

# If there are dependency issues, fix them:
sudo apt-get install -f
```

The service will automatically:
- Install Python dependencies via pip (if not available as Debian packages)
- Be installed to `/lib/systemd/system/star2gps.service`
- Be enabled to start on boot
- Be started immediately after installation

## Service Management

After installation, you can manage the service using systemctl:

```bash
# Check service status
sudo systemctl status star2gps

# Start the service
sudo systemctl start star2gps

# Stop the service
sudo systemctl stop star2gps

# Restart the service
sudo systemctl restart star2gps

# View logs
sudo journalctl -u star2gps -f
```

## Configuration

The service is configured to run with:
- `--gps`: Enable GPS output
- `--log`: Enable logging
- `--baudrate 9600`: Serial baudrate
- `--port /dev/pts/13`: Serial port

To change these settings, edit `/lib/systemd/system/star2gps.service` and run:
```bash
sudo systemctl daemon-reload
sudo systemctl restart star2gps
```

## Package Structure

The package includes:
- Python module: `star2gps` installed to system Python
- Systemd service: `/lib/systemd/system/star2gps.service`
- Dependencies: All packages from `requirements.txt`

## Troubleshooting

1. **Service fails to start**: Check logs with `sudo journalctl -u star2gps`
2. **Port not found**: Ensure `/dev/pts/13` exists or update the service file
3. **Permission issues**: The service runs as root by default
4. **Build errors**: Ensure all dependencies are installed and virtual environment is activated

