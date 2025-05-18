from .plugin import Plugin

import ctypes
import time


class SoundController(Plugin):
    
    def trigger_text(self):
        return ["next track", "previous track", "mute"]

    def execute_command(self, triggered_text):
        # Constants
        
        TRACK_VK = ""
        
        VK_MEDIA_NEXT_TRACK = 0xB0
        VK_MEDIA_PREV_TRACK = 0xB1
        if triggered_text == "previous track":
            TRACK_VK = VK_MEDIA_PREV_TRACK
        elif triggered_text == "next track":
            TRACK_VK = VK_MEDIA_NEXT_TRACK
        elif triggered_text == "mute":
            TRACK_VK =  0xAD 
        
        KEYEVENTF_EXTENDEDKEY = 0x0001
        KEYEVENTF_KEYUP = 0x0002 
        # Press Next Track key
        ctypes.windll.user32.keybd_event(TRACK_VK, 0, KEYEVENTF_EXTENDEDKEY, 0)
        time.sleep(0.05)
        # Release Next Track key
        ctypes.windll.user32.keybd_event(TRACK_VK, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)


