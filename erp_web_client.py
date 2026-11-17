# -*- coding: utf-8 -*-
import sys
import json
import time
import urllib.request
import urllib.error
import urllib.parse
import csv
import io
import os
import websocket

CDP_PORT = 9222
# 主機設定：預設正式機；加 --test 參數改查測試機
# 以完整網址比對命令中心分頁，避免正式機、測試機分頁同時開著時連錯主機
HOSTS = {
    "prod": ("正式機", "erp.chsteel.com.tw"),
    "test": ("測試機", "test.chsteel.com.tw"),
}
ENV = "prod"

def target_url_key():
    return f"{HOSTS[ENV][1]}/erp/ds/jsp/dsjjsql.jsp"

def default_sql_url():
    return f"http://{target_url_key()}"

# 動態取得當前使用者的家目錄，避免寫死工號路徑
USER_HOME = os.path.expanduser("~")
OUTPUT_FILE = os.path.join(USER_HOME, "query_output.txt")
EXPORT_DIR = r"D:\temp\query_results" if os.path.exists("D:\\") else os.path.join(USER_HOME, "query_results")

def get_tab_list():
    for host in ["[::1]", "localhost", "127.0.0.1"]:
        try:
            url = f"http://{host}:{CDP_PORT}/json/list"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception:
            continue
    return None

def create_tab(target_url):
    for host in ["[::1]", "localhost", "127.0.0.1"]:
        try:
            url = f"http://{host}:{CDP_PORT}/json/new?{urllib.parse.quote(target_url, safe=':/?=&')}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}, method="PUT")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception:
            try:
                url = f"http://{host}:{CDP_PORT}/json/new?{target_url}"
                with urllib.request.urlopen(url, timeout=3) as resp:
                    return json.loads(resp.read().decode('utf-8'))
            except Exception:
                continue
    return None

def send_cdp_eval(ws, expression, await_promise=False):
    req_id = int(time.time() * 1000) % 1000000
    msg = {
        "id": req_id,
        "method": "Runtime.evaluate",
        "params": {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": await_promise
        }
    }
    ws.send(json.dumps(msg))
    
    start_time = time.time()
    while time.time() - start_time < 10:
        raw_res = ws.recv()
        res = json.loads(raw_res)
        if res.get("id") == req_id:
            result_obj = res.get("result", {}).get("result", {})
            return result_obj.get("value")
    return None

def execute_sql_on_web(sql_query, row_limit=0):
    # 1. 唯讀安全防護：正式機僅允許 SELECT / WITH 查詢
    cleaned_sql = sql_query.strip().upper()
    if not (cleaned_sql.startswith("SELECT") or cleaned_sql.startswith("WITH")):
        print(f"[安全警示] {HOSTS[ENV][0]}查詢僅限 SELECT / WITH 唯讀查詢，已攔截執行。")
        return False, "FORBIDDEN_SQL_WRITE"

    # 2. 檢查 CDP 是否可連線
    tabs = get_tab_list()
    if tabs is None:
        print("[錯誤] 無法連線至瀏覽器遠端偵錯埠 (Port 9222)。")
        print("請確認是否已透過桌面「啟動正式機ERP(AI連線模式)」捷徑開啟瀏覽器！")
        return False, "CDP_CONNECTION_ERROR"

    # 3. 尋找或開啟命令中心分頁
    target_tab = None
    for tab in tabs:
        url = tab.get("url", "")
        if tab.get("type") == "page" and target_url_key() in url:
            target_tab = tab
            break

    if not target_tab:
        print(f"[提示] 未發現已開啟的{HOSTS[ENV][0]}命令中心，正在自動開啟新分頁：{default_sql_url()}...")
        target_tab = create_tab(default_sql_url())
        if not target_tab:
            print("[錯誤] 自動開啟命令中心分頁失敗，請手動在瀏覽器開啟。")
            return False, "FAILED_TO_CREATE_TAB"
        time.sleep(1.5)

    print(f"[主機] {HOSTS[ENV][0]}（{HOSTS[ENV][1]}）")
    ws_url = target_tab.get("webSocketDebuggerUrl")
    if not ws_url:
        print("[錯誤] 未能取得分頁的 WebSocket 調試位址。")
        return False, "NO_WS_URL"

    # 4. 連線 WebSocket 操控分頁
    try:
        urls_to_try = [ws_url]
        if "localhost" in ws_url:
            urls_to_try.append(ws_url.replace("localhost", "[::1]"))
            urls_to_try.append(ws_url.replace("localhost", "127.0.0.1"))
        elif "127.0.0.1" in ws_url:
            urls_to_try.append(ws_url.replace("127.0.0.1", "[::1]"))
            urls_to_try.append(ws_url.replace("127.0.0.1", "localhost"))

        ws = None
        for u in urls_to_try:
            try:
                ws = websocket.create_connection(u, timeout=5, suppress_origin=True)
                break
            except Exception:
                continue
        if not ws:
            raise Exception(f"無法建立 WebSocket 連線至 {ws_url}")
    except Exception as e:
        print(f"[錯誤] 連線分頁 WebSocket 失敗: {e}")
        return False, str(e)

    try:
        escaped_sql = json.dumps(sql_query)
        
        # 注入執行 JavaScript：填入 SQL、選擇 CSV 格式 (Type=1)、提交表單
        js_submit = f'''
        (function() {{
            var sqlArea = document.getElementById('SqlStr') || document.querySelector("textarea[name='SqlStr']");
            if (!sqlArea) return "NO_SQL_FIELD";
            sqlArea.value = {escaped_sql};
            
            var radioCsv = document.querySelector("input[name='Type'][value='1']");
            if (radioCsv) radioCsv.checked = true;
            
            var rowSizeInput = document.querySelector("input[name='RowSize']");
            if (rowSizeInput) rowSizeInput.value = "{row_limit}";
            
            if (document.forms['form1']) {{
                document.forms['form1'].submit();
                return "SUBMITTED";
            }}
            return "NO_FORM";
        }})();
        '''
        
        res = send_cdp_eval(ws, js_submit)
        if res != "SUBMITTED":
            print(f"[警告] 表單提交回傳狀態: {res}")
            if res == "NO_SQL_FIELD":
                return False, "請確認分頁是否處於登入狀態並停留在命令中心頁面。"

        # 等待網頁載入與查詢結果完成（最多等 15 秒）
        time.sleep(1.0)
        max_wait = 15.0
        start_wait = time.time()
        csv_content = None
        err_message = None

        while time.time() - start_wait < max_wait:
            js_check = '''
            (function() {
                var csvArea = document.getElementById('csvData');
                var msgSpan = document.getElementById('msg');
                var msgText = msgSpan ? msgSpan.innerText : '';
                
                if (csvArea && csvArea.value !== undefined) {
                    return { status: 'DONE', data: csvArea.value, msg: msgText };
                }
                
                if (msgText && (msgText.indexOf('錯誤') !== -1 || msgText.indexOf('Error') !== -1 || msgText.indexOf('禁止') !== -1)) {
                    return { status: 'ERROR', msg: msgText };
                }
                
                return { status: 'WAITING', msg: msgText };
            })();
            '''
            check_res = send_cdp_eval(ws, js_check)
            if isinstance(check_res, dict):
                if check_res.get("status") == "DONE":
                    csv_content = check_res.get("data", "")
                    err_message = check_res.get("msg", "")
                    break
                elif check_res.get("status") == "ERROR":
                    err_message = check_res.get("msg", "")
                    break
            time.sleep(0.5)

        ws.close()

        if csv_content is None and err_message:
            return False, f"查詢發生錯誤: {err_message}"
        if csv_content is None:
            return False, "查詢逾時，未能取得結果。"

        return True, csv_content

    except Exception as e:
        ws.close()
        return False, f"執行例外錯誤: {e}"

def parse_and_save_result(csv_raw):
    os.makedirs(EXPORT_DIR, exist_ok=True)
    
    lines = [line for line in csv_raw.strip().splitlines() if line.strip()]
    if not lines:
        print("[結果] 查詢成功，但無符合條件之資料列 (0 rows returned)。")
        with open(OUTPUT_FILE, "w", encoding="utf-8-sig") as f:
            f.write("0 rows returned.")
        return

    reader = csv.reader(io.StringIO(csv_raw))
    rows = [r for r in reader if any(str(c).strip() for c in r)]

    # 命令中心 csvData 第一列為欄位標題，不計入資料筆數
    header = [str(c).replace("\n", " ") for c in rows[0]] if rows else []
    data_rows = rows[1:]
    total_rows = len(data_rows)

    if total_rows == 0:
        print("[結果] 查詢成功，但無符合條件之資料列 (0 rows returned)。")
        with open(OUTPUT_FILE, "w", encoding="utf-8-sig") as f:
            f.write("0 rows returned.")
        return

    print(f"[成功] 共查詢到 {total_rows} 筆資料。")

    with open(OUTPUT_FILE, "w", encoding="utf-8-sig") as f:
        # <= 20 筆：輸出 Markdown 表格直接呈現在對話中（以實際欄位名稱為表頭）
        if total_rows <= 20:
            f.write("| " + " | ".join(header) + " |\n")
            f.write("| " + " | ".join(["---"] * len(header)) + " |\n")
            for r in data_rows:
                f.write("| " + " | ".join([str(c).replace("\n", " ") for c in r]) + " |\n")
            print(f"已將 {total_rows} 筆結果整理為 Markdown 格式輸出。")
        else:
            # > 20 筆：自動匯出 CSV 檔，僅預覽前 3 筆，徹底省 Token
            now_str = time.strftime("%Y%m%d_%H%M%S")
            csv_path = os.path.join(EXPORT_DIR, f"{ENV}_query_{now_str}.csv")
            with open(csv_path, "w", encoding="cp950", errors="replace", newline="") as out_csv:
                writer = csv.writer(out_csv)
                writer.writerow(header)
                for r in data_rows:
                    writer.writerow(r)

            f.write(f"資料總筆數: {total_rows} 筆（已超過 20 筆限制）\n")
            f.write(f"完整資料已匯出至: {csv_path}\n\n")
            f.write(f"欄位: {header}\n")
            f.write("前 3 筆資料預覽:\n")
            for r in data_rows[:3]:
                f.write(str(r) + "\n")
            print(f"資料筆數超過 20 筆，已自動匯出 CSV 檔：{csv_path}")

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--test" in args:
        ENV = "test"
        args = [a for a in args if a != "--test"]
    if len(args) < 1:
        print('使用方式: python erp_web_client.py [--test] "SELECT ..." [row_limit]')
        sys.exit(1)

    sql_input = args[0]
    limit = int(args[1]) if len(args) > 1 else 0
    
    success, result = execute_sql_on_web(sql_input, limit)
    if success:
        parse_and_save_result(result)
    else:
        print(f"[執行失敗] {result}")
        with open(OUTPUT_FILE, "w", encoding="utf-8-sig") as f:
            f.write(f"ERROR: {result}")
