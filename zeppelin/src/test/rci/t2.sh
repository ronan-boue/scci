clear
mosquitto_pub -t yoko_meeb1 -f ../../doc/data/rci/rci-yoko_meeb1.json
sleep 1
mosquitto_sub -t scci_devices -d -C 1
