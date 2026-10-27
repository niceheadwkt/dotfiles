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
    # reset_time 為 ISO 字串（UTC），轉成本地時間
    try:
        from datetime import datetime
        if not v:
            return ""
        dt = datetime.fromisoformat(str(v).strip().replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.astimezone()
        return dt.strftime(fmt)
    except Exception:
        return ""


# quota 鍵名對應的顯示名稱
QUOTA_LABELS = {"gemini-weekly": "gemini 7d", "3p-weekly": "3p 7d"}


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

    # agy 提供剩餘比例 remaining_fraction，換算成已用百分比
    quota = data.get("quota")
    if isinstance(quota, dict):
        for key, q in quota.items():
            if not isinstance(q, dict):
                continue
            rem = q.get("remaining_fraction")
            if rem is None or isinstance(rem, bool):
                continue
            try:
                used = pct((1 - float(rem)) * 100)
            except Exception:
                continue
            r = reset_time(q.get("reset_time"), "%m/%d %H:%M")
            parts.append(QUOTA_LABELS.get(key, key) + " " + used + "%" + (" 重置 " + r if r else ""))

    parts.append("session " + str(data.get("conversation_title") or "-"))
    parts.append("state " + str(data.get("agent_state") or "-"))
    parts.append("account " + str(data.get("email") or "-"))

    sys.stdout.write(" | ".join(parts) + "\n")


try:
    main()
except Exception:
    sys.stdout.write("statusline\n")
