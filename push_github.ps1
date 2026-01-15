# Simple PowerShell script to push to GitHub
# Run: powershell -ExecutionPolicy Bypass -File push_github.ps1

Write-Host "Starting Git push to GitHub..." -ForegroundColor Cyan

# Check if Git is installed
try {
    $null = git --version 2>&1
    Write-Host "Git is installed" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Git is not installed!" -ForegroundColor Red
    Write-Host "Please install Git from: https://git-scm.com/download/win" -ForegroundColor Yellow
    Write-Host "Then run this script again." -ForegroundColor Yellow
    exit 1
}

# Initialize repo if needed
if (-not (Test-Path .git)) {
    Write-Host "Initializing Git repository..." -ForegroundColor Cyan
    git init
}

# Add remote
Write-Host "Adding remote origin..." -ForegroundColor Cyan
git remote remove origin 2>$null
git remote add origin https://github.com/aladinbajra/talk-to-the-book.git

# Add all files
Write-Host "Adding all files..." -ForegroundColor Cyan
git add .

# Commit
Write-Host "Committing changes..." -ForegroundColor Cyan
git commit -m "Initial commit: Complete Talk to the Book production system"

# Set branch to main
Write-Host "Setting branch to main..." -ForegroundColor Cyan
git branch -M main

# Push
Write-Host ""
Write-Host "Pushing to GitHub..." -ForegroundColor Cyan
Write-Host "Please enter your GitHub credentials when prompted:" -ForegroundColor Yellow
Write-Host "- Username: aladinbajra" -ForegroundColor Yellow
Write-Host "- Password: Use Personal Access Token (not password)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Get token from: https://github.com/settings/tokens" -ForegroundColor Yellow
Write-Host ""

git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "SUCCESS! Project pushed to GitHub!" -ForegroundColor Green
    Write-Host "View at: https://github.com/aladinbajra/talk-to-the-book" -ForegroundColor Cyan
    Start-Process "https://github.com/aladinbajra/talk-to-the-book"
} else {
    Write-Host ""
    Write-Host "ERROR: Push failed!" -ForegroundColor Red
    Write-Host "Check your credentials and try again." -ForegroundColor Yellow
}
