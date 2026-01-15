# PowerShell script për të instaluar Git dhe bërë push automatikisht
# Ekzekuto: powershell -ExecutionPolicy Bypass -File auto_push_to_github.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Auto Push në GitHub - Talk to the Book" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Kontrollo nëse Git është i instaluar
$gitInstalled = $false
try {
    $gitVersion = git --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        $gitInstalled = $true
        Write-Host "[✓] Git është i instaluar: $gitVersion" -ForegroundColor Green
    }
} catch {
    $gitInstalled = $false
}

# Nëse Git nuk është i instaluar, provo ta instalosh
if (-not $gitInstalled) {
    Write-Host "[!] Git nuk është i instaluar!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Ju lutem instalo Git manualisht:" -ForegroundColor Yellow
    Write-Host "1. Shkarko nga: https://git-scm.com/download/win" -ForegroundColor Yellow
    Write-Host "2. Instalo dhe rihape terminalin" -ForegroundColor Yellow
    Write-Host "3. Ekzekuto këtë skedar përsëri" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Ose përdor GitHub Desktop: https://desktop.github.com/" -ForegroundColor Yellow
    Write-Host ""
    
    # Provo të hapësh link-un për download
    $response = Read-Host "Dëshiron të hapësh link-un për download? (y/n)"
    if ($response -eq "y" -or $response -eq "Y") {
        Start-Process "https://git-scm.com/download/win"
    }
    
    exit 1
}

# Kontrollo nëse jemi në një Git repository
if (-not (Test-Path .git)) {
    Write-Host "[1/6] Initializing Git repository..." -ForegroundColor Cyan
    git init
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[✗] Dështoi inicializimi i Git repository" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[1/6] Git repository ekziston tashmë" -ForegroundColor Green
}

# Shto remote origin
Write-Host "[2/6] Shtimi i remote origin..." -ForegroundColor Cyan
git remote remove origin 2>$null
git remote add origin https://github.com/aladinbajra/talk-to-the-book.git
if ($LASTEXITCODE -ne 0) {
    Write-Host "[✗] Dështoi shtimi i remote" -ForegroundColor Red
    exit 1
}
Write-Host "[✓] Remote origin u shtua" -ForegroundColor Green

# Shto të gjitha files
Write-Host "[3/6] Shtimi i të gjitha files..." -ForegroundColor Cyan
git add .
if ($LASTEXITCODE -ne 0) {
    Write-Host "[✗] Dështoi shtimi i files" -ForegroundColor Red
    exit 1
}
Write-Host "[✓] Files u shtuan" -ForegroundColor Green

# Commit
Write-Host "[4/6] Commit changes..." -ForegroundColor Cyan
$commitMessage = "Initial commit: Complete Talk to the Book production system"
git commit -m $commitMessage
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] Commit dështoi - mund të jetë se nuk ka changes të reja" -ForegroundColor Yellow
    Write-Host "    Duke vazhduar me push..." -ForegroundColor Yellow
} else {
    Write-Host "[✓] Commit u bë me sukses" -ForegroundColor Green
}

# Set branch në main
Write-Host "[5/6] Vendosja e branch në main..." -ForegroundColor Cyan
git branch -M main
Write-Host "[✓] Branch u vendos në main" -ForegroundColor Green

# Push
Write-Host "[6/6] Push në GitHub..." -ForegroundColor Cyan
Write-Host ""
Write-Host "Ju lutem vendosni credentials:" -ForegroundColor Yellow
Write-Host "- Username: aladinbajra" -ForegroundColor Yellow
Write-Host "- Password: Përdor Personal Access Token (jo password)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Nëse nuk keni Personal Access Token:" -ForegroundColor Yellow
Write-Host "1. Shko në: https://github.com/settings/tokens" -ForegroundColor Yellow
Write-Host "2. Kliko 'Generate new token (classic)'" -ForegroundColor Yellow
Write-Host "3. Zgjidh scope: repo" -ForegroundColor Yellow
Write-Host "4. Kopjo token-in dhe përdore si password" -ForegroundColor Yellow
Write-Host ""

git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "SUCCESS! Projekti u push-ua me sukses!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Shiko në: https://github.com/aladinbajra/talk-to-the-book" -ForegroundColor Cyan
    Write-Host ""
    
    # Hap browser
    Start-Process "https://github.com/aladinbajra/talk-to-the-book"
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "ERROR: Push dështoi!" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Kontrollo:" -ForegroundColor Yellow
    Write-Host "1. A keni credentials të sakta?" -ForegroundColor Yellow
    Write-Host "2. A keni Personal Access Token nëse përdorni HTTPS?" -ForegroundColor Yellow
    Write-Host "3. A keni internet connection?" -ForegroundColor Yellow
    Write-Host ""
}
