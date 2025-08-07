# send a payload to the MQTT broker
# used to test Cloud2Edge connectivity (module direct method)
mosquitto_pub -t generic-in -f message1.json
mosquitto_pub -t generic-in -f message2.json
mosquitto_pub -t generic-in -f message3.json
mosquitto_sub -t generic-out -v -d -C 1
