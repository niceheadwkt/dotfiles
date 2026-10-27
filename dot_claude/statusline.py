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


def quota(data):
    # AGY：quota 可能是 {used_percentage}、{桶名: {used_percentage}} 或 [{used_percentage}]
    q = data.get("quota")
    if isinstance(q, dict):
        if "used_percentage" in q:
            return pct(q.get("used_percentage"))
        for v in q.values():
            if isinstance(v, dict) and "used_percentage" in v:
                return pct(v.get("used_percentage"))
    elif isinstance(q, list) and q and isinstance(q[0], dict):
        return pct(q[0].get("used_percentage"))
    return None


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

    model = get(data, "model", "display_name") or get(data, "model", "id")
    if not model and isinstance(data.get("model"), str):
        model = data["model"]
    model = str(model or "未知模型")
    tier = data.get("plan_tier") or data.get("plan") or data.get("tier")
    if tier and not isinstance(tier, (dict, list)):
        model += " [" + str(tier) + "]"

    cwd = get(data, "workspace", "current_dir") or data.get("cwd") or ""
    cwd = str(cwd).replace("\\", "/").rstrip("/")
    folder = cwd.split("/")[-1] if cwd else ""
    if not folder:
        folder = cwd or "-"

    parts = [model, folder]

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

    q = quota(data)
    if q is not None:
        parts.append("quota " + q + "%")

    parts.append("session " + str(data.get("session_name") or "-"))
    parts.append("agent " + str(get(data, "agent", "name") or "-"))
    parts.append("account " + account())

    sys.stdout.write(" | ".join(parts) + "\n")


try:
    main()
except Exception:
    sys.stdout.write("statusline\n")
