import json
import os
import time


class ChatHistoryManager:
    def __init__(self, history_file='chat_history.txt', state_file='last_world_state.json'):
        self.history_file = history_file
        self.state_file = state_file
        self.chat_history = ""
        self.last_world_state = {}


    def archive_history(self):
        if not os.path.exists('./logs'):
            os.makedirs('./logs')
        timestr = time.strftime("%Y%m%d-%H%M%S")
        self.save_history(f'./logs/{timestr}.log.txt')
        self.chat_history = ""
        self.save_history()


    def save_history(self, filename=None):
        if not filename:
            filename = self.history_file
        with open(filename, 'w') as file:
            file.write(self.chat_history)
        print(f"Chat history saved to {filename}.")

    def save_last_world_state(self):
        with open(self.state_file, 'w') as file:
            json.dump(self.last_world_state, file)
        print(f"Last world state saved to {self.state_file}.")

    def load_history(self):
        try:
            with open(self.history_file, 'r') as file:
                self.chat_history = file.read()
            print(f"Chat history loaded from {self.history_file}.")
        except FileNotFoundError:
            self.chat_history = ""
            print(f"{self.history_file} not found. Starting with an empty chat history.")

    def load_last_world_state(self):
        try:
            with open(self.state_file, 'r') as file:
                self.last_world_state = json.load(file)
            print(f"Last world state loaded from {self.state_file}.")
        except (FileNotFoundError, json.JSONDecodeError):
            self.last_world_state = {}
            print(f"Error loading world state. Starting with an empty world state.")
