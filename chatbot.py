import subprocess
import json
import re
from typing import Dict, Any, Optional
from chat_history_manager import ChatHistoryManager
from command_processor import CommandProcessor
from ai_implementation import AIImplementation
import asyncio

debug = False

async def world_state_generation(ai, chat_manager, user_input):
    generation_task = asyncio.create_task(
        ai.get_prediction_streaming(current_state=chat_manager.last_world_state, user_input=user_input, is_cancelled=lambda: False)
    )

    try:
        prediction, _, errors = await generation_task
        if prediction:
            chat_manager.log_world_state(prediction)
            chat_manager.log_chat(role='system', content=prediction)
        else:
            chat_manager.log_chat(role='system', content=f"[ERROR PROCESSING RESPONSE] {errors}")
    
    except asyncio.CancelledError:
        if generation_task:
            generation_task.cancel()
            try:
                partial_result, _, errors = await generation_task  # Get partial data if available
                if partial_result:
                    print("Partial data retained after cancellation.")
                    chat_manager.update_world_state(partial_result)
                chat_manager.log_chat(role='system', content="[PARTIAL RESPONSE DUE TO CANCELLATION]")

            except asyncio.CancelledError:
                print("Generation task was successfully cancelled with no partial data.")
        print("Generation interrupted by user feedback.")

        
async def async_input(prompt: str = "") -> str:
    """Helper function to get asynchronous user input."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, input, prompt)


async def main():
    model_name = "gemma2"
    chat_manager = ChatHistoryManager()
    ai = AIImplementation(model_name, chat_manager)
    command_processor = CommandProcessor(chat_manager, ai)
    generation_task = None  # Placeholder for the generation task

    chat_manager.load_history()
    chat_manager.load_last_world_state()

    while True:
        print("Restarting loop...")
        user_input = (await async_input("You: ")).strip()

        # Handle cancellation of previous generation task
        if generation_task and not generation_task.done():
            generation_task.cancel()
            print("Wrapping up world state genration.")
            try:
                await generation_task  # Ensure cleanup
                print("Previous generation task was successfully cancelled.")
            except asyncio.CancelledError:
                print("Previous generation task was successfully cancelled.")

            print("Finished wrapping up world state generation.")

        chat_manager.log_chat(role='user', content=user_input)

        # Command processing
        if user_input.startswith("/"):
            result, pass_on = command_processor.execute_command(user_input.strip())
            chat_manager.log_chat(role='system', content=result)
            print(result)
            if result == "exit":
                break
            else:
                user_input = f"<User ran {user_input} with result {result}>"
            if not pass_on:
                continue

        print("Generating response...")
        # Immediate Response
        quick_response, errors = await ai.get_chat_response(
            user_input=user_input,
        )
        chat_manager.log_chat(role='assistant', content=quick_response)

        # Optionally, handle errors if needed
        if errors:
            chat_manager.log_chat(role='system', content=f"[ERROR] {errors}")

        print("Generating world state")
        # Prepare for a world state generation task
        generation_task = asyncio.create_task(
            world_state_generation(ai, chat_manager, user_input)
        )



if __name__ == "__main__":
    asyncio.run(main())  # Use asyncio.run to start the async main function
