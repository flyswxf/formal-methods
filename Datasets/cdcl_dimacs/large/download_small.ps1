# # 基本用法（自动读取同目录下的 track_main_2023.uri）
# .\download_small.ps1

# # 自定义参数
# .\download_small.ps1 -MaxSizeMB 5 -OutDir "D:\my_downloads"


param(
    [string]$UriFile = "$PSScriptRoot\track_main_2023.uri",
    [int]$MaxSizeMB = 10,
    [string]$OutDir = "$PSScriptRoot\downloads"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $UriFile)) {
    Write-Error "URI file not found: $UriFile"
    exit 1
}

if (-not (Test-Path $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
}

$urls = Get-Content $UriFile | Where-Object { $_.Trim() -ne "" }
$total = $urls.Count
$MaxSizeBytes = $MaxSizeMB * 1024 * 1024

Write-Host "Total URLs: $total"
Write-Host "Size limit: ${MaxSizeMB}MB"
Write-Host "Output dir: $OutDir"
Write-Host ""

$filteredUrls = @()
$skippedCount = 0
$unknownCount = 0

for ($i = 0; $i -lt $urls.Count; $i++) {
    $url = $urls[$i].Trim()
    $pct = [math]::Round(($i + 1) / $total * 100, 1)
    Write-Host -NoNewline "`r[$pct%] Checking $($_ = $i + 1; $_)/$total : $url                    "

    try {
        $resp = Invoke-WebRequest -Uri $url -Method Head -UseBasicParsing -TimeoutSec 30
        $cl = $resp.Headers["Content-Length"]

        if ($cl) {
            $size = [long]$cl
            $sizeMB = [math]::Round($size / 1MB, 2)
            if ($size -lt $MaxSizeBytes) {
                Write-Host "`r[OK  ] $url  ($sizeMB MB)                        "
                $filteredUrls += $url
            } else {
                Write-Host "`r[SKIP] $url  ($sizeMB MB >= ${MaxSizeMB}MB)               "
                $skippedCount++
            }
        } else {
            Write-Host "`r[??? ] $url  (no Content-Length, will download)        "
            $filteredUrls += $url
            $unknownCount++
        }
    } catch {
        Write-Host "`r[ERR ] $url  (HEAD failed: $($_.Exception.Message), will download)   "
        $filteredUrls += $url
        $unknownCount++
    }
}

Write-Host ""
Write-Host ""
Write-Host "=== Summary ==="
Write-Host "Total URLs checked: $total"
Write-Host "Will download (< ${MaxSizeMB}MB): $($filteredUrls.Count)"
Write-Host "Skipped (>= ${MaxSizeMB}MB): $skippedCount"
Write-Host "Unknown size: $unknownCount"
Write-Host ""

if ($filteredUrls.Count -eq 0) {
    Write-Host "No URLs to download."
    exit 0
}

$filteredFile = Join-Path $PSScriptRoot "filtered_urls.txt"
$filteredUrls | Set-Content -Path $filteredFile -Encoding UTF8
Write-Host "Filtered URL list saved to: $filteredFile"
Write-Host "(You can resume later with: wget.exe --content-disposition -i `"$filteredFile`" -P `"$OutDir`")"
Write-Host ""

Write-Host "Starting wget download to: $OutDir"
Write-Host ""

wget.exe --content-disposition -i $filteredFile -P $OutDir

Write-Host ""
Write-Host "Done!"
