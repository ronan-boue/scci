clear
mosquitto_pub -t jace_scci -f ../../doc/data/rci/rci-jace_scci.json
sleep 1
mosquitto_sub -t scci_devices -d -C 1
