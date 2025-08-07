# See https://github.com/docker/toolbox/issues/673#issuecomment-355275054
# Workaround for Docker for Windows in Git Bash.
export MSYS_NO_PATHCONV=1

function docker() {
    (export MSYS_NO_PATHCONV=1; "docker.exe" "$@")
}

vol="-v /$(pwd)/src:/app -v /$(pwd)/config:/config -v //c/Share/PEPC/data:/data"
# env="-e CONFIG_FILENAME=/config/test/test-zeppelin-v2.json"
env="-e IOTEDGE_DEVICEID=TEST_ZEPPELIN_V2"
options="${vol} ${env}"
echo "${options}"
winpty docker run --name zeppelin2 --rm -it ${options} zeppelin-v2
