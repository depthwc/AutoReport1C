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

    def __init__(self, messages, current_df=None):
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
                "messages": self.messages,
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "get_full_table_data",
                            "description": "Returns the full dataset table containing all sales records. Use this only if the user asks detailed questions that require reading all rows.",
                            "parameters": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        }
                    }
                ]
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
                
                if message.get("tool_calls"):
                    self.messages.append(message)
                    for tool_call in message["tool_calls"]:
                        if tool_call["function"]["name"] == "get_full_table_data":
                            if self.current_df is not None and not self.current_df.empty:
                                import report_fun
                                table_str = report_fun.get_table_info(self.current_df).to_string(index=False)
                            else:
                                table_str = "Hozircha hech qanday jadval faol emas."
                            
                            self.messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "name": tool_call["function"]["name"],
                                "content": table_str
                            })
                    continue

                self.response_ready.emit(message.get("content", "") or "")
                break
            else:
                self.error_occurred.emit("AI tushunarsiz javob qaytardi.")
                break
