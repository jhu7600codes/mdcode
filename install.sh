#!/bin/bash
set -e

RAW="https://raw.githubusercontent.com/jhu7600codes/mdcode/main/source/mdcode.py"
TARGET_PY="/usr/local/lib/mdcode.py"
TARGET_BIN="/usr/local/bin/mdcode"

if command -v mdcode &>/dev/null; then
    echo "mdcode already installed, updating..."
    sudo curl -fsSL "$RAW" -o "$TARGET_PY"
    echo "updated mdcode at $TARGET_PY"
else
    echo "installing mdcode..."
    sudo curl -fsSL "$RAW" -o "$TARGET_PY"
    sudo tee "$TARGET_BIN" > /dev/null << 'WRAPPER'
#!/bin/bash
exec python3 /usr/local/lib/mdcode.py "$@"
WRAPPER
    sudo chmod +x "$TARGET_BIN"
    echo "installed mdcode — try: mdcode run yourfile.md"
fi
