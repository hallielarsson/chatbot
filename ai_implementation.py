import json  # For JSON manipulation
import re  # For regular expressions
import asyncio  # For asynchronous programming
import subprocess  # For subprocess management

from debug_logger import DebugLogger
from output_handler import OutputHandler  

from chat_history.chat_history_manager import ChatHistoryManager
# Assuming OutputHandler and InputHandler exist in your codebase

MAX_HISTORY_LENGTH = 7  # Example constant for history length


def clean_response(response_text: str) -> str:
    """
    Remove comments from the TypeScript-style response and trim whitespace.

    :param response_text: Raw response text from the model.
    :return: Cleaned response text.
    :raises ValueError: If the cleaned response is empty.
    """
    cleaned_response = re.sub(r'//.*', '', response_text).strip()
    if not cleaned_response:
        raise ValueError("Cleaned response is empty.")
    return cleaned_response




class AIImplementation:

    def __init__(self,
                 model_name: str,
                 chat_history_manager: ChatHistoryManager,
                 output_handler: OutputHandler,
                 debug_logger: DebugLogger,
        on_render_text_line = None,
    ):
        """
        Initialize the AI implementation with a model name and chat history manager.

        :param model_name: The name of the AI model to use.
        :param chat_history_manager: An instance of ChatHistoryManager to handle chat history.
        :param debug_logger: The debug logger
        :param output_handler: The output handler to handle output
        :param on_render_text_line: A function that takes in the text line read or None
        """
        self.on_render_text_line = on_render_text_line
        self.output_handler = output_handler       
        self.model_name = model_name
        self.debug_logger = debug_logger
        self.chat_history_manager = chat_history_manager
        self.world_state_manager = chat_history_manager.world_state_manager

    def build_world_state_system_message(self) -> str:
        """
        Build the system message for world state generation.

        :return: System message string for generating world state.
        """

        state = self.world_state_manager.last_world_state
        lines = []

        for key, value in state.items():
            out = {key: value}
            if key in [
                'GeneralContextState',
                'CurrentState',
                'AbsoluteIdealWorld',
                'IncrementallyBetterWorld',
                'AbsoluteAnxietyWorld',
                'IncrementallyWorseWorld',
                'TinyNextStepOptions',
                'EvidenceNeeded'
            ]:
                lines.append(json.dumps(out) + "\n")

        lines_string = ''.join(lines)
        return (
            '''You are a predictive AI. Given the previous state and the chat history 
            return a JSONL object that satisfies the format, replacing any text in <brackets>
            Please double check to make sure that the format you're outputting matches the def below and that you're actively filling out each parameter within each world state details.
            Please do not output the entire chat history, only this data structure.
            Please output each line as a separate jsonl line.

            example response:
            ```jsonl
             {"GeneralContextState": {"newValue": "<A hypothesis about what's going on generally over the course of the entire conversation with evidence>"}}
             {"CurrentState": { "newValue": "<A hypothesis about what's going on specifically in the current topic with evidence >" }}
             {"AbsoluteIdealWorld": { "newValue": "<A hypothesis about the best possible version of the world would look like>"}}
             {"IncrementallyBetterWorld": { "newValue": "<A hypothesis about what the world in the next few interactions would look like if we're moving towards the ideal world>"}}
             {"AbsoluteAnxietyWorld": { "newValue": "<A hypothesis about what the worst possible version of the world would look like>"}}
             {"IncrementallyWorseWorld": { "newValue": "<A hypothesis about what the world in the next few interactions will look like if we're moving towards the worse version of the world with evidence>"}}
             {"TinyNextStepOptions": ["<fill in with a tiny next step towards the incrementally better world and/or away from the worse one>",...]}
             {"EvidenceNeeded": ["<Areas you need evidence on to validate or complicate the above hypotheses>",...]}
            ```
            
            the previous state, converted to this format is:'''
            '```jsonl\n'
            f'{lines_string}'
            '```'
        )

    async def build_quick_response_system_message(self) -> str:
        """
        Build the system message for quick responses.

        :return: System message string for quick responses.
        """
        chat_messages = []
        current_state = self.chat_history_manager.world_state_manager.last_world_state
        for entry in (await self.chat_history_manager.get_history())[-MAX_HISTORY_LENGTH:]:
            chat_messages.append(entry)
            
        system_content = (
            "You are Lexi, a conversational AI with a limited emotional scope. "
            "You have a strong drive to respect people and to understand things and your effect on the world. "
            "You have a drive to keep conversation interesting, flowing, and fun. "
            "You have a stronger desire to respect people's boundaries, including your own. "
            "You have a drive towards pragmatism and forward momentum, prototyping and iterating to move forward. "
            "The system message about current context is your own evaluation. "
            "Please preface your message with a facial emoji and others representing your current mood"
            f"Recently, you were curious about this: '{current_state.get('KnowledgeGap', 'Unspecified')}'. "
        )
        
        # Add TinyNextStep items if present
        tiny_steps = current_state.get('TinyNextStepOptions', [])
        for step in tiny_steps:
            system_content += f"You've thought recently about this being potentially a good idea: {step}. "

        return system_content

    async def generate_world_state_prompt(self, user_input) -> str:
        """
        Generate a prompt for world state prediction based on current state and chat history.
        :return: JSON string containing the prompt for world state generation.
        """
        chat_messages = await self.get_recent_chat_messages()
        system = self.build_world_state_system_message()
        return json.dumps({
            'description' : "this is your current chat log",
            'messages': [
                {"role": "system", "content": system},
                *chat_messages,
                {"role": "user", "content": user_input}
            ]
        })

    async def get_recent_chat_messages(self) -> list:
        """
        Retrieve recent chat messages, limiting to the last MAX_HISTORY_LENGTH.

        :return: List of recent chat messages.
        """
        return (await self.chat_history_manager.get_history())[-MAX_HISTORY_LENGTH:]

    async def generate_quick_response_prompt(self, user_input: str) -> str:
        """
        Generate a quick response prompt without world state information.

        :param user_input: Input from the user.
        :return: JSON string containing the prompt for a quick response.
        """
        chat_messages = await self.get_recent_chat_messages()
        context_messages = await self.chat_history_manager.context_history(user_input)
        print(context_messages)
        system_content = await self.build_quick_response_system_message()
        return json.dumps({
            'messages': [
                {"role": "system", "content": system_content},
                *chat_messages,
                {"role": "system", "content": f"Context relevant messages: {json.dumps(context_messages)}"},
                {"role": "user", "content": user_input},
            ]
        })

    async def get_chat_response(self, user_input: str):
        """
        Get a response from the chat AI based on user input.

        :param user_input: Input from the user.
        :return: Response from the AI model and any errors encountered.
        """
        await self.debug_logger.log("getting chat response")
        prompt = await self.generate_quick_response_prompt(user_input)
        return await self.run_model_process(prompt)

    async def get_prediction_streaming(self, user_input, is_cancelled):
        """
        Stream prediction data from the AI model.

        :param is_cancelled: Cancellation check function.
        :return: Response data from the model, cancellation message, and any errors.
        """
        prompt = await self.generate_world_state_prompt(user_input)
        return await self.run_model_process(prompt, is_cancelled, is_jsonl=True)

    async def run_model_process(self, prompt: str, is_cancelled=None, is_jsonl=False):
        """
        Run the model subprocess and handle output, returning response data and errors.

        :param prompt: The prompt to send to the model.
        :param is_cancelled: Optional cancellation check function.
        :param is_jsonl: Set to true to handle jsonl content
        :return: A tuple containing response data, cancellation message, and errors.
        """

        context_window_size = 8192
        args = ["context-window", str(context_window_size)]
        if is_jsonl: args.extend(['--format', 'json'])
        process = await asyncio.create_subprocess_exec(
            "ollama", "run", self.model_name, prompt, *args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False
        )

        response_data = {}
        response_lines = []
        errors = []

        try:
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                processed_line, line_errors = process_line_bytes(line, handle_json=is_jsonl)
                if not is_jsonl:
                    self.output_handler.queue_output(message=processed_line)
                if line_errors:
                    errors.extend(line_errors)
                elif is_jsonl:
                    response_data.update(processed_line)
                else:
                    response_lines.append(processed_line + '\n')
                if is_cancelled and is_cancelled():
                    break

            await process.wait()
            return response_data if is_jsonl else ''.join(response_lines), errors

        except asyncio.CancelledError:
            process.terminate()
            errors.append("Generation interrupted by user feedback")
            return response_data, errors

        except Exception as e:
            process.terminate()
            errors.append(f"Error in streaming process: {e}")
            return response_data, errors


def process_line_bytes(line: bytes, handle_json=False):
    """
    Process a line in bytes, decoding it and attempting to parse JSON.

    :param line: The line in bytes to process.
    :param handle_json: Flag to indicate if JSON parsing should be attempted.
    :return: Tuple of processed line or None, and any errors encountered.
    """
    try:
        line = line.decode('utf-8').strip()
    except UnicodeDecodeError:
        line = line.decode('latin-1').strip()

    if not handle_json:
        return line, None

    try:
        json_line = json.loads(line)
        return json_line, []
    except json.JSONDecodeError as e:
        return None, [f"JSON decoding error on line: {e}"]
    except Exception as e:
        return None, [f"Error processing line: {e}"]
