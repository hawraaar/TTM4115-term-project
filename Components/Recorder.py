from stmpy import Machine, Driver

import paho.mqtt.client as mqtt
import stmpy
import logging
from threading import Thread
import json

from os import system
import os
from time import gmtime, strftime, sleep

import pyaudio
import wave
from threading import Thread
import json

MQTT_BROKER = 'mqtt.item.ntnu.no'
MQTT_PORT = 1883

MQTT_TOPIC_INPUT = 'ttm4115/team_07/command'
MQTT_TOPIC_OUTPUT = 'ttm4115/team_07/answer'



#TODO nr1: choose receiver
#TODO nr2: Every sender should have an ID
#          Every client subsribes to a channel/topic
#          The payload of the message should contain a ID identifying the sender.

class Recorder:
    def __init__(self):
        self.output_dir = '../recordings'
        # deleting all old recordings
        filelist = [ f for f in os.listdir(self.output_dir) if f.endswith(".wav") ]
        for f in filelist:
            os.remove(os.path.join(self.output_dir, f))

        self.filename_list=[]
        self.recording = False
        self.chunk = 1024  # Record in chunks of 1024 samples
        self.sample_format = pyaudio.paInt16  # 16 bits per sample
        self.channels = 1
        self.fs = 44100  # Record at 44100 samples per second
        self.filename = ''
        self.p = pyaudio.PyAudio()

        # get the logger object for the component
        self._logger = logging.getLogger(__name__)
        print('logging under name {}.'.format(__name__))
        self._logger.info('Starting Component')



    def record(self):
        print("starting")
        self._logger.info('Starting')
        self.filename = str(strftime("%Y-%m-%d %H-%M-%S", gmtime())) + ".wav"
        stream = self.p.open(format=self.sample_format,
                             channels=self.channels,
                             rate=self.fs,
                             frames_per_buffer=self.chunk,
                             input=True)
        self.frames = []  # Initialize array to store frames
        # Store data in chunks for 3 seconds
        self.recording = True
        while self.recording:
            data = stream.read(self.chunk)
            self.frames.append(data)
        print("done recording")
        # Adding the filename to the list when finished recording
        self.filename_list.append(self.filename)
        # Stop and close the stream
        stream.stop_stream()
        stream.close()

        # Terminate the PortAudio interface
        # (This leads to only one recodring being possible, commented out for now)
        # self.p.terminate()

    def stop(self):
        print("stopping")
        self.recording = False


    def process(self):
        print("processing")
        # Save the recorded data as a WAV file
        path = self.output_dir + '//' + self.filename
        self.path = path
        wf = wave.open(path, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.p.get_sample_size(self.sample_format))
        wf.setframerate(self.fs)
        wf.writeframes(b''.join(self.frames))
        wf.close()

        if(len(self.filename_list) > 3):
            delete_file_name = self.filename_list[0]
            delete_path = self.output_dir + '/' + delete_file_name
            os.remove(delete_path)
            self.filename_list.remove(delete_file_name)

        print("finished processing")

    def create_machine(m_name, component):
        recorder = Recorder()

        t0 = {'source': 'initial', 'target': 'ready'}
        t1 = {'trigger': 'start', 'source': 'ready', 'target': 'recording'}
        t2 = {'trigger': 'done', 'source': 'recording', 'target': 'processing'}
        t3 = {'trigger': 'done', 'source': 'processing', 'target': 'ready'}

        s_recording = {'name': 'recording', 'do': 'record()', "stop": "stop()"}
        s_processing = {'name': 'processing', 'do': 'process()'}

        recorder_stm = Machine(name=m_name, transitions=[t0, t1, t2, t3], states=[s_recording, s_processing], obj=recorder)
        recorder.stm = recorder_stm
        return recorder

    def get_latest_file(self):
        return self.output_dir + '/' + self.filename
