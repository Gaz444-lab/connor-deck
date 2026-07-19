#!/bin/bash
# One-time setup on Connor's MacBook (same pattern as School Hub / Watch Hub).
# After Xcode CLT / git is installed:
#
#   curl -fsSL https://raw.githubusercontent.com/Gaz444-lab/connor-deck/main/scripts/setup-for-connor.sh | bash
#
set -euo pipefail

REPO_URL="https://github.com/Gaz444-lab/connor-deck.git"
INSTALL_DIR="${HOME}/Documents/connor-deck"
DESKTOP="${HOME}/Desktop"

echo ""
echo "🚀 Setting up Connor's Deck…"
echo ""

if ! command -v git >/dev/null 2>&1; then
  echo "Git is required. Finish Xcode Command Line Tools first, then re-run:"
  echo "  xcode-select --install"
  echo "  curl -fsSL https://raw.githubusercontent.com/Gaz444-lab/connor-deck/main/scripts/setup-for-connor.sh | bash"
  exit 1
fi

if [ -d "${INSTALL_DIR}/.git" ]; then
  echo "Already installed — updating…"
  git -C "$INSTALL_DIR" remote set-url origin "$REPO_URL" 2>/dev/null || true
  git -C "$INSTALL_DIR" pull --ff-only || {
    git -C "$INSTALL_DIR" fetch origin main
    git -C "$INSTALL_DIR" checkout main 2>/dev/null || git -C "$INSTALL_DIR" checkout -B main origin/main
    git -C "$INSTALL_DIR" reset --hard origin/main
  }
else
  echo "Downloading to ${INSTALL_DIR}…"
  mkdir -p "$(dirname "$INSTALL_DIR")"
  git clone "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"
chmod +x *.command launch.sh server.py scripts/*.sh 2>/dev/null || true

# Desktop: Open
cat > "${DESKTOP}/Connor's Deck.command" << EOF
#!/bin/zsh
cd "${INSTALL_DIR}"
exec "${INSTALL_DIR}/Connor's Deck.command"
EOF

# Desktop: Update
cat > "${DESKTOP}/Update Deck.command" << EOF
#!/bin/zsh
cd "${INSTALL_DIR}"
exec "${INSTALL_DIR}/Update Deck.command"
EOF

chmod +x "${DESKTOP}/Connor's Deck.command" "${DESKTOP}/Update Deck.command"
xattr -dr com.apple.quarantine "${DESKTOP}/Connor's Deck.command" 2>/dev/null || true
xattr -dr com.apple.quarantine "${DESKTOP}/Update Deck.command" 2>/dev/null || true
xattr -dr com.apple.quarantine "${INSTALL_DIR}" 2>/dev/null || true

echo ""
echo "✅ Done!"
echo ""
echo "On Connor's Desktop:"
echo "  • Connor's Deck.command   — open the launcher every day"
echo "  • Update Deck.command     — after Dad pushes Deck updates"
echo ""
echo "App folder: ${INSTALL_DIR}"
if [ -f VERSION ]; then echo "Version:    $(cat VERSION)"; fi
echo "Commit:     $(git rev-parse --short HEAD 2>/dev/null || echo n/a)"
echo ""
echo "School Hub, Watch Hub and Mystery Hollow stay in their own folders."
echo "The Deck just launches and updates them for you."
echo ""
echo "First open may ask macOS to allow Terminal — click Open."
echo ""
