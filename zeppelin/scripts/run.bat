docker run --name mqtt -it --entrypoint /bin/sh -p 1883:1883 -v C:\Share:/app/share crrpcdev01.azurecr.io/eclipse-mosquitto:latest
/usr/sbin/mosquitto -c  /mosquitto-no-auth.conf

docker run --rm --name zeppelin1 -it --entrypoint /bin/bash -p 8000:8000 -v C:\Share:/app/share zeppelin --env CONFIG_FILENAME='/config/test-zeppelin.json'
docker exec -it zeppelin1 /bin/bash 

winpty docker run --rm --name zeppelin1 -it --entrypoint bash -p 8000:8000 -v //c/Share:/app/share zeppelin
winpty docker exec -it zeppelin1 bash 
