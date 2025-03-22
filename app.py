import paho.mqtt.client as mqtt
from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO
import json
import eventlet
import eventlet.wsgi
import threading
import os
import yaml

app = Flask(__name__, static_url_path='/static')
app.secret_key = "your_secret_key"

eventlet.monkey_patch() #async compatibility
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet") 

CONFIG_FILE = "config.yaml"
PASSWORD = "TienenKiest,2025" #admin password

# Initialize counter values and image URLs
data = {
    "counters": {"counter1": 0, "counter2": 0 }, 
    "images": {
        "image1": "/static/image_yes.jpg",
        "image2": "/static/image_no.jpg"
    }
}

config = None
mqtt_client = None

# socket.io event at startup
@socketio.on("test_event")
def handle_test_event(data):
    print(f"received test event from browser: {data}")
    #socketio.emit("update_data", data)

# Load configuration from YAML
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as file:
            return yaml.safe_load(file)
    return {
        "title": "Gratis koffie op marktdagen",
        "counters": {"counter1": 0, "counter2": 0},
        "mqtt": {"broker": "192.168.1.10",
                 "port": 1883,
                 "topic1": "counter1",
                 "topic2": "counter2",
                 "user": "rpi_display",
                 "pw": "client"
                 },
    }

# Save configuration to YAML
def save_config(config):
    with open(CONFIG_FILE, "w") as file:
        yaml.safe_dump(config, file)

# MQTT Callbacks
def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT Broker with result code " + str(rc))
    #socketio.emit("update_data", data)
    
    MQTT_TOPICS = ["counter/1", "counter/2", "image/1", "image/2"]
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
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(config["mqtt"]["broker"],
                        config["mqtt"]["port"],
                        60)
    mqtt_client.username_pw_set(username=config["mqtt"]["user"],
                                password=config["mqtt"]["pw"])

    # Run MQTT in a separate thread
    mqtt_thread = threading.Thread(target=mqtt_client.loop_forever)
    mqtt_thread.daemon = True
    mqtt_thread.start()

@app.route('/')
def index():
    return render_template('index.html', title=config["title"])

    #return render_template("index.html", title=config["title"], counter1=config["counters"]["counter1"], counter2=config["counters"]["counter2"])

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if "logged_in" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        if "reset" in request.form:
            mqtt_client.publish(topic="set_counter/1", payload="0", qos=0)
            mqtt_client.publish(topic="set_counter/2", payload="0", qos=0)
            config["counters"]["counter1"] = 0
            config["counters"]["counter2"] = 0
            save_config(config)
            socketio.emit("update_counters", config["counters"])

        if "new_title" in request.form:
            config["title"] = request.form["new_title"]
            save_config(config)
            socketio.emit("update_title", {"title": config["title"]})
            
    return render_template("admin.html", title=config["title"])

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
    config = load_config()
    start_MQTT_client()
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)


