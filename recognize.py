#!/usr/bin/env python3

# prerequisites: as described in https://alphacephei.com/vosk/install and also python module `sounddevice` (simply run command `pip install sounddevice`)
# Example usage using Dutch (nl) recognition model: `python test_microphone.py -m nl`
# For more help run: `python test_microphone.py -h`

import os
import sys 
import json 
import threading
import time
import queue
import json.decoder
import tkinter as tk
import pyperclip
import tkinter.messagebox
from tkinter.ttk import * 
# from ttkbootstrap import * 
import sounddevice as sd
import shelve
from pywinauto.keyboard import send_keys
from PIL import Image, ImageTk

from vosk import Model, KaldiRecognizer

command_switch_to_english = "<<VOSK COMMAND: LANGUAGE - en-us>>"
command_switch_to_polish = "<<VOSK COMMAND: LANGUAGE - pl>>"


def rreplace(s, old, new, occurrence):
    li = s.rsplit(old, occurrence)
    return new.join(li)

def remap_command(previous_string, dictated_string):
    commands_remap = {
        "kropka" : ".",
        "przecinek" : ",",
        "średnik" : ";",
        "szukaj" : "{VK_LCONTROL down}F{VK_LCONTROL up}",
        "find" : "{VK_LCONTROL down}F{VK_LCONTROL up}",
        "po angielsku": command_switch_to_english,
        "to polish": command_switch_to_polish,
    }
    if dictated_string in commands_remap.keys():
        return commands_remap[dictated_string]
    
    if dictated_string.endswith("kropka") or dictated_string.endswith("period"):
        return rreplace(dictated_string, " kropka", ".", 1)

    if dictated_string == "cofnij" or dictated_string == "co w niej": # Tak właśnie.... hmmm 
        return "{BACKSPACE}" * len(previous_string)
    
  
    return dictated_string
    


class App:

    def __init__(self) -> None:
        self.main_thread_queue = queue.Queue()
        
        try:
            self.shelve = shelve.open("vosk-keyboard-proxy.dat")
        except Exception as e:
            # The shelve got screwed up, so recreate the file
            os.unlink("vosk-keyboard-proxy.dat")
            self.shelve = shelve.open("vosk-keyboard-proxy.dat") # Hahaha xD trololo
            
        
                
        self.language = "pl" if not "language" in self.shelve else self.shelve["language"]
        self.autostart = False if not "autostart" in self.shelve else self.shelve["autostart"]
        self.do_logging = False if not "do_logging" in self.shelve else self.shelve["do_logging"]
        
        if "language" in self.shelve:
            self.language = self.shelve["language"]
                
        self.running = False
        self.recognizer_thread = None
        self.interrupted = False

        self.root_window = tk.Tk() # Fcking root window!
        self.root_window.title("Polski - VOSK keyboard proxy")
        self.root_window.geometry("240x400")
        self.taskbar_anim = None

        ico = Image.open('vosk.png')
        photo = ImageTk.PhotoImage(ico)
        self.root_window.wm_iconphoto(False, photo)


        self.lang_var = tk.StringVar(value=self.language)
            
        self.language_polish =  Radiobutton(self.root_window, text="Polish language", var=self.lang_var, value="pl", command=lambda: self.switch_language())
        self.language_polish.pack()
        self.language_english = Radiobutton(self.root_window, text="English language", var=self.lang_var, value="en-us", command=lambda: self.switch_language())
        self.language_english.pack()
        
        self.update_title()
        
        self.do_logging_var = tk.IntVar(value=self.do_logging)
        def on_logging_toggle(): # Just update the shelve with the logging new state.
            self.shelve["do_logging"] = self.do_logging_var.get()
        self.logging_checkbox = Checkbutton(self.root_window, text="Do logging", variable=self.do_logging_var, command=on_logging_toggle)
        self.logging_checkbox.pack(padx=5, pady=5)
        
        self.latest_entries_box = tk.Listbox(self.root_window, width=150)
        self.latest_entries_box.pack(padx=5, pady=5)
        self.latest_entries_box.bind("<Double-Button-1>", lambda e: pyperclip.copy(self.latest_entries_box.get(ANCHOR)))
        
        self.recognizer_running = False
        def toggle_recognizer():
            if not self.recognizer_running:
                self.running = False
                self.interrupted = False
                self.start_recognizer()
                self.start_button["text"] = "STOP"
                self.start_button["bg"] = "red"
                self.start_taskbar_icon_anim()
            else:
                self.interrupted = True
                self.start_button["text"] = "START"
                self.start_button["bg"] = "green"
                self.stop_taskbar_icon_anim()
                self.running = False
            self.recognizer_running = not self.recognizer_running
                
        self.start_button = tk.Button(self.root_window, text="START", command=toggle_recognizer)
        self.start_button["text"] = "START"
        self.start_button["fg"] = "white"
        self.start_button["bg"] = "green"
        self.start_button.pack()

        self.current_input = Label(self.root_window, text="<< Current input >>")
        self.current_input.pack()

        
        autostart_var = tk.BooleanVar(value=False)
        def toggle_autostart():
            autostart = autostart_var.get()
            self.shelve["autostart"] = autostart
        self.autostart_checkbox = Checkbutton(self.root_window, text="Autostart", variable=autostart_var, command=toggle_autostart)
        self.autostart_checkbox.pack(padx=5, pady=5)
        
        self.autostart = False
        if "autostart" in self.shelve:
            self.autostart = self.shelve["autostart"]
            autostart_var.set(self.autostart)
        else:
            self.shelve["autostart"] = self.autostart
            
        exit_button = None
        last_click_time = time.time() * 1000
        def handle_window_close():
            def exit_app():
                self.shelve.sync()
                self.shelve.close()
                self.interrupted = True
                if self.recognizer_thread:
                    self.recognizer_thread.join()
                self.root_window.destroy()
                self.root_window.quit()
                exit(1)
                
            nonlocal last_click_time
            click_time = time.time() * 1000
            print(click_time - last_click_time)
            if click_time - last_click_time < 1600:
                exit_app()
            last_click_time = click_time
            
            
            nonlocal exit_button
            if exit_button is None:
                import tkinter.font
                font = tkinter.font.Font(weight="bold")
                font["size"] = 26
                exit_button = tk.Button(self.root_window, text="EXIT", command=exit_app, bg="red", fg="white", font=font)
                exit_button.pack(ipadx=10, ipady=6, padx=4, pady=8, expand=True, fill="both")
        self.root_window.protocol("WM_DELETE_WINDOW", handle_window_close)

        if self.autostart:
            toggle_recognizer()

        self.shelve.sync()

        self.run_main_thread_queue_handler()
        
        
    def run_main_thread_queue_handler(self):
     
        def read_and_evaluate_queue():
            try:
                func = self.main_thread_queue.get(block=False)
                if func: func()
            except queue.Empty:
                pass
            self.root_window.after(100, read_and_evaluate_queue)
            
        self.root_window.after(100, read_and_evaluate_queue)




    def start(self):
        self.root_window.mainloop()

        
    def switch_language(self):
        self.shelve["language"] = self.lang_var.get()
        self.language = self.lang_var.get()
        self.update_title()
        if self.running:
            self.root_window.after(10, self.restart_recognizer)
            
    def update_title(self):
        langs_map = {
            "pl": "polski",
            "en-us": "english"
        }
        
        language = langs_map[self.language]
        
        self.root_window.title(f"VOSK: {language.capitalize()} - keyboard proxy")
 
    def restart_recognizer(self):
        if self.running:
            self.interrupted = True
            if self.recognizer_thread:
                self.recognizer_thread.join()
            self.interrupted = False
            self.running = False
            self.start_recognizer()

    def start_recognizer(self):
        if not self.running:
            if self.recognizer_thread:
                self.recognizer_thread.join()
            self.recognizer_thread = threading.Thread(target=self.run_recognizer)
            self.running = True
            self.start_taskbar_icon_anim()
            self.recognizer_thread.start()

    
    def start_taskbar_icon_anim(self):
        icon_normal = Image.open('vosk.png')
        icon_recording = Image.open('vosk_rec.png')
        photo_normal = ImageTk.PhotoImage(icon_normal)
        photo_recording = ImageTk.PhotoImage(icon_recording)
        
        def animate():
            self.record_icon_state = not self.record_icon_state
            if self.record_icon_state: 
                self.root_window.wm_iconphoto(False, photo_recording)
            else:
                self.root_window.wm_iconphoto(False, photo_normal)
            self.taskbar_anim = self.root_window.after(500, animate)
        if not self.taskbar_anim:
            self.record_icon_state = False
            self.taskbar_anim = self.root_window.after(500, animate)
        
    def stop_taskbar_icon_anim(self):
        self.root_window.after_cancel(self.taskbar_anim)
        icon_normal = Image.open('vosk.png')
        photo_normal = ImageTk.PhotoImage(icon_normal)
        self.root_window.wm_iconphoto(False, photo_normal)
        self.record_icon_stat = False
        self.taskbar_anim = None
    

    def run_recognizer(self): 
        q = queue.Queue()


        def int_or_str(text):
            """Helper function for argument parsing."""
            try:
                return int(text)
            except ValueError:
                return text

        def callback(indata, frames, time, status):
            """This is called (from a separate thread) for each audio block."""
            if status:
                print(status, file=sys.stderr)
            q.put(bytes(indata))

        try:
            device_info = sd.query_devices(0, "input")
            # soundfile expects an int, sounddevice provides a float:
            samplerate = int(device_info["default_samplerate"])


            model = Model(lang=self.lang_var.get())


            with sd.RawInputStream(samplerate=samplerate, blocksize = 600, device=0,
                    dtype="int16", channels=1, callback=callback, latency="high"):

                rec = KaldiRecognizer(model, samplerate)

                # print(len(sd.query_devices()))


                previous_text = ""
                while not self.interrupted:
                    self.recording = True

                    data = q.get()
                    if rec.AcceptWaveform(data):
                        result = rec.Result()
                        parsed = json.loads(result)
                        text = parsed["text"]
                        if not text or text.strip() == "huh":
                            # The damn quiet "huh" is too much for me..
                            continue
                            
                        # REMAP
                        input_text = text
                        processed_text = remap_command(previous_text + " ", input_text)
                        
                        def to_polish():
                            self.lang_var.set("pl")
                            self.switch_language()
                        def to_english():
                            self.lang_var.set("en-us")
                            self.switch_language()
                        
                        if processed_text == command_switch_to_polish:
                            self.interrupted = True
                            self.main_thread_queue.put(to_polish)
                            return
                        if processed_text == command_switch_to_english:
                            self.interrupted = True
                            self.main_thread_queue.put(to_english)
                            return
                        
                        def set_last_text():
                            self.current_input["text"] = processed_text
                        self.main_thread_queue.put(set_last_text)

                        if previous_text:                                                                       
                            stripped = previous_text.strip()
                            if len(stripped) > 0 and stripped[-1] == ".":
                                processed_text = processed_text.capitalize()
                        if processed_text.strip():
                            send_keys(processed_text + " ", with_spaces = True, pause = 0)
                            previous_text = processed_text

                        self.latest_entries_box.insert(0, text)
                        
                        def print_to_log_conditionaly():
                            if self.do_logging_var.get():
                                self.log_text(text)
                        
                        self.main_thread_queue.put(print_to_log_conditionaly)
                        
                        self.root_window.update()

        except Exception as e:
            print(e)
            pass
        finally:
            self.interrupted = True
            self.recording = False
            

    def log_text(self, text):
        import locale
        locale.setlocale(locale.LC_ALL, "pl-PL")
        import time
        import datetime
        date_title = "Date of recordings: "
        
        today = time.localtime()
        today_name = datetime.date.today().strftime("%A").upper()
        
        today_date_string = str(today.tm_year) + "/" + str(today.tm_mon).zfill(2) + "/" + str(today.tm_mday).zfill(2)  \
           + " | day of year: " +  str(today.tm_yday).zfill(3)
           
        # Search for a "Date of recordings: "
        prepend_date = True # Whether to prepend date before the next log line:
        prepend_newline = False # Dont place newline character when there was no entry or date - the file is empty
        with open("./text_log.txt", "r", encoding="utf-8") as logfile:
            lines = logfile.readlines()
            for line_idx in range(len(lines) - 1, -1, -1):
                line = lines[line_idx]
                if date_title in line:
                    date_start_idx = len(date_title)
                    date_end_idx = date_start_idx + len(today_date_string)
                    last_date_string = line[date_start_idx:date_end_idx]
                    
                    if last_date_string == today_date_string:
                        prepend_date = False
                        prepend_newline = True
                        break
                    if last_date_string != today_date_string:
                        prepend_date = True
                        prepend_newline = True
                        break
        
        todays_time = str(today.tm_hour).zfill(2) + ":" + str(today.tm_min).zfill(2) + ":" + str(today.tm_sec).zfill(2) + ": "
        with open("./text_log.txt", "a", encoding="utf-8") as of:
            if prepend_date:
                if prepend_newline:
                    of.write("\n")
                    print("newlinge")
                of.write(date_title + today_date_string + " " + today_name + "\n")
            of.write(todays_time + text + " \n")
        

    


if __name__ == "__main__":
    app = App()
    app.start()
