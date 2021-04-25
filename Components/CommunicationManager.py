import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import stmpy
import logging
from threading import Thread
import json
import time


#from WalkieCommander import WalkieTalkie

MQTT_BROKER = 'mqtt.item.ntnu.no'
MQTT_PORT = 1883

MQTT_TOPIC_INPUT = 'ttm4115/team_07/Channel2'
MQTT_TOPIC_OUTPUT = 'ttm4115/team_07/Channel2'


## TODO: Make channels configurable from menu

class CommunicationManager:

    def on_connect(self, client, userdata, flags, rc):
        print("hallo")
        self._logger.debug('MQTT connected to {}'.format(client))

    def on_message(self, client, userdata, msg):

        print("A message is received")
        self._logger.debug('Incoming message to topic {}'.format(msg.topic))

        print("aaaaaa")
        self._logger.debug('Incoming message to topic {}'.format(msg.topic))
        # encdoding from bytes to string. This
        f = open("testNew.wav", 'wb')
        f.write(msg.payload)
        print("bbbbbb")
        f.close()

    def send_message(self, filename):
        print("hei")
        f = open('../' + filename, "rb")
        imagestring = f.read()
        f.close()
        byteArray = bytearray(imagestring)
        print("hei2")

        #self.mqtt_client.publish(MQTT_TOPIC_OUTPUT, "TEST")

        publish.single(MQTT_TOPIC_OUTPUT, byteArray, hostname=MQTT_BROKER, port=MQTT_PORT)
        time.sleep(1)
        print("hei3")

    def __init__(self):
        """
        Start the component.
        ## Start of MQTT
        We subscribe to the topic(s) the component listens to.
        The client is available as variable `self.client` so that subscriptions
        may also be changed over time if necessary.
        The MQTT client reconnects in case of failures.
        ## State Machine driver
        We create a single state machine driver for STMPY. This should fit
        for most components. The driver is available from the variable
        `self.driver`. You can use it to send signals into specific state
        machines, for instance.
        """
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

        walkie = WalkieTalkie()

        # we start the stmpy driver, without any state machines for now
        #self.stm_driver = stmpy.Driver()
        #self.stm_driver.start(keep_active=True)
        #self._logger.debug('Component initialization finished')

    def stop(self):
        """
        Stop the component.
        """
        # stop the MQTT client
        self.mqtt_client.loop_stop()
        print("stopped")

        # stop the state machine Driver
        #self.stm_driver.stop()


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

c=CommunicationManager()


time.sleep(2)
print("1")
c.send_message('output.wav')
print("2")
