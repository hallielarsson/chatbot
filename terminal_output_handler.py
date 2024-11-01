import asyncio
from output_handler import OutputHandler  # Ensure this imports your abstract base class

# ANSI color codes
class TerminalOutputHandler(OutputHandler):
    COLORS = {
        "error": "\033[91m",    # Red for error messages
        "system": "\033[94m",   # Blue for system messages
        "chatbot": "\033[92m",  # Green for chatbot responses
        "reset": "\033[0m"      # Reset to default color
    }

    async def send_output(self, message: str, message_type: str = "reset"):
        """Send output to the terminal asynchronously with color coding."""
        # Set color based on message type
        color = self.COLORS.get(message_type, self.COLORS["reset"])
        formatted_message = f"{color}{message}{self.COLORS['reset']}"

        # Simulate asynchronous output handling
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, print, formatted_message)
        except Exception as e:
            # Handle any exceptions that occur during printing
            print(f"{self.COLORS['error']}Error printing message: {e}{self.COLORS['reset']}")

# Example Usage
if __name__ == "__main__":
    output_handler = TerminalOutputHandler()

    # Simulating output
    asyncio.run(output_handler.send_output("This is a system message.", message_type="system"))
    asyncio.run(output_handler.send_output("This is a response from the chatbot.", message_type="chatbot"))
    asyncio.run(output_handler.send_output("This is an error message.", message_type="error"))
