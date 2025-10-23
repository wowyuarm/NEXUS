#!/bin/bash
# NEXUS Aliases Setup Script
# Run: ./scripts/shell/setup_aliases.sh

NEXUS_DIR="$HOME/projects/NEXUS"
BASHRC="$HOME/.bashrc"

echo "Setting up NEXUS shortcuts..."

# Remove old configurations if exist
sed -i '/# NEXUS Database Manager/d' "$BASHRC" 2>/dev/null
sed -i '\|source.*\.bashrc_nexus|d' "$BASHRC" 2>/dev/null
sed -i '/# NEXUS shortcuts/,/^$/d' "$BASHRC" 2>/dev/null

# Add new configuration
cat >> "$BASHRC" << 'EOF'

# NEXUS shortcuts
alias nexus='cd ~/projects/NEXUS && ./scripts/shell/run.sh'
alias db='cd ~/projects/NEXUS && source .venv/bin/activate && python3 scripts/database_manager.py'
EOF

echo ""
echo "✓ Setup complete!"
echo ""
echo "Next step:"
echo "  source ~/.bashrc"
echo ""
echo "Available commands:"
echo "  nexus    - Start NEXUS (frontend + backend)"
echo "  db       - Database manager"
echo ""

