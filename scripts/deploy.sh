#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_REPO="${LOCAL_REPO:-$SCRIPT_DIR/..}"
PI_HOST="${PI_HOST:-}"
PI_PATH="~/pizero_bikecomputer"
LOG_FILE="log/debug.log"
VENV_PYTHON="~/.venv/bin/python"

if [[ -z "$PI_HOST" ]]; then
    echo "Error: PI_HOST not set. Set PI_HOST environment variable or use:"
    echo "  export PI_HOST=user@raspberry-pi-ip"
    echo ""
    echo "Example:"
    echo "  PI_HOST=pi@192.168.1.100 $0 upload"
    exit 1
fi

usage() {
    cat <<EOF
Usage: $0 [OPTIONS] COMMAND

Environment Variables:
    PI_HOST          SSH connection string (e.g., pi@192.168.1.100)
    LOCAL_REPO       Local repository path (default: auto-detected)
    VENV_PYTHON      Path to Python venv (default: ~/.venv/bin/python)

Example:
    export PI_HOST=pi@192.168.1.100
    $0 upload

Commands:
    upload      Upload local repo to Pi (rsync)
    install     Run install.sh on Pi (interactive)
    start       Start the bikecomputer
    stop        Stop the bikecomputer
    logs        Check debug.log for errors
    watch       Tail the debug.log in real-time
    deploy      Full workflow: upload + install + start + check logs

Options:
    -h, --help      Show this help
    --no-install    Skip install step
EOF

    exit 1
}

upload_repo() {
    echo "📤 Uploading repository to Pi..."
    rsync -avz --delete \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.venv' \
        --exclude='logs/*.log' \
        "$LOCAL_REPO/" "$PI_HOST:$PI_PATH/"
    echo "✅ Upload complete"
}

run_install() {
    echo "🔧 Running install.sh on Pi..."
    ssh "$PI_HOST" "cd $PI_PATH && bash install.sh"
}

start_bikecomputer() {
    echo "▶️  Starting pizero_bikecomputer..."
    ssh "$PI_HOST" "cd $PI_PATH && QT_QPA_PLATFORM=offscreen $VENV_PYTHON pizero_bikecomputer.py"
}

stop_bikecomputer() {
    echo "⏹️  Stopping pizero_bikecomputer..."
    ssh "$PI_HOST" "pkill -f pizero_bikecomputer.py || true"
}

check_logs() {
    echo "📜 Checking for errors in debug.log..."
    ssh "$PI_HOST" "grep -i -E '(error|exception|traceback|fail|critical)' $PI_PATH/$LOG_FILE | tail -20" || echo "No errors found"
}

watch_logs() {
    echo "📜 Tailing $LOG_FILE (Ctrl+C to exit)..."
    ssh "$PI_HOST" "tail -f $PI_PATH/$LOG_FILE"
}

deploy() {
    local skip_install="${NO_INSTALL:-false}"
    
    upload_repo
    
    if [[ "$skip_install" != "true" ]]; then
        run_install
    fi
    
    start_bikecomputer
    check_logs
}

NO_INSTALL="false"

COMMAND="${1:-}"

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help) usage ;;
        --no-install) NO_INSTALL="true" ;;
    esac
    shift
done

case "$COMMAND" in
    upload) upload_repo ;;
    install) run_install ;;
    start) start_bikecomputer ;;
    stop) stop_bikecomputer ;;
    logs) check_logs ;;
    watch) watch_logs ;;
    deploy) deploy ;;
    *) usage ;;
esac
