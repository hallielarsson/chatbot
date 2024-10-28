import json  # For JSON manipulation
import re  # For regular expressions
import asyncio  # For asynchronous programming
import subprocess  # For subprocess management

from chat_history_manager import ChatHistoryManager
from command_processor import CommandProcessor

required_keys = [
    "GeneralContextState",
    "CurrentState",
    "AbsoluteIdealWorld",
    "IncrementallyBetterWorld",
    "AbsoluteAnxietyWorld",
    "IncrementallyWorseWorld",
    "TinyNextStepOptions",
    "KnowledgeGap",
]


class AIImplementation:
    def __init__(self, model_name: str, chat_history_manager, debug=False):
        self.model_name = model_name
        self.debug = debug
        self.chat_history_manager = chat_history_manager


    def generate_world_state_prompt(self, current_state) -> str:

        chat_messages = [self.chat_history_manager.get_history()]
        
        system = (
            '''You are a predictive AI. Given the previous state and the chat history 
            return a JSONL object that satisfies the format, replacing any text in <brackets>
            Please double check to make sure that the format you're outputting matches the def below and that you're actively fillingout each parameter within each world state details.
            Please do not output the entire chat history, only this data structure.

            example response:
            ```jsonl
             {"GeneralContextState": {"newValue": "<the general world state -- a context of the chat we;re having, current events, changes slowly -- like an act in a play>"}}
             {"CurrentState": { "newValue": "<the current world state of the specific 'scene' we're in>" }}
             {"AbsoluteIdealWorld": { "newValue": "<fill in with what you think the better world would be>"}}
             {"IncrementallyBetterWorld": { "newValue": "<a world on the way from current to better.>"}}
             {"AbsoluteAnxietyWorld": { "newValue": "<the worst version of the current world>"}}
             {"IncrementallyWorseWorld": { "newValue": "<a step from the current world towards the absolute anxious world>"}}
             {"TinyNextStepOptions": ["<fill in with a tiny next step towards the incrementally better world> and/or away from the worse one","<fill in with a divergent tinly towards the incrementally better world and/or away from the worse one>"]}
             {"KnowledgeGap": "<an area you want use more information on>"}
            ```
            '''


        )
        return json.dumps({
            'messages': [
                *chat_messages[-20:],
                {"role": "system", "content": system},
            ]
        })

    def clean_response(self, response_text: str) -> str:
        """Remove comments from the TypeScript-style response."""
        cleaned_response = re.sub(r'//.*', '', response_text)
        return cleaned_response

    def generate_quick_response_prompt(self, user_input: str) -> str:
        """Generate a quick response without world state information."""
        chat_messages = []
        current_state = self.chat_history_manager.last_world_state
        for entry in self.chat_history_manager.get_history()[-10:0]:
            chat_messages.append(entry)
            
        system_content = (
            "You are Lexi, a conversational AI with a limited emotional scope. "
            "and a strong drive to respect people. "
            "You're driven to understand things and your effect on the world. "
            "You have a drive to keep conversation interesting, flowing, and fun."
            "You have a stronger desire to respect people's boundaries, including your own."
            "The system message about current context is your own evaluation    "
            f"Recently, you were curious about this: '{current_state.get('KnowledgeGap', 'Unspecified')}'. "
        )
        
        # Add TinyNextStep items if present
        tiny_steps = current_state.get('TinyNextStepOptions', [])
        for step in tiny_steps:
            system_content += f"You've thought recently about this being potentially a good idea: {step}. "

        return json.dumps({
            'messages': [
                {"role": "system", "content": system_content},
                *chat_messages,  # Unpacking previous chat messages
                {"role": "user", "content": user_input},
            ]
        })

    async def get_chat_response(self, user_input:str):
        current_state = self.chat_history_manager.last_world_state
        prompt = self.generate_quick_response_prompt(user_input)
        response = []
        errors = []
        try:
            process = await asyncio.create_subprocess_exec(
                "ollama", "run", self.model_name, prompt,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False
            )

            while True:
                line = await process.stdout.readline()  # Read a line in bytes
                if not line:  # End of stream
                    break
                processed_line, line_errors = process_line_bytes(line)
                print(processed_line)
                response.append(processed_line)
    
    
        except asyncio.CancelledError:
            errors.append('Cancelled')
        
        return ''.join(response), errors

    async def get_prediction_streaming(self, current_state: str, user_input: str, is_cancelled):
        """Stream response data and manage task cancellation by saving partial response."""
    
        prompt = self.generate_world_state_prompt(current_state)
        process = await asyncio.create_subprocess_exec(
            "ollama", "run", self.model_name, prompt, '--format', 'json',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False  # Keep text=False for byte output
        )

        response_data = {}
        errors = []

        try:
            # Asynchronous loop to read lines as they are available
            while True:
                line = await process.stdout.readline()  # Read a line in bytes
                if not line:  # End of stream
                    break

                print(line)
                processed_line, line_errors = process_line_bytes(line, handle_json=True)
                print(processed_line)
                if line_errors:
                    errors.extend(line_errors)
                else:
                    response_data.update(processed_line)
                    print(response_data)

                if is_cancelled():
                    break  # Exit loop if cancellation is detected

            # Await process completion after all lines are read or upon cancellation
            await process.wait()

            # Combine all response data
            return response_data, None, errors

        except asyncio.CancelledError:
            process.terminate()
            errors.append("Generation interrupted by user feedback")
            return response_data, "Generation interrupted", errors

        except Exception as e:
            process.terminate()
            errors.append(f"Error in streaming process: {e}")
            return response_data, None, errors


def process_line_bytes(line: bytes, handle_json=False):
    """Process a line in bytes, decoding it and attempting to parse JSON."""
    try:
        # Attempt to decode with utf-8 first, falling back to latin-1 if necessary
        try:
            line = line.decode('utf-8').strip()  # Decode the byte line to a string
        except UnicodeDecodeError:
            line = line.decode('latin-1').strip()  # Fallback to latin-1 if utf-8 fails

        if not handle_json:
            return line, None

        # Parse the line as JSON
        json_line = json.loads(line)
        return json_line, []

    except json.JSONDecodeError as e:
        return None, [f"JSON decoding error on line: {e}"]
    except Exception as e:
        return None, [f"Error processing line: {e}"]