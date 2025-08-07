#!/bin/bash

# Script pour installer les packages Python localement
# et les préparer pour la copie dans le conteneur Docker

echo "Installation des packages Python pour synciot..."

# Créer le répertoire pour les packages locaux
PACKAGE_DIR="./synciot/local_packages"
mkdir -p "$PACKAGE_DIR"

# Installer les packages dans le répertoire local
pip install --target "$PACKAGE_DIR" --no-cache-dir -r ./synciot/requirements.txt

echo "Packages installés dans $PACKAGE_DIR"
echo "Contenu du répertoire:"
ls -la "$PACKAGE_DIR"
