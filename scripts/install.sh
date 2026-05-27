#!/bin/bash
# PA — 一键安装所有 launchd 定时任务
# 用法: bash scripts/install.sh
#       bash scripts/install.sh --uninstall

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LAUNCHD_DIR="$PROJECT_DIR/launchd"
AGENTS_DIR="$HOME/Library/LaunchAgents"

PLISTS=(
    "com.pa.screen-monitor.plist"
    "com.pa.daily-push.morning.plist"
    "com.pa.daily-push.evening.plist"
    "com.pa.resurfacing.plist"
    "com.pa.weekly-pulse.plist"
    "com.pa.feishu-poll.plist"
)

print_status() {
    echo "  [$1] $2"
}

install() {
    echo "========================================"
    echo "  PA — Installing LaunchAgents"
    echo "========================================"
    echo ""
    echo "项目目录: $PROJECT_DIR"
    echo "安装目标: $AGENTS_DIR"
    echo ""

    # Check uv
    if ! command -v /opt/homebrew/bin/uv &> /dev/null; then
        echo "❌ uv 未安装。请先运行: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi

    # Check project files
    if [ ! -f "$PROJECT_DIR/scripts/daily-push.py" ]; then
        echo "❌ 项目文件不完整，请确认 $PROJECT_DIR 是正确的项目目录"
        exit 1
    fi

    mkdir -p "$AGENTS_DIR"

    for plist in "${PLISTS[@]}"; do
        label="${plist%.plist}"
        src="$LAUNCHD_DIR/$plist"
        dst="$AGENTS_DIR/$plist"

        if [ ! -f "$src" ]; then
            print_status "⚠️" "$plist — 源文件不存在，跳过"
            continue
        fi

        # Unload if already loaded
        if launchctl list | grep -q "$label" 2>/dev/null; then
            launchctl unload "$dst" 2>/dev/null || true
        fi

        # Copy and load
        cp "$src" "$dst"
        launchctl load "$dst"
        print_status "✅" "$plist — 已安装并启动"
    done

    echo ""
    echo "========================================"
    echo "  安装完成!"
    echo "========================================"
    echo ""
    echo "定时任务时间表:"
    echo "  🖥️  Screen Monitor    — KeepAlive 守护进程（每 30 秒截图+OCR）"
    echo "  🌅  早间推送          — 每天 08:00（论文推荐 + Deadline）"
    echo "  🌙  晚间推送          — 每天 21:00（屏幕活动 + 阅读 + 代码）"
    echo "  🔄  知识回顾          — 周一/三/五 10:00"
    echo "  📈  研究脉搏          — 周日 20:00"
    echo "  💬  飞书轮询          — 每 30 分钟"
    echo ""
    echo "验证运行状态:"
    echo "  launchctl list | grep com.pa"
    echo ""
    echo "查看日志:"
    echo "  tail -f /tmp/pa-screen-monitor.log"
    echo "  tail -f /tmp/pa-daily-push-morning.log"
    echo ""
    echo "⚠️  注意: Screen Monitor 需要「屏幕录制」权限"
    echo "  System Settings → Privacy & Security → Screen Recording"
    echo ""
}

uninstall() {
    echo "========================================"
    echo "  PA — Uninstalling LaunchAgents"
    echo "========================================"
    echo ""

    for plist in "${PLISTS[@]}"; do
        label="${plist%.plist}"
        dst="$AGENTS_DIR/$plist"

        if [ -f "$dst" ]; then
            launchctl unload "$dst" 2>/dev/null || true
            rm -f "$dst"
            print_status "🗑️" "$plist — 已卸载"
        else
            print_status "—" "$plist — 未安装，跳过"
        fi
    done

    echo ""
    echo "✅ 所有 PA 定时任务已卸载"
    echo ""
}

status() {
    echo "========================================"
    echo "  PA — LaunchAgent Status"
    echo "========================================"
    echo ""

    for plist in "${PLISTS[@]}"; do
        label="${plist%.plist}"
        if launchctl list | grep -q "$label" 2>/dev/null; then
            pid=$(launchctl list | grep "$label" | awk '{print $1}')
            if [ "$pid" = "-" ]; then
                print_status "⏸️" "$label — 已加载（等待触发）"
            else
                print_status "🟢" "$label — 运行中 (PID: $pid)"
            fi
        else
            print_status "⚪" "$label — 未加载"
        fi
    done
    echo ""
}

case "${1:-}" in
    --uninstall|-u)
        uninstall
        ;;
    --status|-s)
        status
        ;;
    *)
        install
        ;;
esac
