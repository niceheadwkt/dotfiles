# setup-junctions.ps1
# 功能：自動將 ~/.agents/skills 下的所有技能以 Junction 連結至各大 Agent 工具目錄
# 注意：此檔案必須儲存為 UTF-8 with BOM 格式以供 PowerShell 5.1 正常解析
$ErrorActionPreference = "Stop"

$userHome   = [Environment]::GetFolderPath("UserProfile")
$ssotPath   = Join-Path $userHome ".agents\skills"
$clientDirs = @(
    (Join-Path $userHome ".gemini\config\skills"),
    (Join-Path $userHome ".claude\skills"),
    (Join-Path $userHome ".codex\skills"),
    (Join-Path $userHome ".config\opencode\skills")
)

foreach ($dir in $clientDirs) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

$skills = Get-ChildItem -Path $ssotPath -Directory | Where-Object {
    $_.Name -notmatch "^\." -and $_.Name -notin @(".system", "synced", ".trash")
}

foreach ($s in $skills) {
    $skillName = $s.Name
    $sourceDir = $s.FullName

    foreach ($clientDir in $clientDirs) {
        $destDir = Join-Path $clientDir $skillName

        if (Test-Path $destDir) {
            $item = Get-Item $destDir
            if ($item.LinkType -eq "Junction") {
                [System.IO.Directory]::Delete($destDir)
            } else {
                Remove-Item -Path $destDir -Recurse -Force
            }
        }

        New-Item -ItemType Junction -Path $destDir -Target $sourceDir | Out-Null
        Write-Host "已建立 Junction: $skillName -> $clientDir" -ForegroundColor Green
    }
}

Write-Host "`n所有 Agent 技能已成功關聯至中央庫！" -ForegroundColor Cyan