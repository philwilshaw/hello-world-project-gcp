param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectId,

    [string]$Region = "europe-west1",
    [string]$RepoOwner = "philwilshaw",
    [string]$RepoName = "hello-world-project-gcp"
)

$ErrorActionPreference = "Stop"

Write-Host "Setting active GCP project to $ProjectId..."
gcloud config set project $ProjectId

Write-Host "Creating dev Cloud Build trigger (branch: dev)..."
gcloud builds triggers create github `
    --name="deploy-dev" `
    --repo-owner=$RepoOwner `
    --repo-name=$RepoName `
    --branch-pattern="^dev$" `
    --build-config="cloudbuild.dev.yaml" `
    --region=$Region

Write-Host "Creating prod Cloud Build trigger (branch: main)..."
gcloud builds triggers create github `
    --name="deploy-prod" `
    --repo-owner=$RepoOwner `
    --repo-name=$RepoName `
    --branch-pattern="^main$" `
    --build-config="cloudbuild.prod.yaml" `
    --region=$Region

Write-Host ""
Write-Host "Done. Triggers created:"
Write-Host "  - deploy-dev  -> pushes to dev  deploy hello-world-dev"
Write-Host "  - deploy-prod -> pushes to main deploy hello-world (prod)"
Write-Host ""
Write-Host "If GitHub is not connected yet, run:"
Write-Host "  gcloud builds connections create github ..."
