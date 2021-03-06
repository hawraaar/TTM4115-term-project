from stmpy import Machine, Driver

import stmpy
import logging
from threading import Thread
import json

from os import system
import os
import time

import pyaudio
import wave


class Player:
    def __init__(self):
        pass

    def play(self, _filename):

        filename = _filename

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
        while data != b'':
            stream.write(data)
            data = wf.readframes(chunk)

        # Close and terminate the stream
        stream.close()
        #p.terminate()

    def create_machine(m_name, component):
        # Create
        player = Player()

        t0 = {'source': 'initial', 'target': 'ready'}
        t1 = {'trigger': 'start', 'source': 'ready', 'target': 'playing'}
        t2 = {'trigger': 'done', 'source': 'playing', 'target': 'ready'}
        t3 = {'trigger': 'replay', 'source': 'ready', 'target': 'playing'}

        s_playing = {'name': 'playing', 'do': 'play(*)','start':'defer', 'replay':''}
        player_stm = Machine(name=m_name, transitions=[t0, t1, t2, t3], states=[s_playing], obj=player)
        player.stm = player_stm

        return player
