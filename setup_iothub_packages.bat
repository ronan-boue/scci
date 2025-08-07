@echo off
REM Script PowerShell pour installer les packages Python localement
REM et les préparer pour la copie dans le conteneur Docker

echo Installation des packages Python pour iothub_simulator...

REM Créer le répertoire pour les packages locaux
set PACKAGE_DIR=.\iothub_simulator\local_packages
if not exist "%PACKAGE_DIR%" mkdir "%PACKAGE_DIR%"

REM Installer les packages dans le répertoire local
pip install --target "%PACKAGE_DIR%" --no-cache-dir -r .\iothub_simulator\requirements.txt

echo Packages installés dans %PACKAGE_DIR%
echo Contenu du répertoire:
dir "%PACKAGE_DIR%"
