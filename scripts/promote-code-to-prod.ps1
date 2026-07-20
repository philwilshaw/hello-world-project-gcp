<#
.SYNOPSIS
  Merge dev into main and push to GitHub to deploy code to production.

.DESCRIPTION
  Cloud Build deploys prod automatically when main is updated.
  This script does not touch the database — use promote-database-to-prod.ps1
  for that.

.EXAMPLE
  .\scripts\promote-code-to-prod.ps1
#>
param(
    [string]$BaseBranch = "main",
    [string]$SourceBranch = "dev"
)

$ErrorActionPreference = "Stop"

function Invoke-Git {
    param([Parameter(Mandatory = $true)][string[]]$Args)
    & git @Args
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Args -join ' ') failed with exit code $LASTEXITCODE"
    }
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

Write-Host "Repository: $repoRoot"
Write-Host "Promoting code: $SourceBranch -> $BaseBranch"
Write-Host ""

$status = & git status --porcelain
if ($status) {
    Write-Warning "You have uncommitted changes. Commit or stash them before promoting."
    $status | ForEach-Object { Write-Host "  $_" }
    $answer = Read-Host "Continue anyway? (y/N)"
    if ($answer -notmatch '^[Yy]$') {
        throw "Aborted."
    }
}

$originalBranch = (& git branch --show-current).Trim()
if (-not $originalBranch) {
    throw "Could not determine the current git branch."
}

try {
    Write-Host "Fetching latest from origin..."
    Invoke-Git @("fetch", "origin", "--prune")

    Write-Host "Checking out $BaseBranch..."
    Invoke-Git @("checkout", $BaseBranch)
    Invoke-Git @("pull", "origin", $BaseBranch)

    Write-Host "Merging origin/$SourceBranch into $BaseBranch..."
    Invoke-Git @("merge", "origin/$SourceBranch", "-m", "Merge $SourceBranch into $BaseBranch for production release.")

    Write-Host "Pushing $BaseBranch to origin..."
    Invoke-Git @("push", "origin", $BaseBranch)

    Write-Host ""
    Write-Host "Done. Code promotion complete."
    Write-Host "  Branch pushed : $BaseBranch"
    Write-Host "  Deploy target : hello-world (prod) via Cloud Build on push to main"
    Write-Host ""
    Write-Host "Check build status:"
    Write-Host "  gcloud builds list --region=europe-west1 --limit=3"
}
finally {
    if ($originalBranch -and $originalBranch -ne $BaseBranch) {
        Write-Host "Returning to branch $originalBranch..."
        Invoke-Git @("checkout", $originalBranch)
    }
}
