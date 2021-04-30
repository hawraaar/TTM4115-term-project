import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

from stmpy import Machine, Driver
import logging
from threading import Thread
import json
import io
import base64
from appJar import gui
from Recorder import Recorder
from Player import Player
import time
from time import gmtime, strftime, sleep
from os import system, path
import os


# TODO: choose proper MQTT broker address
MQTT_BROKER = 'mqtt.item.ntnu.no'
MQTT_PORT = 1883

# TODO: choose proper topics for communication
MQTT_TOPIC_INPUT = 'ttm4115/team_07/Channel'
MQTT_TOPIC_OUTPUT = 'ttm4115/team_07/Channel'
MAX_CHANNELS = 5


class Message:
    def __init__(self, path):
        self.path = path
        self.text = None

class WalkieTalkie:
    """
    The component to send and receive voice messages.
    """

    def __init__(self):
        # setting the standard channel as 0
        self.channel = 0
        # the output dir is where recordings are stored
        self.output_dir = "../player/channel"
        self.channel_dir = self.output_dir + str(self.channel)
        self.fileNameList = []
        self.messageList = []
        # cleaing the player list
        self.creat_channel_folder(self.output_dir)
        self.clear_player_folder(self.output_dir)

        self.ID = "default"
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
        self.mqtt_client.subscribe(MQTT_TOPIC_INPUT + str(self.channel))
        # start the internal loop to process MQTT messages
        self.mqtt_client.loop_start()

        # recorder
        recorder = Recorder.create_machine('stm_recorder', self)
        self.recorder = recorder
        stm_recorder = recorder.stm

        # player
        player = Player.create_machine('stm_player', self)
        self.player=player
        stm_player=player.stm

        # creating driver, attaching machines
        self.driver = Driver()
        self.driver.add_machine(stm_recorder)
        self.driver.add_machine(stm_player)

        # starting driver
        self.driver.start(keep_active = True)
        self.create_gui()
        print("Help!")

    def creat_channel_folder(self, output_dir):
        for i in range(MAX_CHANNELS):
            path = output_dir + str(i)
            if not os.path.exists(path):
                os.mkdir(path)

    def clear_player_folder(self, output_dir):
        for i in range(MAX_CHANNELS):
            for f in os.listdir(output_dir + str(i)):
                if f.endswith(".wav"):
                    os.remove(os.path.join(output_dir+str(i), f))

    def set_channel_path(self):
        self.channel_dir=self.output_dir +str(self.channel)


    def on_connect(self, client, userdata, flags, rc):
        print("hallo")
        #print("Connection returned result: "+ connack_string(rc))
        self._logger.debug('MQTT connected to {}'.format(client))
        self.client_id = client

    # Function when WalkieTalkie receives a message
    def on_message(self, client, userdata, msg):
        print("A message is received")
        self._logger.debug('Incoming message to topic {}'.format(msg.topic))

        #message_payload_received = json.load(io.BytesIO(msg.payload))
        message_payload_received = json.loads(msg.payload)
        dataFixed = base64.b64decode(bytearray(bytes(message_payload_received['data'], "utf-8")))
        #print(dataFixed)
        dataToByteArray = dataFixed
        print("client_id: " + message_payload_received['ID'])

        # encdoding from bytes to string. This
        if (message_payload_received['ID'] != self.ID):
            temp_file = str(strftime("%Y-%m-%d %H-%M-%S", gmtime())) + ".wav"
            self.temp_file = temp_file
            f = open(os.path.join(self.channel_dir, self.temp_file), 'wb')
            f.write(dataToByteArray)
            print("bbbbbb")
            f.close()
            self.driver.send('start', 'stm_player', args=[os.path.join(self.channel_dir, self.temp_file)])
            time.sleep(1)
            self.messageList =  [ Message(path) for path in os.listdir(self.channel_dir) if path.endswith(".wav") ]
            self.fileNameList = [ m.path for m in self.messageList]
            print(self.fileNameList)
            self.app.changeOptionBox("Choose message", self.fileNameList)
        else:
            if(message_payload_received['Msg_ID'] == self.recorder.get_latest_file()):
                print("Message delivered")
                self.app.setLabel("delivered","Message delivered")
                self.app.setLabelBg("delivered","green")
            else:
                print('Message lost not last message-ID')

    def send_message(self):
        print("hei")
    #   try:
        path = self.recorder.get_latest_file()
        f = open(path, "rb")
        imagestring = f.read()
        f.close()
        imageByteArray = bytearray(imagestring)
        # DEBUG start:
        print("hei2")
        # DEBUG end:
        imageByteArrayString = str(base64.b64encode(imageByteArray), "utf-8")
        package = {'ID': self.ID, 'data': imageByteArrayString, 'Msg_ID': path}
        payload = json.dumps(package)
        # mqtt_msg = publish.single(MQTT_TOPIC_OUTPUT + str(self.channel), payload, client_id=self.ID, hostname=MQTT_BROKER, port=MQTT_PORT, qos = 2)
        mqtt_msg = self.mqtt_client.publish(MQTT_TOPIC_OUTPUT + str(self.channel), payload, qos = 2)

        timestamp = time.time()
        #while(not mqtt_msg.is_published()):
        #    if(time.time() - timestamp > 5):
        #        print("Message not delivered")
        #        break
        #    print(mqtt_msg.is_published())
        print("sending the message took: {} ".format(time.time()-timestamp))

        self.app.setLabel("delivered","Sending")
        self.app.setLabelBg("delivered","yellow")
        time.sleep(1)
        # catching the exception thrown by mqtt when no acc is given.


    # Creates the appJar GUI
    def create_gui(self):
        BUTTON_WIDTH = 20
        self.app = gui("Walkie-Talkie", "300x500")

        # Choose ID
        self.app.addLabel("NameLabel", "User: " + self.ID, 0, 0)
        self.app.startLabelFrame("Names")
        self.app.addLabel("NameEntryLabel", "Name: ", 1, 0)

        def on_button_name(title):
            self.ID = self.app.getEntry("NameEntry")
            self.app.setLabel("NameLabel", "User: " + self.ID)
            print("User changed")

        self.app.addEntry("NameEntry", 1, 1)
        self.app.setEntrySubmitFunction("NameEntry", on_button_name)
        self.app.stopLabelFrame()


        # Choose channel
        self.app.startLabelFrame('Change channel:')
        self.app.addLabel("Channel",text="Connected to channel: {}".format(self.channel), colspan=2)
        self.app.setLabelWidth('Channel', int(BUTTON_WIDTH*(5/3)))

        def on_button_pressed_increase(title):
            self.mqtt_client.unsubscribe(MQTT_TOPIC_INPUT + str(self.channel))
            self.channel = (self.channel + 1)% MAX_CHANNELS
            self.set_channel_path()
            self.mqtt_client.subscribe(MQTT_TOPIC_INPUT + str(self.channel))
            self.app.setLabel("Channel",text="Connected to channel: {}".format(self.channel))

        self.app.addButton('Increase', on_button_pressed_increase, 1, 0)
        self.app.setButtonWidth('Increase', BUTTON_WIDTH)

        def on_button_pressed_decrease(title):
            self.mqtt_client.unsubscribe(MQTT_TOPIC_INPUT + str(self.channel))
            self.channel = (self.channel - 1) % MAX_CHANNELS
            self.set_channel_path()
            self.mqtt_client.subscribe(MQTT_TOPIC_INPUT + str(self.channel))
            self.app.setLabel("Channel",text="Connected to channel: {}".format(self.channel))

        self.app.addButton('Decrease', on_button_pressed_decrease, 1 , 1)
        self.app.setButtonWidth('Decrease', BUTTON_WIDTH)
        self.app.stopLabelFrame()

        # Start and stop recording
        self.app.startLabelFrame('Recordings')
        print("1")

        def on_button_pressed_start(title):
            self.driver.send('start', 'stm_recorder')
            print("2")

        self.app.addButton('Start recording', on_button_pressed_start, 0, 0)
        self.app.setButtonWidth("Start recording", BUTTON_WIDTH)
        print("3")
        print("4")

        def on_button_pressed_stop(title):
            self.driver.send('stop', 'stm_recorder')
            time.sleep(2)
            self.send_message()
        print('5')

        def on_button_pressed_resend(title):
            self.send_message()

        self.app.addButton('Stop and send', on_button_pressed_stop, 0, 1)
        self.app.setButtonWidth('Stop and send', BUTTON_WIDTH)
        self.app.addButton('Resend', on_button_pressed_resend, colspan=2)
        self.app.setButtonWidth('Resend', BUTTON_WIDTH*2)
        self.app.addLabel("delivered", "")
        self.app.stopLabelFrame()

        # Replay last received message
        self.app.startLabelFrame('Replay message:')
        self.app.addOptionBox("Choose message", self.fileNameList, colspan=2)
        self.app.setOptionBoxWidth('Choose message', BUTTON_WIDTH)


        def on_button_pressed_replay(title):
            play_list = self.fileNameList
            if play_list:
                tmp = self.app.getOptionBox('Choose message')
                #print('Temp File: ' + str(tmp))
                self.driver.send('replay', 'stm_player', args=[os.path.join(self.channel_dir, tmp)])
            else:
                print("You have no messages. ")

        self.app.addButton('Replay', on_button_pressed_replay, 1, 0)
        self.app.setButtonWidth('Replay', BUTTON_WIDTH)
        self.app.addButton('Text Message', on_button_pressed_replay, 1, 1)
        self.app.setButtonWidth('Text Message', BUTTON_WIDTH)
        self.app.stopLabelFrame()
        self.app.startFrame("message frame")
        self.app.setBg("white")
        self.app.addMessage("message", "No message data...")
        self.app.stopFrame()
        self.app.go()
        self.driver.stop()

    def stop(self):
        """
        Stop the component.
        """
        self.mqtt_client.loop_stop()
        # Stop the state machine Driver
        self.driver.stop()

def main():
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

# Voice to text - create a stm and then put do the
if __name__ == "__main__":
    main()
