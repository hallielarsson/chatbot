import json
import os
import time

class ChatHistoryManager:
    def __init__(self, history_file='chat_history.jsonl', state_file='last_world_state.json'):
        self.history_file = history_file
        self.state_file = state_file
        self.state_history_file = 'world_states.jsonl'
        self.chat_history = []
        self.world_state_history = []
        self.last_world_state = {}

    def get_timestamp(self):
        return time.strftime("%Y-%m-%d %H:%M:%S")

    def get_history(self):
        return self.chat_history

    def rate_chat(self, value):
        
        self.chat_history[-1]['rating'] = value

    def archive_history(self):
        if not os.path.exists('./logs'):
            os.makedirs('./logs')
        timestr = time.strftime("%Y%m%d-%H%M%S")
        archive_file = f'./logs/{timestr}.chat_history.jsonl'
        self.save_history(archive_file)
        self.chat_history = []  # Clear current chat history after archiving
        self.save_history()

    def save_history(self, filename=None):
        if not filename:
            filename = self.history_file
        with open(filename, 'w') as file:
            for entry in self.chat_history:
                json.dump(entry, file)
                file.write('\n')
        print(f"Chat history saved to {filename}.")

    def log_chat(self, role, content):
        """Logs a single chat entry to the history."""
        entry = {"role": role, "content": content, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}
        self.chat_history.append(entry)

    def save_last_world_state(self):
        with open(self.state_file, 'w') as file:
            json.dump(self.last_world_state, file)
        with open(self.state_history_file, 'a') as file:
            json.dump(self.last_world_state, file)
            file.write('\n')
        print(f"Last world state saved to {self.state_file}.")

    def load_history(self):
        self.chat_history = []
        try:
            with open(self.history_file, 'r') as file:
                for line in file:
                    self.chat_history.append(json.loads(line))
            print(f"Chat history loaded from {self.history_file}.")
        except FileNotFoundError:
            print(f"{self.history_file} not found. Starting with an empty chat history.")

    def load_last_world_state(self):
        try:
            with open(self.state_history_file, 'r') as file:
                self.world_state_history = []
                for line in file:
                    self.world_state_history.append(json.loads(line))
        except (FileNotFoundError, json.JSONDecodeError):
            self.world_state_history = []
            print(f"Error loading world state. Starting with an empty world state.")
        try:
            with open(self.state_file, 'r') as file:
                self.last_world_state = json.load(file)
            print(f"Last world state loaded from {self.state_file}.")
        except (FileNotFoundError, json.JSONDecodeError):
            self.last_world_state = {}
            print(f"Error loading world state. Starting with an empty world state.")

    def update_world_state(self, state):
        for key, value in state.items():
            if key in self.last_world_state:
                self.last_world_state[key] = value
        new_state = self.last_world_state.update(state)
        self.log_world_state(new_state)

    def log_world_state(self, state):
        self.last_world_state = state
        self.world_state_history.append(state)
        self.save_last_world_state()