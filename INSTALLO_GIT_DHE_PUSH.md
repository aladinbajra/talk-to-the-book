# Instalimi i Git dhe Push në GitHub

## ⚠️ Git nuk është i instaluar në sistemin tuaj

Për të bërë push në GitHub, duhet të instalosh Git fillimisht.

## 🚀 Hapi 1: Instalo Git

### Windows:
1. Shkarko Git nga: **https://git-scm.com/download/win**
2. Ekzekuto installer-in
3. Zgjidh "Add Git to PATH" gjatë instalimit
4. Rihape terminalin/Command Prompt

### Ose përdor GitHub Desktop (më e lehtë):
1. Shkarko nga: **https://desktop.github.com/**
2. Instalo dhe login me GitHub account
3. Hape projektin dhe bëj push

## 🚀 Hapi 2: Pas instalimit të Git

Ekzekuto këtë komandë në terminal:

```powershell
powershell -ExecutionPolicy Bypass -File push_github.ps1
```

Ose manualisht:

```bash
git init
git remote add origin https://github.com/aladinbajra/talk-to-the-book.git
git add .
git commit -m "Initial commit: Complete Talk to the Book production system"
git branch -M main
git push -u origin main
```

## 🔐 Hapi 3: Authentication

Kur të kërkohet password, **përdor Personal Access Token**, jo password-in e GitHub:

1. Shko në: **https://github.com/settings/tokens**
2. Kliko **"Generate new token (classic)"**
3. Zgjidh scope: **`repo`**
4. Kliko **"Generate token"**
5. **Kopjo token-in** (do të shfaqet vetëm një herë!)
6. Përdore token-in si password kur të kërkohet

## ✅ Verifikimi

Pas push, shiko në:
**https://github.com/aladinbajra/talk-to-the-book**

## 📝 Alternativë: Upload Manual

Nëse nuk dëshiron të instalosh Git, mund të:
1. Krijo një ZIP file të projektit
2. Shko në GitHub repository
3. Kliko "uploading an existing file"
4. Upload ZIP file-in dhe extract

Por kjo metodë nuk është ideale për version control.

---

**Status**: Git nuk është i instaluar - duhet instalim manual
**Skedari push_github.ps1**: Gati për ekzekutim pas instalimit të Git
