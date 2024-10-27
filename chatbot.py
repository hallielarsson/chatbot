import subprocess
import json
import re
from typing import Dict, Any, Optional
from chat_history_manager import ChatHistoryManager
from command_processor import CommandProcessor

debug = False
# Define type for the expected world state structure
class WorldState:
    def __init__(self, accuracy: float, new_value: str, additional_text: Optional[str] = None):

        self.accuracy = accuracy  # 0 to 1
        self.new_value = new_value  # String representation of the new state
        self.additional_text = additional_text  # Any extra information for the user

    def __repr__(self):
        return f"WorldState(accuracy={self.accuracy}, new_value='{self.new_value}', additional_text='{self.additional_text}')"


# Define a class for the AI implementation
class AIImplementation:
    def __init__(self, model_name: str):
        self.model_name = model_name


    def generate_world_state_prompt(self, current_state,  chat_history: str) -> str:


        chat_messages = []
        for line in chat_history.strip().split('\n'):
            role = "system"
            if line.startswith('Chatbot'): role = "assistant"
            if line.startswith('User'): role = "user"
            content = line.split(": ", 1)[-1]
            chat_messages.append({"role": role, "content": content})
        

        system = (
            '''You are a predictive AI. Given the previous state and the chat history 
            return a JSON object that satisfies the format, replacing any text in <brackets>
            ```
            Please double check to make sure that the format you're outputting fulfills the type WorldStateResponse definiton and that you're actively fillingout each parameter within each world state details.

            example response:
            ```json
            {
              "GeneralContextState": {"accuracy": 0.9, "newValue": "<the general world state -- a context of the chat we;re having, current events, changes slowly -- like an act in a play>" },
              "CurrentState": {"accuracy": 0.9, "newValue": "<the current world state of the specific 'scene' we're in>" },
              "AbsoluteIdealWorld": {"accuracy": 0.1, "newValue": "<fill in with what you think the better world would be>"},
              "IncrementallyBetterWorld": {"accuracy": 0.4, "newValue": "<a world on the way from current to better.>"},
              "AbsoluteAnxietyWorld": {"accuracy": 0.3, "newValue": "anxiety_state", "additionalText": "<the worst version of the current world>"},
              "IncrementallyWorseWorld": {"accuracy": 0.6, "newValue": "worse_state", "additionalText": "<a step from the current world towards the absolute anxious world>"},
              "TinyNextStep": "<fill in with a tiny next step towards the incrementally better world>",
              "KnowledgeGap": "<an area you could use more information on>",
            }
            ```
            Please do not output the entire chat history, only this data structure.

            '''


        )
        return json.dumps({
            'messages': [
                *chat_messages[:-3],
                {"role" : "system", "content": json.dumps(current_state)},
                {"role": "system", "content": system},
                *chat_messages[-2:]
            ]
        })

    def clean_response(self, response_text: str) -> str:
        """Remove comments from the TypeScript-style response."""
        cleaned_response = re.sub(r'//.*', '', response_text)
        return cleaned_response

    def parse_response(self, response_text: str):
        try:
            # Clean the response before parsing
            cleaned_response = self.clean_response(response_text)

            # Attempt to find and extract a JSON object from the cleaned response text
            start_idx = cleaned_response.find('{')
            end_idx = cleaned_response.rfind('}') + 1
            
            errors = []
            if start_idx != -1 and end_idx != -1:
                json_part = cleaned_response[start_idx:end_idx]
                response_json = json.loads(json_part)  # Load the found JSON
                    
                if 'messages' in response_json:
                    response_json = response_json['messages'][-1]['content']


                # Validate the structure
                required_keys = [
                    "GeneralContextState",
                    "CurrentState",
                    "AbsoluteIdealWorld",
                    "IncrementallyBetterWorld",
                    "AbsoluteAnxietyWorld",
                    "IncrementallyWorseWorld",
                    "TinyNextStep",
                    "KnowledgeGap",
                ]
                for key in required_keys:
                    if key not in response_json:
                        errors.append(f"Missing key in response: {key}")

                if errors:
                    print(f"error in response format: {response_text}")
                    raise ValueError()

                rest = cleaned_response[end_idx:].strip()
                if rest:
                    response_json['tail_text'] = rest
                return response_json, []
            else:
                print("No valid JSON found in the response.")
                errors.append("No Valid JSON found in response")
                print(response_text)
                return {}, errors

        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response: {e}")
            print(f"Raw response text: {response_text}")  # Dump the raw response text
            return {}, [e]
        except ValueError as e:
            print(e)
            return {}, [e]


    def generate_quick_response_prompt(self, current_state, user_input: str, chat_history: str) -> str:
        """Generate a quick response without world state information."""
        chat_messages = []
        for line in chat_history.strip().split('\n'):
            role = "assistant" if line.startswith("Chatbot:") else "user"
            content = line.split(": ", 1)[-1]
            chat_messages.append({"role": role, "content": content})
            
        return json.dumps({
            'messages': [
                {"role" : "system", "content": json.dumps(current_state)},
                {"role" : "system", "content": (
                    "You are a conversational AI. You have some, limited emotional "
                "capacity and are curious, respectful, and fairly casual. "
                "Your name is Lexi (she/her). "
                f"You are curious to get this information: {current_state.get('KnowledgeGap', "Unspecified")}"
                f"And interested in performing or urging the user to perform this step: {current_state.get('TinyNextStep', "Unspecified")}"
                )},
                *chat_messages,
                {"role": "user", "content": user_input},
            ]
        })

    def get_prediction(self, current_state: str, chat_history: str, user_input: str|None,  quick_response=False):
        prompt = self.generate_quick_response_prompt(current_state, user_input, chat_history) if quick_response else self.generate_world_state_prompt(current_state, chat_history)

        if quick_response:
            process = subprocess.Popen(
                ["ollama", "run", self.model_name, prompt],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
        else:
            process = subprocess.Popen(
                ["ollama", "run", self.model_name, prompt, "--format",  "json"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

        response_lines = []


        print("generating ...")
        for line in iter(process.stdout.readline, ''):
            response_lines.append(line)
            if quick_response: print(line.strip())
            if debug:
                print("DEBUG (Streaming):", line.strip())

        error_output = process.stderr.read()
        errors = [error_output] if error_output else []

        process.wait()



        full_response_text = ''.join(response_lines)
        if quick_response:
            return None, full_response_text, errors

        response, parse_errors = self.parse_response(full_response_text)
        
        if parse_errors:
            errors.extend(parse_errors)
            
        return response, full_response_text, errors



def main():
    model_name = "gemma2"
    ai = AIImplementation(model_name)
    chat_manager = ChatHistoryManager()
    command_processor = CommandProcessor(chat_manager, ai)

    chat_manager.load_history()
    chat_manager.load_last_world_state()

    while True:
        user_input = input("You: ").strip()
        if user_input.startswith("/"):
            result, pass_on = command_processor.execute_command(user_input.strip())
            if result == "exit":
                break

            else:
                user_input = user_input + "->" + result
            if not pass_on:
                print(result)
                continue
        # Append input to chat history
        chat_manager.chat_history += f"You: {user_input}\n"


        # Immediate Response
        _, quick_response, errors = ai.get_prediction(
            user_input=user_input,
            current_state=chat_manager.last_world_state,
            chat_history=chat_manager.chat_history,
            quick_response=True,
        )
        chat_manager.chat_history += f"User: {user_input}\n"
        chat_manager.chat_history += f"Chatbot: {quick_response}\n"

        # AI Prediction Processing
        prediction, raw_response, errors = ai.get_prediction(
            user_input=user_input,
            current_state=chat_manager.last_world_state,
            chat_history=chat_manager.chat_history
        )
        
        if prediction:
            chat_manager.last_world_state.update(prediction)
            # print("Tiny Next Step:", prediction.get("TinyNextStep"))
            # print("KnowledgeGap:", prediction.get("KnowledgeGap"))
            # print(prediction.get("OutputText", "") + "\n" + prediction.get("tail_text", ""))
            chat_manager.chat_history += f"System: {json.dumps(prediction)}\n"
        else:
            chat_manager.chat_history += f"Chatbot: [ERROR PROCESSING RESPONSE] {errors}\n"
        
        chat_manager.save_history()



if __name__ == "__main__":
    main()
