#!/bin/bash
# Amazon Invoice Analyzer — Smart Installer & Launcher
# • Vérifie Python 3.10+ et Node.js 18+, les installe si absents (via Homebrew)
# • Au premier lancement : sélecteur de dossier graphique, copie des fichiers,
#   installation des dépendances, raccourci Bureau, alias terminal
# • Aux lancements suivants : démarre directement l'application

set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
CONFIG_DIR="$HOME/.config/amazon-analyzer"
CONFIG="$CONFIG_DIR/install_path"

# ── Couleurs ──────────────────────────────────────────────────────────────────
G='\033[0;32m'; Y='\033[1;33m'; B='\033[0;34m'; R='\033[0;31m'
BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "  ${G}✓${NC} $*"; }
info() { echo -e "  ${B}▶${NC} $*"; }
warn() { echo -e "  ${Y}⚠${NC} $*"; }
err()  { echo -e "  ${R}✗${NC} $*"; exit 1; }

clear
echo -e "\n${BOLD}  ╔═══════════════════════════════════════════════╗"
echo    "  ║   📦  Amazon Invoice Analyzer              ║"
echo -e "  ╚═══════════════════════════════════════════════╝${NC}\n"

# ═════════════════════════════════════════════════════════════════════════════
# 1. PYTHON 3.10+
# ═════════════════════════════════════════════════════════════════════════════
_python_ver() {
    "$1" -c "import sys; v=sys.version_info; print(v.major*100+v.minor)" 2>/dev/null || echo 0
}
find_python() {
    for cmd in python3.13 python3.12 python3.11 python3.10 python3 python; do
        command -v "$cmd" &>/dev/null && [ "$(_python_ver "$cmd")" -ge 310 ] && echo "$cmd" && return
    done
}

PYTHON=$(find_python || true)

if [ -z "$PYTHON" ]; then
    warn "Python 3.10+ introuvable — installation automatique..."

    # Homebrew (requis pour installer Python proprement sur macOS)
    if ! command -v brew &>/dev/null; then
        info "Installation de Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        for p in /opt/homebrew/bin /usr/local/bin; do
            [ -f "$p/brew" ] && eval "$($p/brew shellenv)"
        done
    fi

    info "brew install python@3.12..."
    brew install python@3.12 2>/dev/null || brew upgrade python@3.12
    for p in /opt/homebrew/opt/python@3.12/bin /usr/local/opt/python@3.12/bin; do
        [ -d "$p" ] && export PATH="$p:$PATH"
    done
    brew link --overwrite python@3.12 2>/dev/null || true

    PYTHON=$(find_python || true)
    if [ -z "$PYTHON" ]; then
        warn "Installation automatique échouée."
        open "https://www.python.org/downloads/" 2>/dev/null || true
        echo -e "\n  → Installez Python 3.10+ depuis https://python.org/downloads"
        read -rp "     Appuyez sur Entrée une fois Python installé..."
        PYTHON=$(find_python || true)
        [ -z "$PYTHON" ] && err "Python 3.10+ introuvable. Arrêt."
    fi
fi
ok "Python : $($PYTHON --version)"

# ═════════════════════════════════════════════════════════════════════════════
# 2. NODE.JS 18+
# ═════════════════════════════════════════════════════════════════════════════
_node_major() { command -v node &>/dev/null && node -e "process.stdout.write(process.versions.node.split('.')[0])" 2>/dev/null || echo 0; }

if [ "$(_node_major)" -lt 18 ] 2>/dev/null; then
    warn "Node.js 18+ introuvable — installation automatique..."

    if ! command -v brew &>/dev/null; then
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        for p in /opt/homebrew/bin /usr/local/bin; do
            [ -f "$p/brew" ] && eval "$($p/brew shellenv)"
        done
    fi

    info "brew install node@20..."
    brew install node@20 2>/dev/null || brew upgrade node@20
    for p in /opt/homebrew/opt/node@20/bin /usr/local/opt/node@20/bin; do
        [ -d "$p" ] && export PATH="$p:$PATH"
    done
    brew link --overwrite node@20 2>/dev/null || true

    if [ "$(_node_major)" -lt 18 ] 2>/dev/null; then
        warn "Installation automatique échouée."
        open "https://nodejs.org/downloads/" 2>/dev/null || true
        echo -e "\n  → Installez Node.js 18+ depuis https://nodejs.org/downloads"
        read -rp "     Appuyez sur Entrée une fois Node.js installé..."
        [ "$(_node_major)" -lt 18 ] 2>/dev/null && err "Node.js 18+ introuvable. Arrêt."
    fi
fi
ok "Node.js : $(node --version)"

# ═════════════════════════════════════════════════════════════════════════════
# 3. PREMIÈRE INSTALLATION (sélecteur de dossier + copie + deps + raccourcis)
# ═════════════════════════════════════════════════════════════════════════════
INSTALL_DIR=""
[ -f "$CONFIG" ] && INSTALL_DIR=$(cat "$CONFIG")
[ -n "$INSTALL_DIR" ] && [ ! -d "$INSTALL_DIR" ] && INSTALL_DIR=""

if [ -z "$INSTALL_DIR" ]; then
    echo ""
    info "Première installation — choisissez le dossier de destination :"
    echo ""

    # Sélecteur de dossier graphique (AppleScript)
    CHOSEN=$(osascript 2>/dev/null <<'APPLESCRIPT'
try
    set f to choose folder with prompt "Où installer Amazon Invoice Analyzer ?" ¬
             default location (path to home folder)
    return POSIX path of f
on error
    return ""
end try
APPLESCRIPT
    )
    [ -z "$CHOSEN" ] && CHOSEN="$HOME/"
    INSTALL_DIR="${CHOSEN%/}/Amazon Invoice Analyzer"

    info "Copie des fichiers vers : $INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"
    rsync -a \
        --exclude='node_modules/' --exclude='__pycache__/' \
        --exclude='.git/' --exclude='*.pyc' --exclude='.DS_Store' \
        --exclude='.claude/' --exclude='docs/' \
        "$SRC/" "$INSTALL_DIR/"
    chmod +x "$INSTALL_DIR/start.sh"
    ok "Fichiers copiés"

    # Dépendances Python
    info "Installation des dépendances Python (première fois uniquement)..."
    cd "$INSTALL_DIR/backend"
    $PYTHON -m pip install -r requirements.txt -q
    $PYTHON -m playwright install chromium 2>/dev/null || $PYTHON -m playwright install chromium
    ok "Dépendances Python"

    # Dépendances Node
    info "Installation des dépendances Node.js..."
    cd "$INSTALL_DIR/frontend"
    npm install --silent
    ok "Dépendances Node.js"

    # ── Raccourci Bureau (.app) ────────────────────────────────────────────
    APP="$HOME/Desktop/Amazon Analyzer.app"
    mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

    # Génère le launcher en remplaçant INSTALL_DIR
    sed "s|__INSTALL_DIR__|$INSTALL_DIR|g" > "$APP/Contents/MacOS/launcher" <<'LAUNCHER_TEMPLATE'
#!/bin/bash
INSTALL_DIR="__INSTALL_DIR__"
if lsof -ti:8000 &>/dev/null && lsof -ti:5173 &>/dev/null; then
    open http://localhost:5173
    osascript -e 'display notification "Amazon Analyzer est déjà en cours." with title "Amazon Analyzer 📦"'
    exit 0
fi
osascript <<APPLESCRIPT
tell application "Terminal"
    activate
    do script "cd '$INSTALL_DIR' && ./start.sh"
end tell
APPLESCRIPT
LAUNCHER_TEMPLATE
    chmod +x "$APP/Contents/MacOS/launcher"

    cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key><string>launcher</string>
    <key>CFBundleName</key><string>Amazon Analyzer</string>
    <key>CFBundleDisplayName</key><string>Amazon Analyzer</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST
    ok "Raccourci créé sur le Bureau"

    # ── Alias terminal ─────────────────────────────────────────────────────
    ALIAS_LINE="alias factures=\"cd '$INSTALL_DIR' && ./start.sh\""
    for rc in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.bash_profile"; do
        [ -f "$rc" ] && ! grep -q "alias factures=" "$rc" && {
            printf '\n# Amazon Invoice Analyzer\n%s\n' "$ALIAS_LINE" >> "$rc"
        }
    done
    ok "Alias 'factures' ajouté au terminal"

    # ── Sauvegarde du chemin d'installation ──────────────────────────────
    mkdir -p "$CONFIG_DIR"
    echo "$INSTALL_DIR" > "$CONFIG"

    echo ""
    echo -e "  ${G}${BOLD}╔═══════════════════════════════════════════════╗"
    echo    "  ║  ✅  Installation terminée !                ║"
    echo    "  ║  • Raccourci : Bureau → Amazon Analyzer     ║"
    echo    "  ║  • Terminal  : tapez 'factures'             ║"
    echo -e "  ╚═══════════════════════════════════════════════╝${NC}"
    echo ""
    sleep 1
fi

# ═════════════════════════════════════════════════════════════════════════════
# 4. LANCEMENT
# ═════════════════════════════════════════════════════════════════════════════
# Si déjà en cours, ouvrir le navigateur uniquement
if lsof -ti:8000 &>/dev/null && lsof -ti:5173 &>/dev/null; then
    ok "Application déjà en cours — ouverture du navigateur"
    open http://localhost:5173
    exit 0
fi

info "Démarrage du backend (port 8000)..."
cd "$INSTALL_DIR/backend"
$PYTHON -m uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

info "Démarrage du frontend (port 5173)..."
cd "$INSTALL_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

sleep 3
open http://localhost:5173
echo ""
ok "Application disponible sur http://localhost:5173"
echo -e "  ${BOLD}Ctrl+C pour arrêter.${NC}\n"

trap "echo ''; info 'Arrêt…'; kill \$BACKEND_PID \$FRONTEND_PID 2>/dev/null; exit 0" EXIT INT TERM
wait
