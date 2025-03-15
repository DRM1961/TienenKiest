import paho.mqtt.client as mqtt
from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO
import json
import eventlet
import eventlet.wsgi
import threading
import os

eventlet.monkey_patch() #async compatibility

app = Flask(__name__, static_url_path='/static')
app.secret_key = "your_secret_key"
title = "Gratis koffie op marktdagen"
TITLE_FILE = "title_file.txt"
counter1 = 0
counter2 = 0
PASSWORD = "TienenKiest,2025" #admin password

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet") 

# Initialize counter values and image URLs
data = {
    "counters": {"counter1": 0, "counter2": 0 }, 
    "images": {
        "image1": "/static/image_yes.jpg",
        "image2": "/static/image_no.jpg"
    }
}

# MQTT Broker Configuration
MQTT_BROKER = "192.168.129.82"
MQTT_PORT = 1883
MQTT_TOPICS = ["counter/1", "counter/2", "image/1", "image/2"]
mqtt_user = "rpi6"
mqtt_pw = "client"
mqtt_client = mqtt.Client()

# socket.io event at startup
@socketio.on("test_event")
def handle_test_event(data):
    print(f"received test event from browser: {data}")
    #socketio.emit("update_data", data)

# Load title from file or set a default one
def load_title():
    if os.path.exists(TITLE_FILE):
        with open(TITLE_FILE, "r") as file:
            return file.read().strip()
    return "Gratis koffie op marktdagen"

def save_title(title):
    with open(TITLE_FILE, "w") as file:
        file.write(title)

# MQTT Callbacks
def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT Broker with result code " + str(rc))
    socketio.emit("update_data", data)
    for topic in MQTT_TOPICS:
        client.subscribe(topic)

def on_message(client, userdata, msg):
    global data
    topic = msg.topic

    if topic == "counter/1":
        data["counters"]["counter1"] = int(msg.payload.decode("utf-8"))
    elif topic == "counter/2":
        data["counters"]["counter2"] = int(msg.payload.decode("utf-8"))
    elif topic == "image/1":
        with open('static/image_yes.jpg', 'wb') as fd:
            fd.write(msg.payload)
    elif topic == "image/2":
        #data["images"]["image2"] = payload
        with open('static/image_no.jpg', 'wb') as fd:
            fd.write(msg.payload)
    if "counter" in topic: 
        print(f"received {topic} with payload {msg.payload}")
    else:
        print(f"received {topic}")
    print(f"data =  {data}")
        
    # Send updated values to all connected clients
    socketio.sleep(0)
    socketio.emit("update_data", data)

def start_MQTT_client():
    # Initialize MQTT Client
    global mqtt_client
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.username_pw_set(username=mqtt_user,password=mqtt_pw)

    # Run MQTT in a separate thread
    mqtt_thread = threading.Thread(target=mqtt_client.loop_forever)
    mqtt_thread.daemon = True
    mqtt_thread.start()

@app.route('/')
def index():
    return render_template('index.html', title=title)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if "logged_in" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        global title, counter1, counter2
        if "reset" in request.form:
            mqtt_client.publish(topic="set_counter/1", payload="0", qos=0)
            mqtt_client.publish(topic="set_counter/2", payload="0", qos=0)
            counter1 = 0
            counter2 = 0
            socketio.emit("update_counters", {"counter1": counter1, "counter2": counter2})

        if "new_title" in request.form:
            title = request.form["new_title"]
            save_title(title)
            socketio.emit("update_title", {"title": title})
            
    return render_template("admin.html", title=title)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["password"] == PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("admin"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))

if __name__ == '__main__':
    title = load_title()
    start_MQTT_client()
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)


