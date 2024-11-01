class DebugLogger:
    def __init__(self, output_handler):
        self.debug_messages = []
        self.enabled = True
        self.file_name = 'debug.txt'
        self.active_log = False
        self.output_handler = output_handler
        
    async def toggle(self):
        """Toggle debug logging on or off."""
        self.enabled = not self.enabled
        status = "enabled" if self.enabled else "disabled"
        await self.output_handler.send_output(f"Debug mode {status}.", message_type="system")

    async def set_active_log(self, active: bool):
        """Set whether to actively log debug messages to the output."""
        self.active_log = active
        status = "enabled" if self.active_log else "disabled"
        await self.output_handler.send_output(f"Active log mode {status}.", message_type="system")

    async def log(self, message: str):
        """Log a debug message if logging is enabled."""
        if self.enabled:
            self.debug_messages.append(message)
            if self.active_log:
                await self.output_handler.send_output(message, message_type="system")

    async def flush(self):
        """Send all debug messages to the output handler."""
        for message in self.debug_messages:
            await self.output_handler.send_output(message, message_type="system")
        self.debug_messages.clear()  # Clear messages after flushing

    import os

    class DebugLogger:
        def __init__(self, output_handler, file_name='debug_log.txt'):
            self.debug_messages = []
            self.enabled = True
            self.active_log = False
            self.output_handler = output_handler
            self.file_name = file_name  # Default file name for logging

        async def toggle(self):
            """Toggle debug logging on or off."""
            self.enabled = not self.enabled
            status = "enabled" if self.enabled else "disabled"
            await self.output_handler.send_output(f"Debug mode {status}.", message_type="system")

        async def set_active_log(self, active: bool):
            """Set whether to actively log debug messages to the output."""
            self.active_log = active
            status = "enabled" if self.active_log else "disabled"
            await self.output_handler.send_output(f"Active log mode {status}.", message_type="system")

        async def log(self, message: str):
            """Log a debug message if logging is enabled."""
            if self.enabled:
                self.debug_messages.append(message)
                await self.write_to_file()
                if self.active_log:
                    await self.output_handler.send_output(message, message_type="system")

        async def flush(self):
            """Send all debug messages to the output handler and clear the message buffer."""
            for message in self.debug_messages:
                await self.output_handler.send_output(message, message_type="system")
            self.debug_messages.clear()  # Clear messages after flushing

        async def write_to_file(self):
            """Write all debug messages to a specified file."""
            if not self.debug_messages:
                await self.output_handler.send_output("No messages to write to file.", message_type="system")
                return

            try:
                with open(self.file_name, 'a') as file:  # Append mode to keep existing logs
                    for message in self.debug_messages:
                        file.write(message + '\n')
                await self.output_handler.send_output(f"Debug messages written to {self.file_name}.",
                                                      message_type="system")
            except IOError as e:
                await self.output_handler.send_output(f"Error writing to file: {str(e)}", message_type="error")

            self.debug_messages.clear()  # Clear after writing to file
