#!/usr/bin/env bash
set -euo pipefail

echo "=== Knowledge Vault Setup ==="
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "[1/3] Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

echo "[2/3] Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo "[3/3] Initializing database with sample data..."
python3 seed.py

echo ""
echo "✓ Setup complete!"
echo ""
echo "Next steps:"
echo "  source .venv/bin/activate"
echo "  python3 server.py"
echo "  open http://localhost:51420"
echo ""
echo "Or use the CLI:"
echo "  python3 vault.py add 'My Note' 'Content here' --tags demo --type note"
echo "  python3 vault.py search 'note'"
echo "  python3 vault.py stats"
