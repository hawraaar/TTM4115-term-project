from stmpy import Machine, Driver

import paho.mqtt.client as mqtt
import stmpy
import logging
from threading import Thread
import json

from os import system
import os
import time

import pyaudio
import wave
from threading import Thread
import json

class Player:
    def __init__(self):
        pass

    def play(self):
        filename = 'output.wav'
        print("STARTING RECORDING")

        # Set chunk size of 1024 samples per data frame
        chunk = 1024

        # Open the sound file
        wf = wave.open(filename, 'rb')

        # Create an interface to PortAudio
        p = pyaudio.PyAudio()

        # Open a .Stream object to write the WAV file to
        # 'output = True' indicates that the sound will be played rather than recorded
        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True)

        # Read data in chunks
        data = wf.readframes(chunk)

        # Play the sound by writing the audio data to the stream
        i = 0
        while data != b'':
            i += 1
            stream.write(data)
            data = wf.readframes(chunk)
            if(i%1000000 == 0): print("playing")

        print("Hello! - player")

        # Close and terminate the stream
        stream.close()
        #p.terminate()

    def create_machine(m_name, component):
        # Create
        player = Player()

        t0 = {'source': 'initial', 'target': 'ready'}
        t1 = {'trigger': 'start', 'source': 'ready', 'target': 'playing'}
        t2 = {'trigger': 'done', 'source': 'playing', 'target': 'ready'}

        s_playing = {'name': 'playing', 'do': 'play()'}
        player_stm = Machine(name=m_name, transitions=[t0, t1, t2], states=[s_playing], obj=player)
        player.stm = player_stm

        return player_stm
