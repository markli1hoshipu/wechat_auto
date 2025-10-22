from datetime import datetime


class MessageSupervisor:
    """Supervisor class to log and save all received messages"""

    def __init__(self, log_file: str = "message_logs.txt"):
        self.log_file = log_file

    def log_message(self, msg_type: str, msg_attr: str, chat: str, content: str, is_reply: bool = False):
        """
        Log a message with timestamp

        Args:
            msg_type: Type of message (text, image, video, etc.)
            msg_attr: Message attribute (friend, group, self, etc.)
            chat: Name of the chat/contact
            content: Message content
            is_reply: Whether this is an auto-reply
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prefix = "[AUTO-REPLY]" if is_reply else ""
        text = f"{prefix}[{timestamp}][{msg_type} {msg_attr}]{chat} - {content}"

        print(text)

        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(text + '\n')
        except Exception as e:
            print(f"Error saving message: {e}")

    def save_chat_history(self, chat: str, messages):
        """
        Save initial chat history when program starts

        Args:
            chat: Name of the chat/contact
            messages: List of messages to save
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = f"\n{'='*60}\n[CHAT HISTORY SNAPSHOT] {chat} - {timestamp}\n{'='*60}\n"

        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(header)
                for msg in messages:
                    text = f"[{msg.type} {msg.attr}]{chat} - {msg.content}"
                    f.write(text + '\n')
                f.write(f"{'='*60}\n")

            print(f"Saved {len(messages)} messages from chat history with {chat}")
        except Exception as e:
            print(f"Error saving chat history: {e}")
