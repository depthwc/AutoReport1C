import json
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from dotenv import load_dotenv
import os

class AIChatWorker(QThread):
    response_ready = Signal(str)
    error_occurred = Signal(str) 

    def __init__(self, messages):
        load_dotenv(".env") 
        super().__init__()
        self.messages = messages
        self.current_df = current_df
        self.api_key = os.getenv("api")
        self.api_url = os.getenv("url")
        


    def run(self):
        if not self.api_key:
            self.error_occurred.emit("API error")
            return


        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        while True:
            payload = {
                "model": "coder",
                "messages": self.messages 
            }
            
            try:
                resp = requests.post(self.api_url, headers=headers, json=payload, timeout=40)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                self.error_occurred.emit(f"Server xatosi yoki tarmoq muammosi: {e}")
                return
                
            if "choices" in data and len(data["choices"]) > 0:
                message = data["choices"][0]["message"]
                
                self.response_ready.emit(message.get("content", ""))
                break
            else:
                self.error_occurred.emit("AI tushunarsiz javob qaytardi.")
                break
