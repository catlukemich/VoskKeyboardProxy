import os

from .plugin import Plugin

class CalculatorLauncher(Plugin):
    
    def trigger_text(self):
        return ["calculator", "kalkulator"]
    
    def execute_command(self, triggered_text):
        # import ctypes
        # import time

        # # Constants
        # VK_LAUNCH_APP1 = 0xB6
        # KEYEVENTF_EXTENDEDKEY = 0x0001
        # KEYEVENTF_KEYUP = 0x0002

        # # Press Launch App1 (Calculator) key
        # ctypes.windll.user32.keybd_event(VK_LAUNCH_APP1, 0, KEYEVENTF_EXTENDEDKEY, 0)
        # time.sleep(0.05)
        # # Release Launch App1 key
        # ctypes.windll.user32.keybd_event(VK_LAUNCH_APP1, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
        
        # print("runnign calkdflkasjls")
        os.system("calc.exe")