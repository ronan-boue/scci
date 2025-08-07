@echo off
REM Script PowerShell pour installer les packages Python localement
REM et les préparer pour la copie dans le conteneur Docker

echo Installation des packages Python pour synciot...

REM Créer le répertoire pour les packages locaux
set PACKAGE_DIR=.\synciot\local_packages
if not exist "%PACKAGE_DIR%" mkdir "%PACKAGE_DIR%"

REM Installer les packages dans le répertoire local
pip install --target "%PACKAGE_DIR%" --no-cache-dir -r .\synciot\requirements.txt

echo Packages installés dans %PACKAGE_DIR%
echo Contenu du répertoire:
dir "%PACKAGE_DIR%"
