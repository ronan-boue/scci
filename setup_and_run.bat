@echo off
echo ================================================================
echo Setup complet pour le build Docker avec packages locaux
echo ================================================================

echo.
echo 1. Installation des packages pour iothub_simulator...
call setup_iothub_packages.bat

echo.
echo 2. Installation des packages pour synciot...
call setup_synciot_packages.bat

echo.
echo 3. Build et lancement des conteneurs Docker...
docker-compose -f docker-compose.local.yml up --build

echo.
echo ================================================================
echo Setup terminé!
echo ================================================================
