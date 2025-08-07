# build docker image
# docker build --no-cache -t synciot-rci -f docker/Dockerfile.webapp.amd64 .
docker build -t synciot-rci -f docker/Dockerfile.webapp.amd64 .
if [ $? -ne 0 ]; then
    echo "Failed to build docker image"
    exit 1
fi
docker images
