# build docker image
docker build -t zeppelin -f docker/Dockerfile.test.mqtt.amd64 .
if [ $? -ne 0 ]; then
    echo "Failed to build docker image"
    exit 1
fi
docker rmi $(docker images --filter "dangling=true" -q --no-trunc)
docker images

