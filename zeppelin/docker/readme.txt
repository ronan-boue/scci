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

PEPC (RPC)
az login
az account set --subscription 622b2ddb-475f-4814-a9c6-129441b598ac
az acr login -n crrpcdev01 --subscription 622b2ddb-475f-4814-a9c6-129441b598ac

scripts/build.sh

docker tag zeppelin crrpcdev01.azurecr.io/zeppelin:v1.24
docker push crrpcdev01.azurecr.io/zeppelin:v1.24

BATR (IBR)
az account set --subscription a02105bb-b363-47c0-b472-838a59364134
az acr login -n acrinodev01 --subscription a02105bb-b363-47c0-b472-838a59364134
docker tag zeppelin acrinodev01.azurecr.io/ibr-v2/zeppelin:v1.20
docker push acrinodev01.azurecr.io/ibr-v2/zeppelin:v1.20
