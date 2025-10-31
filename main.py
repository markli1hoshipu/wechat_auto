import yaml
import time
import re
import threading
from collections import defaultdict
from datetime import datetime
from wxauto import WeChat
from wxauto.msgs import FriendMessage
from message_supervisor import MessageSupervisor
from openai import OpenAI


class WeChatAutoResponder:
    """WeChat auto-responder with GPT-powered message logging"""

    def __init__(self, config_file: str = "config.yaml"):
        self.config = self._load_config(config_file)
        self.wx = WeChat()
        self.supervisor = MessageSupervisor(self.config.get('log_file', 'message_logs.txt'))
        self.user_configs = {user['nickname']: user for user in self.config.get('users', [])}

        # Initialize OpenAI client
        openai_config = self.config.get('openai', {})
        self.openai_client = OpenAI(api_key=openai_config.get('api_key'))
        self.gpt_model = openai_config.get('model', 'gpt-4o-mini')
        self.gpt_temperature = openai_config.get('temperature', 0.8)
        self.gpt_max_tokens = openai_config.get('max_tokens', 150)
        self.history_length = self.config.get('history_context_length', 20)

        # Store recent chat history for each user
        self.chat_histories = {}
        
        # Message queue and timers for batching responses
        self.message_queues = defaultdict(list)
        self.response_timers = {}
        self.timer_locks = defaultdict(threading.Lock)

    def _load_config(self, config_file: str) -> dict:
        """Load configuration from YAML file"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            raise

    def _build_chat_context(self, chat_name: str, current_messages: list) -> list:
        """Build chat context for GPT from recent history"""
        # Get user-specific prompt or use default
        user_config = self.user_configs.get(chat_name, {})
        user_prompt = user_config.get('prompt', '')
        
        # Build the system prompt with style instructions
        system_prompt = f"""**STYLE INSTRUCTIONS**
You are responding in a WeChat conversation. Follow these style guidelines:

1. Mimic natural WeChat conversation style
2. Keep responses concise and natural
3. Match the tone from the conversation history
4. DO NOT mention that you're an AI

{f'**USER-SPECIFIC STYLE**{user_prompt}' if user_prompt else ''}"""
            
        messages = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]

        # Build conversation history section
        history_text = ""
        if chat_name in self.chat_histories:
            history = self.chat_histories[chat_name][-self.history_length:]
            history_lines = []
            for entry in history:
                sender = "Me" if entry['is_user'] else "Friend"
                history_lines.append(f"{sender}: {entry['content']}")
            if history_lines:
                history_text = "\n**PREVIOUS CONVERSATION HISTORY**\n" + "\n".join(history_lines)

        # Build current messages section
        messages_to_respond = ""
        if len(current_messages) == 1:
            messages_to_respond = current_messages[0]
        else:
            messages_to_respond = "\n".join([f"[{i+1}] {msg}" for i, msg in enumerate(current_messages)])

        # Combine everything into a clear user message
        user_content = f"""**MESSAGES TO RESPOND TO**
{messages_to_respond}
{history_text}

Please generate an appropriate response to the above message(s), considering the conversation history and following the style instructions."""

        messages.append({
            "role": "user", 
            "content": user_content
        })

        # Log what we're sending to AI for debugging
        print(f"\n[AI Request Structure]")
        print(f"System Prompt: {system_prompt[:100]}...")
        print(f"Messages to respond: {len(current_messages)} message(s)")
        print(f"History context: {len(self.chat_histories.get(chat_name, []))} previous messages")
        
        return messages

    def get_gpt_reply(self, chat_name: str, batched_messages: list) -> str:
        """Get GPT-generated reply based on chat history and user's tone"""
        try:
            # Build context from chat history
            messages = self._build_chat_context(chat_name, batched_messages)

            # Call OpenAI API
            response = self.openai_client.chat.completions.create(
                model=self.gpt_model,
                messages=messages,
                temperature=self.gpt_temperature,
                max_tokens=self.gpt_max_tokens
            )

            reply = response.choices[0].message.content.strip()
            return reply

        except Exception as e:
            return "请稍等"  # Fallback response

    def _update_chat_history(self, chat_name: str, content: str, is_user: bool):
        """Update chat history for a user"""
        if chat_name not in self.chat_histories:
            self.chat_histories[chat_name] = []

        self.chat_histories[chat_name].append({
            'content': content,
            'is_user': is_user
        })

        # Keep only recent messages
        if len(self.chat_histories[chat_name]) > self.history_length * 2:
            self.chat_histories[chat_name] = self.chat_histories[chat_name][-self.history_length * 2:]

    def on_message(self, msg, chat):
        """
        Callback function for handling incoming messages

        Args:
            msg: Message object from wxauto
            chat: Chat object from wxauto
        """
        # Get chat name from Chat object - try multiple attributes
        chat_name = None
        for attr in ['nickname', 'name', 'who']:
            chat_name = getattr(chat, attr, None)
            if chat_name:
                break

        # If no attribute found, parse from string representation
        if not chat_name:
            chat_str = str(chat)
            # Extract name from: <wxauto - Chat object("stCRg 小助手")>
            import re
            match = re.search(r'Chat object\("([^"]+)"\)', chat_str)
            if match:
                chat_name = match.group(1)
            else:
                chat_name = chat_str

        # Debug: Print message type
        # print(f"\n[DEBUG] Message received:")
        # print(f"  - Type: {msg.__class__.__name__}")
        # print(f"  - Chat object: '{chat}'")
        # print(f"  - Chat attributes: {dir(chat)}")
        # print(f"  - Chat name: '{chat_name}'")
        # print(f"  - msg.type: {msg.type}")
        # print(f"  - msg.attr: {msg.attr}")
        # print(f"  - Content: {msg.content}")

        # Log the received message
        self.supervisor.log_message(
            msg_type=msg.type,
            msg_attr=msg.attr,
            chat=chat_name,
            content=msg.content,
            is_reply=False
        )

        # Handle images and videos
        if msg.type in ('image', 'video'):
            try:
                download_path = msg.download()
            except Exception as e:
                pass

        # Update chat history with received message
        self._update_chat_history(chat_name, msg.content, is_user=False)

        # Auto-reply to friend messages with batching
        if isinstance(msg, FriendMessage):
            # Check if this user has auto-reply configured
            if chat_name in self.user_configs:
                # Add message to queue
                with self.timer_locks[chat_name]:
                    self.message_queues[chat_name].append((msg, msg.content))
                    
                    # Cancel existing timer if any
                    if chat_name in self.response_timers:
                        self.response_timers[chat_name].cancel()
                    
                    # Get wait time from config (default 5 seconds)
                    wait_time = self.user_configs[chat_name].get('wait_time', 5)
                    
                    # Create new timer
                    timer = threading.Timer(wait_time, self._send_batched_reply, args=[chat_name])
                    self.response_timers[chat_name] = timer
                    timer.start()

    def _send_batched_reply(self, chat_name: str):
        """Send a batched reply after the timer expires"""
        with self.timer_locks[chat_name]:
            if not self.message_queues[chat_name]:
                return
            
            # Get all queued messages
            queued_messages = self.message_queues[chat_name].copy()
            self.message_queues[chat_name].clear()
            
            # Remove timer reference
            if chat_name in self.response_timers:
                del self.response_timers[chat_name]
        
        try:
            # Extract just the message contents
            message_contents = [msg[1] for msg in queued_messages]
            
            # Get GPT reply for all messages
            reply = self.get_gpt_reply(chat_name, message_contents)
            
            # Random delay to seem natural
            import random
            delay = random.uniform(1, 3)
            time.sleep(delay)
            
            # Send reply using the last message's quote function
            last_msg = queued_messages[-1][0]
            last_msg.quote(reply)
            
            # Update chat history with sent message
            self._update_chat_history(chat_name, reply, is_user=True)
            
            # Log the auto-reply
            self.supervisor.log_message(
                msg_type='text',
                msg_attr='self',
                chat=chat_name,
                content=reply,
                is_reply=True
            )
        except Exception as e:
            pass
    
    def save_initial_chat_history(self):
        """Save chat history for all configured users on startup and load into memory"""
        print("Saving initial chat history...")

        for nickname in self.user_configs.keys():
            try:
                # Switch to user's chat
                self.wx.ChatWith(nickname)
                time.sleep(0.5)

                # Get all messages
                messages = self.wx.GetAllMessage()

                if messages:
                    # Save chat history to file
                    self.supervisor.save_chat_history(nickname, messages)

                    # Load recent messages into memory for GPT context
                    # Take only the most recent messages based on history_length
                    recent_messages = messages[-self.history_length:] if len(messages) > self.history_length else messages

                    for msg in recent_messages:
                        # Determine if message is from user or friend
                        # msg.attr can be 'self' (user's message) or 'friend' (friend's message)
                        is_user = (msg.attr == 'self')

                        # Add to chat history
                        self._update_chat_history(nickname, msg.content, is_user=is_user)

                    print(f"Loaded {len(recent_messages)} messages into context for {nickname}")

            except Exception as e:
                print(f"Error saving chat history for {nickname}: {e}")

        print("Chat history saved and loaded into context.")
        print("-" * 60)

    def start(self):
        """Start the auto-responder"""
        print("="*60)
        print("WeChat Auto-Responder with GPT Starting...")
        print("="*60)

        users = self.config.get('users', [])
        if not users:
            print("No users configured in config.yaml!")
            return

        print(f"OpenAI Model: {self.gpt_model}")
        print(f"Temperature: {self.gpt_temperature}")
        print(f"Max Tokens: {self.gpt_max_tokens}")
        print(f"History Context Length: {self.history_length}")
        print(f"\nConfigured users: {len(users)}")
        for user in users:
            nickname = user['nickname']
            enabled = user.get('enabled', True)
            wait_time = user.get('wait_time', 5)
            has_prompt = 'Yes' if user.get('prompt') else 'No'
            status = "Enabled" if enabled else "Disabled"
            print(f"  - {nickname}: {status} (Wait: {wait_time}s, Custom Prompt: {has_prompt})")

        print("-" * 60)

        # Save initial chat history
        self.save_initial_chat_history()

        # Add listeners for all configured users
        print("Adding message listeners...")
        for nickname in self.user_configs.keys():
            try:
                self.wx.AddListenChat(nickname=nickname, callback=self.on_message)
                print(f"Listening to: {nickname}")
            except Exception as e:
                print(f"Error adding listener for {nickname}: {e}")

        print("-" * 60)
        print("Auto-responder is running. Press Ctrl+C to stop.")
        print("="*60)

        # Keep the program running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n" + "="*60)
            print("Stopping auto-responder...")
            
            # Cancel all pending timers
            for chat_name in list(self.response_timers.keys()):
                self.response_timers[chat_name].cancel()
            self.response_timers.clear()

            # Remove all listeners
            for nickname in self.user_configs.keys():
                try:
                    self.wx.RemoveListenChat(nickname=nickname)
                    print(f"Removed listener for: {nickname}")
                except Exception as e:
                    print(f"Error removing listener for {nickname}: {e}")

            print("Auto-responder stopped.")
            print("="*60)


def main():
    """Main entry point"""
    try:
        responder = WeChatAutoResponder()
        responder.start()
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
