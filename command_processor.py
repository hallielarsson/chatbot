import subprocess
import json

from debug_logger import DebugLogger


async def handle_exit(command):
    """Handle the exit command."""
    return "exit", False


class CommandProcessor:
    def __init__(self, chat_history_manager, ai, output_handler, debug_logger:DebugLogger):
        self.chat_history_manager = chat_history_manager
        self.world_state_manager = self.chat_history_manager.world_state_manager
        self.ai = ai
        self.output_handler = output_handler
        self.debug_logger = debug_logger
        
        # Define command handlers
        self.command_handlers = {
            "/exit": handle_exit,
            "/debug": self.toggle_debug,
            "/save": self.handle_save,
            "/archive": self.handle_archive,
            "/load": self.handle_load,
            "/states": self.handle_states,
            "/+": self.handle_rate_chat_positive,
            "/-": self.handle_rate_chat_negative,
            "/c ": self.handle_console_command
        }

    async def toggle_debug(self):
        """Toggle the debug logger."""
        await self.debug_logger.toggle()

    async def set_active_log(self, active: bool):
        """Set whether to actively log debug messages to the output."""
        await self.debug_logger.set_active_log(active)

    async def execute_command(self, command):
        """Execute a command and return its output and pass_on flag."""
        if command.startswith('/i '):
            inputs = command[3:].split('/')
            output, pass_on = await self.execute_command(''.join(inputs[1:]))
            output = output or "NO OUTPUT"
            return inputs[0] + '->' + output, pass_on

        for cmd_prefix, handler in self.command_handlers.items():
            if command.startswith(cmd_prefix):
                return await handler(command)

        return "Unrecognized command.", False

    async def handle_save(self, command):
        """Handle the save command."""
        self.chat_history_manager.save_logs()
        self.chat_history_manager.save_last_world_state()
        return "History saved.", False

    async def handle_archive(self, command):
        """Handle the archive command."""
        self.chat_history_manager.archive_history()
        self.chat_history_manager.save_last_world_state()
        return "History archived.", False

    async def handle_load(self, command):
        """Handle the load command."""
        self.chat_history_manager.load_history()
        self.world_state_manager.load_last_world_state()
        return "History loaded.", False

    async def handle_states(self, command):
        """Handle the states command."""
        return json.dumps(self.world_state_manager.last_world_state, indent=2), False

    async def handle_rate_chat_positive(self, command):
        """Rate chat positively."""
        self.chat_history_manager.rate_chat(1)
        return "Chat rated positively.", False

    async def handle_rate_chat_negative(self, command):
        """Rate chat negatively."""
        self.chat_history_manager.rate_chat(-1)
        return "Chat rated negatively.", False

    async def handle_console_command(self, command):
        """Process and execute a console command."""
        command = command[3:]  # Remove the '/c ' prefix
        return await self.process_console_command(command)

    async def process_console_command(self, command):
        """Process and execute a console command."""
        pass_on = command.rstrip().endswith('|')
        if pass_on:
            command = command.rstrip()[:-1].strip()

        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            output = result.stdout.strip() if result.returncode == 0 else f"Error running command: {result.stderr.strip()}"

            if self.debug_logger.enabled:
                await self.debug_logger.log(f"Executed command: {command}, Output: {output}")
                await self.debug_logger.flush()

            return output, pass_on

        except Exception as e:
            error_msg = f"Failed to run command: {e}"
            if self.debug_logger.enabled:
                await self.debug_logger.log(error_msg)
            return error_msg, pass_on
