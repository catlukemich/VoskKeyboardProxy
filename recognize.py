#!/usr/bin/env python3

# prerequisites: as described in https://alphacephei.com/vosk/install and also python module `sounddevice` (simply run command `pip install sounddevice`)
# Example usage using Dutch (nl) recognition model: `python test_microphone.py -m nl`
# For more help run: `python test_microphone.py -h`

import json.decoder
import threading
import tkinter
from ttkbootstrap import ttk   
import argparse
import queue
import sys 
import sounddevice as sd
import json 
import pystray
from pywinauto.keyboard import send_keys
from PIL import Image, ImageTk

from vosk import Model, KaldiRecognizer

def rreplace(s, old, new, occurrence):
    li = s.rsplit(old, occurrence)
    return new.join(li)
def remap_command(previous_string, dictated_string):
    pl_commands_remap = {
        "kropka" : ".",
        "przecinek" : ",",
        "średnik" : ";",
        
    }
    if dictated_string in pl_commands_remap.keys():
        return pl_commands_remap[dictated_string]
    
    if dictated_string.endswith("kropka"):
        return rreplace(dictated_string, " kropka", ".", 1)

    if dictated_string == "cofnij" or dictated_string == "co w niej": # Tak właśnie.... 
        return "{BACKSPACE}" * len(previous_string)

    return dictated_string
    


class App:

    def __init__(self) -> None:
        self.running = False
        self.recognizer_thread = None
        self.interrupted = False

        self.root_window = tkinter.Tk() # Fcking root window!
        self.root_window.title("Polski - VOSK keyboard proxy")
        self.root_window.geometry("240x200")

        ico = Image.open('vosk.png')
        photo = ImageTk.PhotoImage(ico)
        self.root_window.wm_iconphoto(False, photo)


        self.lang_var = tkinter.StringVar(value="pl")
        self.language_polish =  tkinter.Radiobutton(self.root_window, text="Polish language", var=self.lang_var, value="pl", command=self.set_polish)
        self.language_polish.pack()
        self.language_english = tkinter.Radiobutton(self.root_window, text="English language", var=self.lang_var, value="en-us", command=self.set_english)
        self.language_english.pack()

        self.do_logging_var = tkinter.IntVar(value=True)
        self.logging_checkbox = tkinter.Checkbutton(self.root_window, text="Do logging", variable=self.do_logging_var)
        self.start_button = tkinter.Button(self.root_window, text="START", command=self.start_recognizer)
        self.start_button.pack()

        self.current_input = tkinter.Label(self.root_window, text="<< Current input >>")
        self.current_input.pack()


        exit_button = None
        def display_exit_button():
            nonlocal exit_button
            if exit_button is None:
                import tkinter.font
                font = tkinter.font.Font(weight="bold")
                font["size"] = 26
                exit_button = tkinter.Button(self.root_window, text="EXIT", command=lambda: self.root_window.destroy() or exit(1), bg="red", fg="white", font=font)
                exit_button.pack(ipadx=16, ipady=8, padx=10, pady=10, expand=True, fill="both")
        self.root_window.protocol("WM_DELETE_WINDOW", display_exit_button)



    def start(self):
        self.root_window.mainloop()

    def set_english(self):
        self.root_window.title("English - VOSK keyboard proxy")

        self.restart_recognizer()

    def set_polish(self):
        self.root_window.title("Polski - VOSK keyboard proxy")

        self.restart_recognizer()

    def restart_recognizer(self):
        if self.running:
            self.interrupted = True
            self.recognizer_thread.join()
            self.interrupted = False
            self.running = False
            self.start_recognizer()

    def start_recognizer(self):
        if not self.running:
            self.recognizer_thread = threading.Thread(target=self.run_recognizer)
            self.running = True
            self.start_button["text"] = "RUNNING"
            self.recognizer_thread.start()


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

        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument(
            "-l", "--list-devices", action="store_true",
            help="show list of audio devices and exit")
        args, remaining = parser.parse_known_args()
        if args.list_devices:
            print(sd.query_devices())
            parser.exit(0)
        parser = argparse.ArgumentParser(
            description=__doc__,
            formatter_class=argparse.RawDescriptionHelpFormatter,  
            parents=[parser])
        parser.add_argument(
            "-f", "--filename", type=str, metavar="FILENAME",
            help="audio file to store recording to")
        parser.add_argument(
            "-d", "--device", type=int_or_str,
            help="input device (numeric ID or substring)")
        parser.add_argument(

            "-r", "--samplerate", type=int, help="sampling rate")
        parser.add_argument(
            "-m", "--model", type=str, help="language model; e.g. en-us, fr, nl; default is en-us")
        args = parser.parse_args(remaining)

        try:
            if args.samplerate is None:
                device_info = sd.query_devices(args.device, "input")
                # soundfile expects an int, sounddevice provides a float:
                args.samplerate = int(device_info["default_samplerate"])
                

                model = Model(lang=self.lang_var.get())

            if args.filename:    
                dump_fn = open(args.filename, "wb")
            else:
                dump_fn = None

            with sd.RawInputStream(samplerate=args.samplerate, blocksize = 8000, device=args.device,
                    dtype="int16", channels=1, callback=callback, latency="low"):
                # print("#" * 80)
                # print("Press Ctrl+C to stop the recording")
                # print("#" * 80)

                rec = KaldiRecognizer(model, args.samplerate)

                print(self.interrupted)

                previous_text = ""
                while not self.interrupted:
                        
                    self.root_window.update()
                    data = q.get()
                    if rec.AcceptWaveform(data):
                        print("fdsafas", flush=True)
                        result = rec.Result()
                        parsed = json.loads(result)
                        text = parsed["text"]
                        #if not text or text.strip() == "huh":
                        #   continue
                            
                        # REMAP
                        input_text = parsed["text"]
                                 
                        processed_text = remap_command(previous_text + " ", input_text)
                        self.current_input["text"] = processed_text
                                      
                        if previous_text:                                                                       
                            stripped = previous_text.strip()
                            if len(stripped) > 0 and stripped[-1] == ".":
                                processed_text = processed_text.capitalize()
                        if processed_text.strip():
                            send_keys(processed_text + " ", with_spaces = True, pause = 0)
                            previous_text = processed_text

                        if self.do_logging_var.get():
                            with open("./current_text.txt", "a") as of:
                                of.write(parsed["text"] + " \n")
                     
                    if dump_fn is not None:
                        dump_fn.write(data)
                print("interrupted")                  

        except KeyboardInterrupt:
            print("\nDone")
            parser.exit(0)
        except Exception as e:
            parser.exit(type(e).__name__ + ": " + str(e))

        print("exititng!!!!")


if __name__ == "__main__":
    app = App()
    app.start()
