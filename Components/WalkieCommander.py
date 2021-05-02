import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

import os
import sys
import time
import json
import io
import base64
import logging
import speech_recognition as sr
from time import gmtime, strftime, sleep
from stmpy import Machine, Driver
from Recorder import Recorder
from Player import Player
from appJar import gui
from threading import Thread
from os import system, path
from random import *


# Choose MQTT broker address
MQTT_BROKER = 'mqtt.item.ntnu.no'
MQTT_PORT = 1883

# TODO: choose proper topics for communication
MQTT_TOPIC_INPUT = 'ttm4115/team07/Channel'
MQTT_TOPIC_OUTPUT = 'ttm4115/team07/Channel'
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
        # setting the standard channel as 0 and ID as default
        self.channel = 0
        self.ID = "default"

        # the output dir is where received recordings are stored
        self.output_dir = "../player/"
        self.record_dir = "../recordings/"
        self.channel_dir = self.output_dir + str(self.channel)
        self.fileNameList = []
        self.messageList = []

        # cleaing the player list
        self.create_channel_folder(self.output_dir, self.record_dir)

        #Burde vi ha create_player_folder for konsistent??
        self.clear_player_folder(self.output_dir)

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
        self.mqtt_client.on_disconnect = self.on_disconnect


        # Connect to the broker
        try:
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT)

        except:
            print("Connection fails")
            sys.exit(1)


        self.mqtt_client.loop_start()

        '''
        #Testing the on_disconnect function
        time.sleep(10)
        self.mqtt_client.disconnect() # disconnect gracefully
        self.mqtt_client.loop_stop() # stops network loop
        time.sleep(5)
        self.mqtt_client.connect()
        '''


        # recorder
        recorder = Recorder.create_machine('stm_recorder', self)
        self.recorder = recorder
        stm_recorder = recorder.stm

        # player
        player = Player.create_machine('stm_player', self)
        self.player = player
        stm_player = player.stm

        # creating driver, attaching machines
        self.driver = Driver()
        self.driver.add_machine(stm_recorder)
        self.driver.add_machine(stm_player)

        # starting driver
        self.driver.start(keep_active = True)
        self.create_gui()
        print("Bye!")


    def create_channel_folder(self, output_dir, record_dir):
        if not os.path.exists(output_dir): os.mkdir(output_dir)
        if not os.path.exists(record_dir): os.mkdir(record_dir)
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
        print(mqtt.connack_string(rc))
        if(rc == 0):
            self.mqtt_client.subscribe(MQTT_TOPIC_INPUT + str(self.channel))
            self.mqtt_client.subscribe(MQTT_TOPIC_INPUT+ str(self.channel)+"/ACK")
            self._logger.debug('MQTT connected to {}'.format(client))
            self.client_id = client
        else:
            print(mqtt.connack_string(rc))

    def on_disconnect(self, client, userdata, rc):
        if(rc == 0):
            print("Disconnected gracefully.")
        else:
            print("Unexpected disconnection.")
            self.app.setLabel("delivered", text = "Connection lost: Waiting to reconnect \n and resend latest message")


    # Runs when WalkieTalkie receives a message
    def on_message(self, client, userdata, msg):
        print("A message is received")
        self._logger.debug('Incoming message to topic {}'.format(msg.topic))


        #message_payload_received = json.load(io.BytesIO(msg.payload))
        if(msg.payload):
            message_payload_received = json.loads(msg.payload)
            # Check correct channel
            if(str(msg.topic) == MQTT_TOPIC_OUTPUT + str(self.channel) and message_payload_received):
                dataToByteArray = base64.b64decode(bytearray(bytes(message_payload_received['data'], "utf-8")))

                print("client_id: " + message_payload_received['ID'])

                # Check that message is not sent to self
                if (message_payload_received['ID'] != self.ID):
                    temp_file = message_payload_received['ID'] + str(strftime(" %Y-%m-%d %H-%M-%S", gmtime())) + ".wav"
                    self.temp_file = temp_file
                    f = open(os.path.join(self.channel_dir, self.temp_file), 'wb')
                    f.write(dataToByteArray)
                    print("Data written to file")
                    f.close()
                    self.driver.send('start', 'stm_player', args=[os.path.join(self.channel_dir, self.temp_file)])
                    time.sleep(1)
                    self.messageList  = [ Message(path) for path in os.listdir(self.channel_dir) if path.endswith(".wav") ]
                    self.fileNameList = [ m.path for m in self.messageList]
                    print(self.fileNameList)
                    self.app.changeOptionBox("Choose message", self.fileNameList)

                    # Sending ack
                    package_ack = {'message_id': message_payload_received['Msg_ID'], 'sender': message_payload_received['ID']}
                    payload_ack = json.dumps(package_ack)
                    self.mqtt_client.publish(str(msg.topic)+"/ACK", payload_ack, qos=2)


            # Checks for ACK
            if (str(msg.topic) == MQTT_TOPIC_INPUT+ str(self.channel)+"/ACK"):
                if(message_payload_received['message_id'] == self.recorder.get_latest_file()):
                    if(message_payload_received['sender'] == self.ID):
                        print("Message delivered with ID: "+ message_payload_received['message_id'] + " and sender: " + message_payload_received['sender'])
                        self.app.setLabel("delivered","Message delivered")
                        self.app.setLabelFg("delivered","green")




    def send_message(self):
        print("Sending a new message")
        #self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
        path = self.recorder.get_latest_file()
        f = open(path, "rb")
        imagestring = f.read()
        f.close()
        imageByteArray = bytearray(imagestring)
        imageByteArrayString = str(base64.b64encode(imageByteArray), "utf-8")
        package = {'ID': self.ID, 'data': imageByteArrayString, 'Msg_ID': path}
        payload = json.dumps(package)
        mqtt_msg = self.mqtt_client.publish(MQTT_TOPIC_OUTPUT + str(self.channel), payload, qos = 2)
        timestamp = time.time()
        print("Sending the message took: {} ".format(time.time()-timestamp))

        self.app.setLabel("delivered",text = "Sending")
        self.app.setLabelFg("delivered","orange")
        time.sleep(1)
        # catching the exception thrown by mqtt when no acc is given.
        ## TODO: Her kan vi kanskje ha Message failed rød tekst? Hvis Catch error.


    # Creates the appJar GUI
    def create_gui(self):
        BUTTON_WIDTH = 30
        self.app = gui("Walkie-Talkie", "300x500")


        #set username
        def on_button_name(title):
            self.ID = self.app.getEntry("NameEntry")
            self.app.setLabel("NameLabel", "User: " + self.ID)
            print("User ID changed")

        #channel up
        def on_button_pressed_increase(title):
            self.mqtt_client.unsubscribe(MQTT_TOPIC_INPUT + str(self.channel))
            self.mqtt_client.unsubscribe(MQTT_TOPIC_INPUT+ str(self.channel)+"/ACK")
            self.channel = (self.channel + 1)% MAX_CHANNELS
            self.set_channel_path()
            self.mqtt_client.subscribe(MQTT_TOPIC_INPUT + str(self.channel))
            self.mqtt_client.subscribe(MQTT_TOPIC_INPUT+ str(self.channel)+"/ACK")
            self.app.setLabel("Channel",text="Connected to channel: {}".format(self.channel))

        #channel up
        def on_button_pressed_decrease(title):
            self.mqtt_client.unsubscribe(MQTT_TOPIC_INPUT + str(self.channel))
            self.mqtt_client.unsubscribe(MQTT_TOPIC_INPUT+ str(self.channel)+"/ACK")
            self.channel = (self.channel - 1) % MAX_CHANNELS
            self.set_channel_path()
            self.mqtt_client.subscribe(MQTT_TOPIC_INPUT + str(self.channel))
            self.mqtt_client.subscribe(MQTT_TOPIC_INPUT+ str(self.channel)+"/ACK")
            self.app.setLabel("Channel",text="Connected to channel: {}".format(self.channel))


        #start recording
        def on_button_pressed_start(title):
            self.driver.send('start', 'stm_recorder')
            print("Start recording")

        #Stop recording and send message
        def on_button_pressed_stop(title):
            self.driver.send('stop', 'stm_recorder')
            time.sleep(1)
            self.send_message()
            print("Stop recording")

        #resend latest message
        def on_button_pressed_resend(title):
            if os.listdir(self.record_dir) != []:
                self.send_message()
            else:
                print("You have no messages. ")

        #Replay chosen message
        def on_button_pressed_replay(title):
            play_list = self.fileNameList
            if play_list:
                tmp = self.app.getOptionBox('Choose message')
                self.driver.send('replay', 'stm_player', args=[os.path.join(self.channel_dir, tmp)])
            else:
                print("You have no messages. ")


        def voiceToText(title):
            play_list = self.fileNameList
            if play_list:
                tmp = self.app.getOptionBox('Choose message')
                r = sr.Recognizer()

                lyd=sr.AudioFile(os.path.join(self.channel_dir, tmp))
                with lyd as source:
                    audio = r.record(source)
                try:
                    s = r.recognize_google(audio)
                    self.app.setLabel("message","Message: " + s)
                except Exception as e:
                    print("Exception: "+str(e))
            else:
                print("You have no messages. ")



        # Choose ID
        self.app.addLabel("NameLabel", "User: " + self.ID, 0, 0)

        self.app.startLabelFrame("Names")

        self.app.addLabel("NameEntryLabel", "Name: ", 1, 0)

        self.app.addEntry("NameEntry", 1, 1)
        self.app.setEntrySubmitFunction("NameEntry", on_button_name)
        self.app.stopLabelFrame()


        # Choose channel
        self.app.startLabelFrame('Change channel:')
        self.app.addLabel("Channel",text="Connected to channel: {}".format(self.channel), colspan=2)
        self.app.setLabelWidth('Channel', int(BUTTON_WIDTH*(5/3)))

        self.app.addButton('Increase', on_button_pressed_increase, 1, 0)
        self.app.setButtonWidth('Increase', BUTTON_WIDTH)

        self.app.addButton('Decrease', on_button_pressed_decrease, 1 , 1)
        self.app.setButtonWidth('Decrease', BUTTON_WIDTH)
        self.app.stopLabelFrame()

        # Start and stop recording
        self.app.startLabelFrame('Send messages')

        self.app.addButton('Start recording', on_button_pressed_start, 1, 0)
        self.app.setButtonWidth("Start recording", BUTTON_WIDTH)

        self.app.addButton('Stop and send', on_button_pressed_stop, 1, 1)
        self.app.setButtonWidth('Stop and send', BUTTON_WIDTH)

        #resend and exit button
        self.app.addButton('Resend', on_button_pressed_resend, colspan=2)
        self.app.setButtonWidth('Resend', BUTTON_WIDTH*2)
        self.app.addButton('Exit system', sys.exit, colspan=3)
        self.app.setButtonWidth('Exit system', BUTTON_WIDTH*2)


        self.app.addLabel("delivered", "")
        self.app.stopLabelFrame()


        # Replay last received message
        self.app.startLabelFrame('Replay message:')
        self.app.addOptionBox("Choose message", self.fileNameList, colspan=2)
        self.app.setOptionBoxWidth('Choose message', BUTTON_WIDTH)

        self.app.addButton('Replay', on_button_pressed_replay, 1, 0)
        self.app.setButtonWidth('Replay', BUTTON_WIDTH)
        self.app.addButton('Text Message', voiceToText, 1, 1)
        self.app.setButtonWidth('Text Message', BUTTON_WIDTH)
        self.app.stopLabelFrame()



        #Voice to text
        self.app.startFrame("message frame")
        self.app.setBg("white")
        self.app.addLabel("message", "No message data...")
        self.app.stopFrame()
        self.app.go()
        self.stop()


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
