clear
mosquitto_pub -t yoko_scci -f ../../doc/data/rci/rci-yoko_scci.json
sleep 1
mosquitto_sub -t scci_devices -d -C 1
