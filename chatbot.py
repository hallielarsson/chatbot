import asyncio

from chat_history.chat_history_manager import ChatHistoryManager
from command_processor import CommandProcessor
from ai_implementation import AIImplementation
from input_handler import InputHandler
from output_handler import OutputHandler  # Assuming you have this
from debug_logger import DebugLogger


class Chatbot:
    def __init__(self, input_handler: InputHandler, output_handler: OutputHandler, model_name: str, debug_logger=None):
        self.debug_logger = debug_logger or DebugLogger(output_handler)
        self.chat_manager = ChatHistoryManager(output_handler, self.debug_logger)
        self.ai = AIImplementation(
            model_name,
            self.chat_manager,
            debug_logger=self.debug_logger,
            output_handler=output_handler,

           )
        self.command_processor = CommandProcessor(self.chat_manager,
                                                  self.ai,
                                                  output_handler,
                                                  debug_logger=self.debug_logger)
        self.input_handler = input_handler
        self.output_handler = output_handler
        self.generation_task = None

    async def load(self):
        await self.chat_manager.load_history()
        await self.chat_manager.load_last_world_state()

    async def listen(self):
        """Listen for user input using the input handler."""
        return await self.input_handler.get_input()

    async def world_state_generation(self, user_input):
        history_manager = self.chat_manager
        state_manager = history_manager.world_state_manager
        self.generation_task = asyncio.create_task(
            self.ai.get_prediction_streaming(
                current_state=state_manager.last_world_state,
                user_input=user_input,
                is_cancelled=lambda: False)
        )

        try:
            prediction, errors = await self.generation_task
            if prediction:
                await state_manager.update_world_state(prediction)
                # await history_manager.log_chat(role='system', content=prediction)
            else:
                await history_manager.log_chat(role='system', content=f"[ERROR PROCESSING RESPONSE] {errors}")

        except asyncio.CancelledError:
            if self.generation_task:
                self.generation_task.cancel()
                try:
                    partial_result, errors = await self.generation_task  # Get partial data if available
                    if partial_result:
                        await self.debug_logger.log("Partial data retained after cancellation.")
                        await state_manager.update_world_state(partial_result)
                    await history_manager.log_chat(role='system', content="[PARTIAL RESPONSE DUE TO CANCELLATION]")

                except asyncio.CancelledError:
                    await self.debug_logger.log("Generation task was successfully cancelled with no partial data.")
            await self.debug_logger.log("Generation interrupted by user feedback.")

    async def handle_input(self):
        """Handles user input and processes commands or chat responses."""
        while True:
            user_input = await self.listen()  # Call the listen method to get user input
            if self.generation_task and not self.generation_task.done():
                self.generation_task.cancel()
                await self.debug_logger.log("Wrapping up world state genration.")
                try:
                    await self.generation_task  # Ensure cleanup
                    await self.debug_logger.log("Previous generation task was successfully cancelled.")
                except asyncio.CancelledError:
                    await self.debug_logger.log("Previous generation task was successfully cancelled.")

                await self.debug_logger.log("Finished wrapping up world state generation.")

            await self.chat_manager.log_chat(role='user', content=user_input)
            await self.debug_logger.log("Chat logged")
            # Command processing
            if user_input.startswith("/"):
                result, pass_on = await self.command_processor.execute_command(user_input.strip())
                await self.chat_manager.log_chat(role='system', content=result)
                await self.output_handler.send_output(result)

                if result == "exit":
                    break
                else:
                    user_input = f"<User ran {user_input} with result {result}>"

                if not pass_on:
                    continue

            # Generate response
            await self.debug_logger.log("User input processed")
            quick_response, errors = await self.ai.get_chat_response(user_input=user_input)
            await self.chat_manager.log_chat(role='assistant', content=quick_response)

            # Handle errors if needed
            if errors:
                await self.chat_manager.log_chat(role='system', content=f"[ERROR] {errors}")

            # Output the response
            await self.output_handler.send_output(quick_response)
            await self.world_state_generation(user_input)

    async def run(self):
        """Main method to run the chatbot."""
        await self.output_handler.send_output("Chatbot is starting...")
        await self.load()
        await self.handle_input()
