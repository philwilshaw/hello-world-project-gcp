<#
.SYNOPSIS
  Copy the dev database to prod and restart the prod Cloud Run service.

.DESCRIPTION
  1. Snapshots the live dev database to the dev GCS bucket (mark-safe).
  2. Copies app.db, last-safe.db, and writes-enabled to the prod bucket.
  3. Restarts prod so new instances load the copied database from GCS.

  Requires ADMIN_TOKEN — the same value configured on the dev Cloud Run service.

.EXAMPLE
  $env:ADMIN_TOKEN = 'your-token'
  .\scripts\promote-database-to-prod.ps1

.EXAMPLE
  .\scripts\promote-database-to-prod.ps1 -ProjectId hello-world-project-gcp
#>
param(
    [string]$ProjectId = "hello-world-project-gcp",
    [string]$Region = "europe-west1",
    [string]$DevService = "hello-world-dev",
    [string]$ProdService = "hello-world",
    [string]$DevUrl = "https://hello-world-dev-859465631308.europe-west1.run.app",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

function Invoke-GCloud {
    param([Parameter(Mandatory = $true)][string[]]$Args)
    & gcloud.cmd @Args
    if ($LASTEXITCODE -ne 0) {
        throw "gcloud $($Args -join ' ') failed with exit code $LASTEXITCODE"
    }
}

function Invoke-AdminPost {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$Token
    )

    $response = curl.exe -sS --max-time 60 -X POST `
        -H "X-Admin-Token: $Token" `
        -H "Content-Length: 0" `
        $Url

    if (-not $response) {
        throw "Empty response from $Url"
    }

    try {
        return $response | ConvertFrom-Json
    }
    catch {
        throw "Non-JSON response from $Url`: $response"
    }
}

$token = $env:ADMIN_TOKEN
if (-not $token) {
    throw @"
ADMIN_TOKEN is not set.

Set it in PowerShell before running:
  `$env:ADMIN_TOKEN = 'your-token'

The value must match the ADMIN_TOKEN env var on the dev Cloud Run service.
"@
}

$devBucket = "gs://$ProjectId-hello-world-data-dev"
$prodBucket = "gs://$ProjectId-hello-world-data-prod"

Write-Host "Project     : $ProjectId"
Write-Host "Region      : $Region"
Write-Host "Dev bucket  : $devBucket"
Write-Host "Prod bucket : $prodBucket"
Write-Host ""

if (-not $Force) {
    Write-Warning "This will overwrite the production database with the current dev database."
    $answer = Read-Host "Continue? (y/N)"
    if ($answer -notmatch '^[Yy]$') {
        throw "Aborted."
    }
}

Write-Host "Step 1/4: Snapshot dev database to GCS (mark-safe)..."
$markSafeUrl = "$DevUrl/internal/db/mark-safe"
$markSafeResult = Invoke-AdminPost -Url $markSafeUrl -Token $token
if (-not $markSafeResult.ok) {
    throw "mark-safe failed: $($markSafeResult | ConvertTo-Json -Compress)"
}
Write-Host "  $($markSafeResult.message)"

Write-Host "Step 2/4: Copy database files dev -> prod..."
foreach ($object in @("app.db", "last-safe.db", "writes-enabled")) {
    Write-Host "  $object"
    Invoke-GCloud @(
        "storage", "cp",
        "$devBucket/$object",
        "$prodBucket/$object",
        "--project=$ProjectId"
    )
}

Write-Host "Step 3/4: Restart prod Cloud Run service..."
$syncStamp = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
Invoke-GCloud @(
    "run", "services", "update", $ProdService,
    "--region=$Region",
    "--project=$ProjectId",
    "--update-env-vars=DB_SYNC_TS=$syncStamp",
    "--quiet"
)

Write-Host "Step 4/4: Verify prod bucket..."
Invoke-GCloud @("storage", "ls", "$prodBucket/")

Write-Host ""
Write-Host "Done. Database promotion complete."
Write-Host "  Prod service : $ProdService"
Write-Host "  Prod URL     : https://hello-world-859465631308.europe-west1.run.app"
Write-Host ""
Write-Host "Tip: run scripts/setup-db-jobs.sh so dev data is backed up hourly and"
Write-Host "     you rarely need to promote the database manually."
