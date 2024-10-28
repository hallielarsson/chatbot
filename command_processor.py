import subprocess
import json
import pandas as pd    


class CommandProcessor:
    def __init__(self, chat_history_manager, ai):
        self.chat_history_manager = chat_history_manager
        self.ai = ai
        self.debug = False

    def toggle_debug(self):
        self.debug = not self.debug
        print(f"Debug mode {'enabled' if self.debug else 'disabled'}.")

    def execute_command(self, command):
        if command.startswith('/i '):
            inputs = command[3:].split('/')
            output, pass_on =  self.execute_command(''.join(inputs[1:]))
            output = output or "NO OUTPUT"
            return inputs[0] + '->' + output, pass_on
            
        if command == "/exit":
            return "exit", False
        elif command == "/debug":
            self.toggle_debug()
        elif command == "/save":
            self.chat_history_manager.save_history()
            self.chat_history_manager.save_last_world_state()
        elif command == "/archive":
            self.chat_history_manager.archive_history()
            self.chat_history_manager.save_last_world_state()
        elif command == "/load":
            self.chat_history_manager.load_history()
            self.chat_history_manager.load_last_world_state()
        elif command == "/states":
            return json.dumps(self.chat_history_manager.last_world_state, indent=2), False
        elif command == '/+':
            self.chat_history_manager.rate_chat(1)
        elif command == '/-':
            self.chat_history_manager.rate_chat(-1)
        elif command.startswith('/c '):
            command = command[3:]
            output, pass_on = self.process_console_command(command)
            return output, pass_on

        else:
            return "Unrecognized command.", False
        return "", False


    def process_console_command(self, command):
        # Remove only trailing whitespace (not '|') before checking
        pass_on = command.rstrip().endswith('|')
        print(pass_on, command, command.rstrip())
        if pass_on:
            # Remove the trailing '|' to prepare the command for execution
            command = command.rstrip()[:-1].strip()

        try:
            # Execute the command and capture output
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            output = result.stdout.strip() if result.returncode == 0 else f"Error running command: {result.stderr.strip()}"
            print(output)  # Print to console for visibility

            # Return output and pass_on flag to indicate if this should be fed into AI
            return output, pass_on

        except Exception as e:
            error_msg = f"Failed to run command: {e}"
            print(error_msg)
            return error_msg, pass_on