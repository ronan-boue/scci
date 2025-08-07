# Test payload with cloud event from original publisher
clear
mosquitto_pub -t yoko_scci_ce -f ../../doc/data/rci/rci-yoko_scci_ce.json
sleep 1
mosquitto_sub -t scci_devices -d -C 1
