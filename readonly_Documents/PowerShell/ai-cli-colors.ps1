# AI CLI 專屬色彩配置
# 在 PowerShell 輸入 claude、codex、opencode、agy 時，暫時把目前分頁換成該工具的配色，
# 離開（含 Ctrl+C）後自動還原成分頁原本的配色。
# 透過 OSC 4/10/11/12 跳脫序列切換，只在 Windows Terminal（有 WT_SESSION）中作用。
# 由 Windows PowerShell 與 PowerShell 7 的設定檔共同 dot-source 載入。

$AiCliSchemes = @{
    # Solarized Light
    claude   = @{
        fg = '657b83'; bg = 'fdf6e3'; cursor = '586e75'
        palette = '002b36','dc322f','859900','b58900','268bd2','d33682','2aa198','eee8d5',
                  '073642','cb4b16','586e75','657b83','839496','6c71c4','93a1a1','fdf6e3'
    }
    # One Half Dark
    codex    = @{
        fg = 'dcdfe4'; bg = '282c34'; cursor = 'ffffff'
        palette = '282c34','e06c75','98c379','e5c07b','61afef','c678dd','56b6c2','dcdfe4',
                  '5a6374','e06c75','98c379','e5c07b','61afef','c678dd','56b6c2','dcdfe4'
    }
    # Solarized Dark
    opencode = @{
        fg = '839496'; bg = '002b36'; cursor = 'ffffff'
        palette = '002b36','dc322f','859900','b58900','268bd2','d33682','2aa198','eee8d5',
                  '073642','cb4b16','586e75','657b83','839496','6c71c4','93a1a1','fdf6e3'
    }
    # One Half Light 調色盤 + 淺藍背景（Antigravity）
    # 白(7)／亮白(15) 原為 fafafa／ffffff，在淺藍背景上看不清楚，改為深灰
    # 亮黃(11) 原為 e4c07a，對比偏低，改為深金黃
    agy      = @{
        fg = '383a42'; bg = 'e8f0fe'; cursor = '4f525d'
        palette = '383a42','e45649','50a14f','c18301','0184bc','a626a4','0997b3','5c6370',
                  '4f525d','df6c75','98c379','b07d00','61afef','c577dd','56b5c1','383a42'
    }
}

function ConvertTo-OscColor([string]$hex) {
    'rgb:{0}/{1}/{2}' -f $hex.Substring(0, 2), $hex.Substring(2, 2), $hex.Substring(4, 2)
}

function Set-AiCliScheme([string]$name) {
    if (-not $env:WT_SESSION) { return }
    $s = $AiCliSchemes[$name]
    if (-not $s) { return }
    $esc = [char]27; $st = "$esc\"
    $seq = "$esc]10;$(ConvertTo-OscColor $s.fg)$st" +
           "$esc]11;$(ConvertTo-OscColor $s.bg)$st" +
           "$esc]12;$(ConvertTo-OscColor $s.cursor)$st"
    for ($i = 0; $i -lt 16; $i++) {
        $seq += "$esc]4;$i;$(ConvertTo-OscColor $s.palette[$i])$st"
    }
    [Console]::Write($seq)
}

function Reset-AiCliScheme {
    if (-not $env:WT_SESSION) { return }
    $esc = [char]27; $st = "$esc\"
    # 還原調色盤、前景、背景、游標色為分頁設定檔的原始值
    [Console]::Write("$esc]104$st$esc]110$st$esc]111$st$esc]112$st")
}

function Invoke-AiCli([string]$name, [object[]]$cliArgs) {
    # 指定只找外部程式或 .ps1 腳本，避免呼叫到同名的包裝函式自己
    $cmd = Get-Command $name -CommandType Application, ExternalScript -ErrorAction SilentlyContinue |
           Select-Object -First 1
    if (-not $cmd) { Write-Error "找不到指令：$name"; return }
    Set-AiCliScheme $name
    try { & $cmd.Source @cliArgs }
    finally { Reset-AiCliScheme }
}

function claude   { Invoke-AiCli 'claude'   $args }
# claudea 與 claude 共用 Solarized Light（Cream 背景）配色
function claudea  { Invoke-AiCli 'claude'   (@('--dangerously-skip-permissions') + $args) }
function codex    { Invoke-AiCli 'codex'    $args }
function opencode { Invoke-AiCli 'opencode' $args }
function agy      { Invoke-AiCli 'agy'      $args }
# agya 與 agy 共用淺藍背景配色
function agya     { Invoke-AiCli 'agy'      (@('--dangerously-skip-permissions') + $args) }
