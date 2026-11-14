#!${TX_PREFIX:-/usr/local}/files/usr/bin/bash
# ffp: FFP-NIMBUS2-INSTALL content-pipeline bash
# Global Proxy Engine — Self-contained installer
set -e
echo "Installing Global Proxy Engine..."
pip install -r requirements.txt 2>/dev/null || python3 -m pip install -r requirements.txt
echo "Installation complete"
