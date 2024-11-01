import os

from terminal_input_handler import TerminalInputHandler
from terminal_output_handler import TerminalOutputHandler 
from chatbot import Chatbot
from debug_logger import DebugLogger
import asyncio


if __name__ == "__main__":
    os.environ["TOKENIZERS_PARALLELISM"] = 'false'
    input_handler = TerminalInputHandler()  # Create an instance of your input handler
    output_handler = TerminalOutputHandler()  # Assuming you have a similar output handler
    debug_logger = DebugLogger(output_handler)
    chatbot = Chatbot(input_handler, output_handler, model_name="gemma2", debug_logger=debug_logger)

    # Start the chatbot
    asyncio.run(chatbot.run())
