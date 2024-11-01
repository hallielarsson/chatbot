from terminal_output_handler import TerminalOutputHandler  # Adjust the import according to your structure
import pytest
from unittest.mock import patch


@pytest.mark.asyncio
async def test_send_output_system_message():
    """Test sending a system message."""
    output_handler = TerminalOutputHandler()
    message = "This is a system message."
    expected_output = f"\033[94m{message}\033[0m"  # Expected ANSI formatted output

    with patch('builtins.print') as mock_print:
        await output_handler.send_output(message, message_type="system")
        mock_print.assert_called_once_with(expected_output)


@pytest.mark.asyncio
async def test_send_output_chatbot_message():
    """Test sending a chatbot message."""
    output_handler = TerminalOutputHandler()
    message = "This is a response from the chatbot."
    expected_output = f"\033[92m{message}\033[0m"  # Expected ANSI formatted output

    with patch('builtins.print') as mock_print:
        await output_handler.send_output(message, message_type="chatbot")
        mock_print.assert_called_once_with(expected_output)


@pytest.mark.asyncio
async def test_send_output_error_message():
    """Test sending an error message."""
    output_handler = TerminalOutputHandler()
    message = "This is an error message."
    expected_output = f"\033[91m{message}\033[0m"  # Expected ANSI formatted output

    with patch('builtins.print') as mock_print:
        await output_handler.send_output(message, message_type="error")
        mock_print.assert_called_once_with(expected_output)


@pytest.mark.asyncio
async def test_send_output_default_message_type():
    """Test sending a message with the default message type."""
    output_handler = TerminalOutputHandler()
    message = "This is a default message."
    expected_output = f"\033[0m{message}\033[0m"  # Expected ANSI formatted output for default

    with patch('builtins.print') as mock_print:
        await output_handler.send_output(message)
        mock_print.assert_called_once_with(expected_output)

# Run these tests using pytest
if __name__ == "__main__":
    pytest.main()
