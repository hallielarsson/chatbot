import asyncio
from input_handler import InputHandler

class TerminalInputHandler(InputHandler):
    async def get_input(self) -> str:
        """Get input from the terminal."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, input, "You: ")

    async def listen(self):
        """Continuously listen for user input in an asynchronous loop."""
        while True:
            user_input = await self.get_input()
            # Here you could handle the input further, e.g., passing it to the chatbot
            print(f"Received input: {user_input}")  # Example action; replace with actual handling
