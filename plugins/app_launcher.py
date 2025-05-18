import os
from .plugin import Plugin

class AppLauncher(Plugin):
    
    def __init__(self):
        self.start_sentence = "system start"
        # Executiables names must be in system PATH variable
        self.apps_map = {
            "calculator",
            "browser",
            "server",
            "sleep"
        }
    
    def requires_keyboard(self):
        return False
    
    def trigger_text(self):
        start_sentence = "system" 
        
        app_names = [
            "calculator",
            "browser",
            "server",
            "calculator",
            "sleep",
            "uśpić"
        ]
        
        return [f"{start_sentence} {app}"for app in app_names]
        
    
    def execute_command(self, triggered_text : str ):
        if "sleep" in triggered_text or "uśpić" in triggered_text:
            os.system("%windir%\\System32\\rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        
        # app = triggered_text.replace(self.start_sentence + " ", "");
        
        # executable = [
            
        # ]
        # calculator
        # os.system()