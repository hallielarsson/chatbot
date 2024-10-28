import json
import unittest
from unittest.mock import MagicMock, patch, Mock  # Import Mock from unittest.mock
import asyncio

from ai_implementation import AIImplementation  # Adjust the import according to your project structure

class AsyncMock:
    def __init__(self, responses):
        self.responses = responses
        self.read_index = 0

    async def readline(self):
        if self.read_index < len(self.responses):
            response = self.responses[self.read_index]
            self.read_index += 1
            await asyncio.sleep(0)  # Yield control to the event loop
            return response
        return b''  # Return empty byte string to simulate EOF

    def close(self):
        pass  # Add any cleanup if needed

class TestAIImplementation(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.mock_chat_history_manager = MagicMock()
        self.ai = AIImplementation("test_model", self.mock_chat_history_manager, debug=True)

    def test_generate_world_state_prompt(self):
        # Setup mock return values
        self.mock_chat_history_manager.get_history.return_value = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        current_state = {
            "KnowledgeGap": "AI capabilities"
        }
        
        expected_output = json.dumps({
            'messages': [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
                {"role": "system", "content": "You are a predictive AI. Given the previous state and the chat history \n            return a JSONL object that satisfies the format, replacing any text in <brackets>\n            Please double check to make sure that the format you're outputting matches the def below and that you're actively fillingout each parameter within each world state details.\n            Please do not output the entire chat history, only this data structure.\n\n            example response:\n            ```jsonl\n             {\"GeneralContextState\": {\"newValue\": \"<the general world state -- a context of the chat we;re having, current events, changes slowly -- like an act in a play>\"}}\n             {\"CurrentState\": { \"newValue\": \"<the current world state of the specific 'scene' we're in>\" }}\n             {\"AbsoluteIdealWorld\": { \"newValue\": \"<fill in with what you think the better world would be>\"}}\n             {\"IncrementallyBetterWorld\": { \"newValue\": \"<a world on the way from current to better.>\"}}\n             {\"AbsoluteAnxietyWorld\": { \"newValue\": \"<the worst version of the current world>\"}}\n             {\"IncrementallyWorseWorld\": { \"newValue\": \"<a step from the current world towards the absolute anxious world>\"}}\n             {\"TinyNextStepOptions\": [\"<fill in with a tiny next step towards the incrementally better world> and/or away from the worse one\",\"<fill in with a divergent tinly towards the incrementally better world and/or away from the worse one>\"]}\n             {\"KnowledgeGap\": \"<an area you want use more information on>\"}\n            ```\n            "}
            ]
        })

        actual_output = self.ai.generate_world_state_prompt(current_state)
        # For debugging: print the actual output to compare
        print("Actual Output:", actual_output)  
        self.assertEqual(actual_output, expected_output)

    def test_clean_response(self):
        response_text = "This is a response // This is a comment"
        expected_cleaned_response = "This is a response "
        actual_cleaned_response = self.ai.clean_response(response_text)
        self.assertEqual(actual_cleaned_response, expected_cleaned_response)

    async def test_get_chat_response(self):
        self.mock_chat_history_manager.last_world_state = {
            "KnowledgeGap": "AI capabilities"
        }
        prompt = self.ai.generate_quick_response_prompt("How are you?")

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = MagicMock()
            # Create an instance of AsyncMock with your responses
            mock_process.stdout.readline = AsyncMock([b"Response line 1\n", b"Response line 2\n"])
            mock_subprocess.return_value = mock_process

            response, errors = await self.ai.get_chat_response("How are you?")

            self.assertIn("Response line", response)
            self.assertEqual(errors, [])

    async def test_get_prediction_streaming(self):
        self.mock_chat_history_manager.last_world_state = {
            "KnowledgeGap": "AI capabilities"
        }
        is_cancelled = Mock(return_value=False)
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = MagicMock()
            mock_process.stdout.readline = Mock(side_effect=["{\"GeneralContextState\": {\"newValue\": \"test\"}}\n", ""])
            mock_subprocess.return_value = mock_process

            response_obj, message, errors = await self.ai.get_prediction_streaming("current_state", "user_input", is_cancelled)

            self.assertIn("GeneralContextState", response_obj)
            self.assertEqual(errors, [])

if __name__ == "__main__":
    unittest.main()
