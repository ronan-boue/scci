# Guide de Setup Docker avec Packages Locaux

Ce guide explique comment résoudre les problèmes SSL lors du build Docker en installant les packages Python localement sur votre machine, puis en les copiant dans les conteneurs.

## Problème résolu

L'erreur `SSLError violation of protocol` lors de l'installation des packages Python dans les conteneurs Docker, causée par les restrictions de proxy/firewall d'entreprise.

## Solution

La solution consiste à :
1. Installer les packages Python sur votre machine locale (qui a accès aux repositories Python)
2. Copier ces packages pré-installés dans les conteneurs Docker
3. Configurer le PYTHONPATH pour utiliser ces packages

## Instructions d'utilisation

### Méthode simple (tout automatique)

1. Exécutez le script complet :
   ```powershell
   .\setup_and_run.bat
   ```

### Méthode manuelle (étape par étape)

1. **Installer les packages localement** :
   ```powershell
   # Pour iothub_simulator
   .\setup_iothub_packages.bat
   
   # Pour synciot
   .\setup_synciot_packages.bat
   ```

2. **Vérifier que les répertoires de packages sont créés** :
   - `./iothub_simulator/local_packages/`
   - `./synciot/local_packages/`

3. **Build et lancer les conteneurs** :
   ```powershell
   docker-compose -f docker-compose.local.yml up --build
   ```

## Fichiers créés

### Nouveaux Dockerfiles
- `iothub_simulator/docker/Dockerfile.local` - Version qui utilise les packages locaux
- `synciot/docker/Dockerfile.webapp.local` - Version qui utilise les packages locaux

### Scripts de setup
- `setup_iothub_packages.bat` - Installe les packages pour iothub_simulator
- `setup_synciot_packages.bat` - Installe les packages pour synciot
- `setup_and_run.bat` - Script complet automatique

### Configuration Docker
- `docker-compose.local.yml` - Version qui utilise les nouveaux Dockerfiles
- `.dockerignore` - Ignore les fichiers inutiles lors du build

## Comment ça marche

1. **Installation locale** : Les scripts `setup_*_packages.bat` utilisent `pip install --target` pour installer les packages dans un répertoire local spécifique.

2. **Copie dans le conteneur** : Les nouveaux Dockerfiles copient le contenu de `./local_packages` dans `/app/lib/python3.12/site-packages` du conteneur.

3. **Configuration PYTHONPATH** : Les Dockerfiles configurent la variable d'environnement `PYTHONPATH` pour que Python trouve les packages dans le nouveau répertoire.

## Avantages

- ✅ Contourne les restrictions SSL/proxy d'entreprise
- ✅ Installation rapide des packages (pas de téléchargement dans le conteneur)
- ✅ Build Docker plus rapide
- ✅ Packages installés une seule fois sur la machine locale

## Nettoyage

Pour nettoyer les packages locaux installés :
```powershell
rmdir /s /q .\iothub_simulator\local_packages
rmdir /s /q .\synciot\local_packages
```

## Dépannage

### Erreur "pip n'est pas reconnu"
Assurez-vous que Python et pip sont installés et dans votre PATH.

### Packages manquants au runtime
Vérifiez que :
1. Les packages sont bien installés dans `./local_packages`
2. Le PYTHONPATH est correctement configuré dans le Dockerfile
3. Les packages sont bien copiés dans le conteneur

### Problème de permissions
Sur Windows, exécutez PowerShell en tant qu'administrateur si nécessaire.
