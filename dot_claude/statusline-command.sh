#!/usr/bin/env bash
# Claude Code 狀態列：使用者@主機 | 資料夾 | 模型 | Context | 5h/7d 用量
input=$(cat)

# 找可用的 Python：略過 WindowsApps 下的 Microsoft Store 空殼
PY=""
for c in python python3 py; do
  p=$(command -v "$c" 2>/dev/null) || continue
  case "$p" in */WindowsApps/*) continue ;; esac
  PY=$p; break
done

# 一次解析 JSON，每個欄位一行輸出（空欄位也保留一行）：模型、資料夾、ctx、5h、7d
if [ -n "$PY" ]; then
  { IFS= read -r model; IFS= read -r dir; IFS= read -r ctx; IFS= read -r five; IFS= read -r week; } < <(
    printf '%s' "$input" | PYTHONIOENCODING=utf-8 "$PY" -c '
import sys, json
try:
    d = json.loads(sys.stdin.buffer.read().decode("utf-8"))
except Exception:
    d = {}
def g(*ks):
    v = d
    for k in ks:
        v = v.get(k) if isinstance(v, dict) else None
    return "" if v is None else str(v)
for v in (g("model", "display_name"),
          g("workspace", "current_dir") or g("cwd"),
          g("context_window", "used_percentage"),
          g("rate_limits", "five_hour", "used_percentage"),
          g("rate_limits", "seven_day", "used_percentage")):
    print(v)
' 2>/dev/null | tr -d '\r')
fi

dir=${dir//\\//}
folder=${dir##*/}
[ -z "$folder" ] && folder=$dir

user=${USERNAME:-$(whoami)}
host=${COMPUTERNAME:-$(hostname)}

out=$(printf '\033[32m%s@%s\033[0m' "$user" "$host")
[ -n "$folder" ] && out="$out $(printf '\033[34m%s\033[0m' "$folder")"
[ -n "$model" ] && out="$out $(printf '\033[36m%s\033[0m' "$model")"
[ -n "$ctx" ] && out="$out $(printf '\033[33mctx:%.0f%%\033[0m' "$ctx")"
[ -n "$five" ] && out="$out $(printf '\033[35m5h:%.0f%%\033[0m' "$five")"
[ -n "$week" ] && out="$out $(printf '\033[35m7d:%.0f%%\033[0m' "$week")"
printf '%s' "$out"
