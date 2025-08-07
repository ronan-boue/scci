# build docker image
docker build -t zeppelin-v2 -f docker/Dockerfile.test.v2.amd64 .
if [ $? -ne 0 ]; then
    echo "Failed to build docker image"
    exit 1
fi

