import subprocess
import json
import re
from typing import Dict, Any, Optional
debug = True
# Define type for the expected world state structure
class WorldState:
    def __init__(self, accuracy: float, new_value: str, additional_text: Optional[str] = None):
        self.accuracy = accuracy  # 0 to 1
        self.new_value = new_value  # String representation of the new state
        self.additional_text = additional_text  # Any extra information for the user

# Define a class for the AI implementation
class AIImplementation:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def generate_prompt(self, current_state, user_input:str, chat_history: str) -> str:

        chat_messages = []
        for line in chat_history.strip().split('\n'):
            role = "assistant" if line.startswith("Chatbot:") else "user"
            content = line.split(": ", 1)[-1]
            chat_messages.append({"role": role, "content": content})
        

        system = (
            '''You are a predictive AI. Given the previous state (above) and the chat history (below) 
            return a JSON object that satisfies the format, replacing any text in <brackets>
            ```
            Please double check to make sure that the format you're outputting fulfills the type WorldStateResponse definiton and that you're actively fillingout each parameter within each world state details.

            example response:
            ```json
            {
              "CurrentState": {"accuracy": 0.8, "newValue": "<the current world state>" },
              "AbsoluteIdealWorld": {"accuracy": 0.9, "newValue": "<fill in with what you think the better world would be>"},
              "IncrementallyBetterWorld": {"accuracy": 0.7, "newValue": "<a world on the way from current to better.>"},
              "AbsoluteAnxietyWorld": {"accuracy": 0.5, "newValue": "anxiety_state", "additionalText": "<the worst version of the current world>"},
              "IncrementallyWorseWorld": {"accuracy": 0.6, "newValue": "worse_state", "additionalText": "<a step from the current world towards the absolute anxious world>"},
              "TinyNextStep": "<fill in with a tiny next step towards the incrementally better world>",
              "KnowledgeGap": "<an area you need more info on to confirm the accuracy of the world state>",
            }
            ```
            Please do not output the entire chat history, only this data structure.

            '''


        )
        return json.dumps({
            'messages': [
                *chat_messages,
                {"role": "system", "content":  current_state},                
                {"role": "system", "content": system},
                {"role": "user", "content": user_input}

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
                        print(response_json)
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

    def get_prediction(self, user_input: str, current_state: str, chat_history: str):
        prompt = self.generate_prompt(current_state, user_input, chat_history)
        
        # Use subprocess.Popen to allow streaming of output line-by-line
        process = subprocess.Popen(
            ["ollama", "run", self.model_name, prompt, "--format", "json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        response_lines = []
        errors = []
        
        # Process the output in real-time as each line arrives
        if process.stdout:
            for line in iter(process.stdout.readline, ''):
                response_lines.append(line)
                
                # Stream to debug mode in real-time
                if debug:
                    print("DEBUG (Streaming):", line.strip())

        
        # Collect stderr output if any
        error_output = process.stderr.read()
        if error_output:
            errors.append(error_output)
        
        # Wait for the process to complete
        process.wait()

        # Combine lines into the final response text
        full_response_text = ''.join(response_lines)
        
        # Parse the response
        response, parse_errors = self.parse_response(full_response_text)
        
        # Aggregate parsing errors and subprocess errors
        if parse_errors:
            errors.extend(parse_errors)
        
        return response, full_response_text, errors

        

# Main chat loop
def main():
    model_name = "mistral" # Ollama model name
    ai = AIImplementation(model_name)
    
    chat_history = ""
    last_world_state = {}
    global debug

    def save_history(file_name: str):
        with open(file_name, 'w') as file:
            file.write(chat_history)
        print(f"Chat history saved to {file_name}.")

 
    def save_last_world_state(file_name: str):
        with open(file_name, 'w') as file:
            json.dump(last_world_state, file)
        print(f"Last world state saved to {file_name}.")

    def load_history(file_name: str):
        """Load chat history from a file, setting chat_history to an empty string if the file is not found."""
        nonlocal chat_history
        try:
            with open(file_name, 'r') as file:
                chat_history = file.read()
            print(f"Chat history loaded from {file_name}.")
        except FileNotFoundError:
            chat_history = ""
            print(f"{file_name} not found. Starting with an empty chat history.")

    def load_last_world_state(file_name: str):
        """Load last world state from a file, setting last_world_state to an empty dictionary if the file is not found."""
        nonlocal last_world_state
        try:
            with open(file_name, 'r') as file:
                last_world_state = json.load(file)
            print(f"Last world state loaded from {file_name}.")
        except FileNotFoundError:
            last_world_state = {}
            print(f"{file_name} not found. Starting with an empty world state.")
        except json.JSONDecodeError:
            last_world_state = {}
            print(f"Error reading {file_name}. The file is not valid JSON. Starting with an empty world state.")
   
    def run_console_command(command: str) -> str:
        """Run a console command and return its output."""
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                print(f"Error running command: {result.stderr.strip()}")
                return ""
        except Exception as e:
            print(f"Failed to run command: {e}")
            return ""

    load_history('chat_history.txt')

    previous_response = ''
    while True:
        user_input = input("You: ") 

        output_file = None
    
        if '>' in user_input:
            # extract the file path from the user input
            output_file = user_input.split('>')[1].strip()

        if user_input.lower() == "/exit":
            break
        elif user_input.lower() == "/debug":
            debug = not debug
            continue
        elif user_input.lower() == "/save":
            save_history("chat_history.txt")
            save_last_world_state("last_world_state.json")
            continue
        elif user_input.lower() == "/load":
            load_history("chat_history.txt")
            load_last_world_state("last_world_state.json")
            continue
        elif user_input.lower() == "/states":
            # Display states with evaluations (example placeholder)
            print(json.dumps(last_world_state))
            continue
        elif user_input.lower().startswith("/console "):
            command = user_input[9:]  # Remove "/console " from the input
            feedback = command.endswith("|")
            if feedback:
                command = command[:-1].strip()  # Remove the trailing pipe
            output = run_console_command(command)
            print(output)
            if feedback:
                next_input = output
                print(f"Next input from command output: {next_input}")
                user_input = next_input  # Use the output as the next input
            else:
                continue
        elif user_input.lower()[0] == "/":
            print("unrecognized command")
            continue
        
        # Append the user input to chat history
        chat_history += f"You: {user_input}\n"
        
        # Call AI to get predictions
        prediction, raw_response, errors = ai.get_prediction(
            user_input=user_input,
            current_state=last_world_state,
            chat_history=chat_history)

        # Process the prediction result
        if prediction:
            for state, details in prediction.items():
                if isinstance(details, dict):
                    last_world_state[state] = details  # Update the last world state
                    if debug: print(f"{state}: Accuracy: {details.get('accuracy', 'N/A')}, New Value: {details.get('newValue', 'N/A')}, Additional Info: {details.get('additionalText', '')}")
                else:
                    if debug: print(f"{state}: {details} (Type: {type(details)})")
            save_last_world_state('last_world_state.json')
            save_history('chat_history.txt')


            # Output Tiny Next Step and Clarifying Question
            print("Tiny Next Step:", prediction.get("TinyNextStep"))
            print("Clarifying Question:", prediction.get("ClarifyingQuestion"))
            print(prediction.get("OutputText") + '\n' + prediction.get("tail_text", ""))
            
            output_file_params = prediction.get('OutputFile')
            if output_file_params:
                if input(f"Chatbot provided a file. Do you want to save it to {output_file_params['path']}?") == 'y':
                    with open(output_file_params['path'], 'w') as f:
                        f.write(output_file_params['content'])

            chat_history += f"Chatbot: {raw_response}\n"
        else:
            chat_history += f"Chatbot: [ERROR PROCESSING RESPONSE] {errors}\n - {raw_response}\n"
        save_history('chat_history.txt')

        if output_file:
            # save the response to the file
            with open(output_file, 'w') as f:
                f.write(raw_response)


if __name__ == "__main__":
    main()
