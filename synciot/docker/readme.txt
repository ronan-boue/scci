# DISABLE DOCKER DESKTOP PROXY !!!
#
# .bashrc
export HTTP_PROXY="http://proxysg.hydro.qc.ca:8081/"
export HTTPS_PROXY="http://proxysg.hydro.qc.ca:8081/"
export NO_PROXY=".hydro.qc.ca"
export REQUESTS_CA_BUNDLE=/c/Users/$USERNAME/.tls/cacert-hq-combined.pem
# For cacert-hq-combined.pem, look in attached files in https://confluence.hydro.qc.ca/x/h4MVE
#
# bash
winpty curl -px http://proxysg.hydro.qc.ca:8081 --proxy-ntlm -U $MY_CIP https://ifconfig.co/json

# si az login fail, lancer cette comande: az config set core.encrypt_token_cache=false

# IMPORTANT: Update _version.py with build _version
# -------------------------------------------------

az login
az account set --subscription 622b2ddb-475f-4814-a9c6-129441b598ac
az acr login -n crrcidev01 --subscription 622b2ddb-475f-4814-a9c6-129441b598ac

scripts/build.sh

docker tag synciot-rci crrcidev01.azurecr.io/synciot-rci:v1.4
docker push crrcidev01.azurecr.io/synciot-rci:v1.4
