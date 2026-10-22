import sys, json

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def get(d, *keys):
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def pct(v):
    try:
        if v is None or isinstance(v, bool):
            return None
        return str(int(round(float(v))))
    except Exception:
        return None


def reset_time(v, fmt):
    # resets_at 可能是 Unix 秒、毫秒或 ISO 字串，一律轉成本地時間
    try:
        from datetime import datetime
        if v is None or isinstance(v, bool):
            return ""
        if isinstance(v, (int, float)) or str(v).strip().replace(".", "", 1).isdigit():
            ts = float(v)
            if ts > 1e12:
                ts /= 1000
            dt = datetime.fromtimestamp(ts)
        else:
            dt = datetime.fromisoformat(str(v).strip().replace("Z", "+00:00"))
            if dt.tzinfo is not None:
                dt = dt.astimezone()
        return dt.strftime(fmt)
    except Exception:
        return ""


def account():
    try:
        import os
        path = os.path.join(os.path.expanduser("~"), ".claude.json")
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
        return str(get(cfg, "oauthAccount", "emailAddress") or "-")
    except Exception:
        return "-"


def main():
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        data = json.loads(raw) if raw.strip() else {}
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}

    model = get(data, "model", "display_name") or get(data, "model", "id") or "未知模型"

    cwd = get(data, "workspace", "current_dir") or data.get("cwd") or ""
    cwd = str(cwd).replace("\\", "/").rstrip("/")
    folder = cwd.split("/")[-1] if cwd else ""
    if not folder:
        folder = cwd or "-"

    parts = [str(model), folder]

    ctx = pct(get(data, "context_window", "used_percentage"))
    parts.append("context " + (ctx if ctx is not None else "0") + "%")

    five = pct(get(data, "rate_limits", "five_hour", "used_percentage"))
    week = pct(get(data, "rate_limits", "seven_day", "used_percentage"))
    if five is not None:
        r = reset_time(get(data, "rate_limits", "five_hour", "resets_at"), "%H:%M")
        parts.append("5h " + five + "%" + (" 重置 " + r if r else ""))
    if week is not None:
        r = reset_time(get(data, "rate_limits", "seven_day", "resets_at"), "%m/%d %H:%M")
        parts.append("7d " + week + "%" + (" 重置 " + r if r else ""))

    parts.append("session " + str(data.get("session_name") or "-"))
    parts.append("agent " + str(get(data, "agent", "name") or "-"))
    parts.append("account " + account())

    sys.stdout.write(" | ".join(parts) + "\n")


try:
    main()
except Exception:
    sys.stdout.write("statusline\n")
