# https://pypi.org/project/paho-mqtt/
# sudo apt install python3-paho-mqtt
# mosquitto_sub -d -t testTopic -u rpi6 -P client
# mosquitto_pub -d -t  testTopic -m "counter-value"  -u dm -P client
# mosquitto_pub -d -t  topicFile -f ~/dev/todo.txt -u mqtt_admin -P admin


import paho.mqtt.client as mqtt
import time
import random

#broker_IP="172.21.235.58"
broker_IP="192.168.129.82"

port = 1883
keepalive = 60
   
counter1 = 0
counter2 = 0

class CMqttClient:
    def __init__(self, userdata, user, pw):
        self.user = user
        self.pw = pw
        self.userdata = userdata
        self.data = []
        self.isFile = False
        self.filename = ""
        self.connected = False
        self.subscribed = False
        self.client = mqtt.Client(userdata=userdata)  
        self.client.username_pw_set(username=self.user,password=self.pw)
        self.client.on_connect = self.on_connect
        self.client.connect(broker_IP, port, keepalive) 
        self.client.loop_start() #loop_forever?

    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code "+str(rc))
        print(f"Connected client {client} userdata {userdata} flags {flags} return code {rc}")
        if rc == 0:
            self.connected = True

    def on_subscribe(self, client, userdata, mid, granted_qos):
        print(f"Subscribed client {client} userdata {userdata} mid {mid} granted_qos {granted_qos}")
        self.subscribed = True

    def on_message(self, client, userdata, msg):
        global counter1, counter2
        if self.isFile:
            print(f"received client {client} userdata {userdata}")
            with open(self.filename, 'wb') as fd:
                fd.write(msg.payload)
        else:
            print(f"received client {client} userdata {userdata} msg {msg}")
            print(msg.topic+" "+str(msg.payload))
            if msg.topic=="set_counter/1":
                counter1 = int(msg.payload)
            if msg.topic=="set_counter/2":
                counter2 = int(msg.payload)

    def subscribe(self, topic, filename="", isFile=False):
        self.client.on_subscribe = self.on_subscribe
        self.client.on_message = self.on_message
        self.filename = filename
        self.isFile = isFile
        self.client.subscribe(topic,0)

    def publish(self, topic, datastring, isFilename=False):
        if isFilename:
            file = open(datastring, "rb")
            filestring = file.read()
            byteArray = bytes(filestring)
            print(len(byteArray))
            
            self.client.publish(topic=topic, payload=byteArray, qos=0)
        else:
            self.client.publish(topic=topic, payload=datastring, qos=0)

    
if __name__ == "__main__":
    
    sub1 = CMqttClient("rpi1", "rpi6", "client")
    sub2 = CMqttClient("rpi2", "dm", "client")
    sub1.subscribe("set_counter/1")
    sub2.subscribe("set_counter/2")
    
    counter1 = 0
    counter2 = 0

    images = []

    while(1):
        sub = random.randint(1,2)
        imagenr = random.randint(0,49)
        image = f'/home/rpi6/dev/TienenKiest/backup/images/{imagenr:08}.jpg'

        if sub==1 and sub1.connected:
            counter1 += 1
            sub1.publish("counter/1", str(counter1))
            sub1.publish("image/1", image, True)
            print(f"publishing 1, counter {counter1}")

        
        if sub==2 and sub2.connected:
            counter2 += 1
            sub1.publish("counter/2", str(counter2))
            sub1.publish("image/2", image, True)
            print(f"publishing 2, counter {counter2}")
        
        time.sleep(5)

