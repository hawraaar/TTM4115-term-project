import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

from stmpy import Machine, Driver
import logging
from threading import Thread
import json
from appJar import gui
from Recorder import Recorder
from Player import Player
import time
from time import gmtime, strftime, sleep


# TODO: choose proper MQTT broker address
MQTT_BROKER = 'mqtt.item.ntnu.no'
MQTT_PORT = 1883

# TODO: choose proper topics for communication
MQTT_TOPIC_INPUT = 'ttm4115/team_07/Channel2'
MQTT_TOPIC_OUTPUT = 'ttm4115/team_07/Channel2'



class WalkieTalkie:

    """
    The component to send voice commands.
    """
    def on_connect(self, client, userdata, flags, rc):
        print("hallo")
        self._logger.debug('MQTT connected to {}'.format(client))

    def on_message(self, client, userdata, msg):
        print("A message is received")
        self._logger.debug('Incoming message to topic {}'.format(msg.topic))
        # encdoding from bytes to string. This
        temp_file = str(strftime("%Y-%m-%d %H-%M-%S", gmtime())) + ".wav"
        self.temp_file = temp_file
        f = open("../player/" + temp_file, 'wb')
        f.write(msg.payload)
        print("bbbbbb")
        f.close()
        self.driver.send('start', 'stm_player', args=[self.temp_file])

    def send_message(self):
        print("hei")
        path = self.recorder.get_latest_file()
        f = open(path, "rb")
        imagestring = f.read()
        f.close()
        byteArray = bytearray(imagestring)
        print("hei2")

        #self.mqtt_client.publish(MQTT_TOPIC_OUTPUT, "TEST")

        publish.single(MQTT_TOPIC_OUTPUT, byteArray, hostname=MQTT_BROKER, port=MQTT_PORT)
        time.sleep(1)
        print("hei3")


    def __init__(self):
        # get the logger object for the component
        self._logger = logging.getLogger(__name__)
        print('logging under name {}.'.format(__name__))
        self._logger.info('Starting Component')

        # create a new MQTT client
        self._logger.debug('Connecting to MQTT broker {} at port {}'.format(MQTT_BROKER, MQTT_PORT))
        self.mqtt_client = mqtt.Client()
        # callback methods
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        # Connect to the broker
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
        # subscribe to proper topic(s) of your choice
        self.mqtt_client.subscribe(MQTT_TOPIC_INPUT)
        # start the internal loop to process MQTT messages
        self.mqtt_client.loop_start()


        recorder = Recorder.create_machine('stm_recorder', self)
        self.recorder = recorder
        stm_recorder = recorder.stm
        #recorder.stm_recorder = stm_recorder

        stm_player = Player.create_machine('stm_player', self)
        #recorder.stm_player = stm_player

        self.driver = Driver()
        self.driver.add_machine(stm_recorder)
        self.driver.add_machine(stm_player)


        self.driver.start(keep_active = True)
        self.create_gui()
        print("Help!")

    def create_gui(self):
        self.app = gui()


        def extract_timer_name(label):
            label = label.lower()
            if 'start' in label: return 'start'
            if 'stop'  in label: return 'stop'
            return None

        self.app.startLabelFrame('Start recording:')
        print("1")

        def on_button_pressed_start(title):
            self.driver.send('start', 'stm_recorder')
            print("2")

        self.app.addButton('Start', on_button_pressed_start)
        print("3")
        self.app.stopLabelFrame()
        print("4")

        self.app.startLabelFrame('Stop recording:')
        def on_button_pressed_stop(title):
            self.driver.send('stop', 'stm_recorder')
            time.sleep(2)
            self.send_message()
        print('5')
        self.app.addButton('Stop recording', on_button_pressed_stop)
        self.app.stopLabelFrame()

        self.app.startLabelFrame('Replay:')
        def on_button_pressed_play(title):
            self.driver.send('start', 'stm_player', args=[self.temp_file])
        self.app.addButton('Replay', on_button_pressed_play)
        self.app.stopLabelFrame()

        self.app.go()
        self.driver.stop()


    def stop(self):
        """
        Stop the component.
        """
        self.mqtt_client.loop_stop()

        # stop the state machine Driver
        self.driver.stop()


# logging.DEBUG: Most fine-grained logging, printing everything
# logging.INFO:  Only the most important informational log items
# logging.WARN:  Show only warnings and errors.
# logging.ERROR: Show only error messages.
debug_level = logging.DEBUG
logger = logging.getLogger(__name__)
logger.setLevel(debug_level)
ch = logging.StreamHandler()
ch.setLevel(debug_level)
formatter = logging.Formatter('%(asctime)s - %(name)-12s - %(levelname)-8s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

t = WalkieTalkie()
