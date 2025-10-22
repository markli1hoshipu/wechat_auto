# WeChat Auto-Responder with GPT

Intelligent WeChat auto-responder powered by OpenAI GPT that learns your conversational style and responds naturally.

## Features

- **GPT-Powered Auto-Reply**: Uses OpenAI GPT to generate natural responses that mimic your tone and style
- **Context-Aware**: Analyzes chat history to understand your conversation patterns
- **Message Logging**: Saves all received and sent messages with timestamps
- **Multi-User Support**: Monitor and auto-reply to multiple contacts
- **Chat History**: Automatically saves chat history on startup for GPT context

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- `wxauto` - WeChat automation library
- `openai` - OpenAI API client
- `pyyaml` - YAML configuration parser

### 2. WeChat Desktop

Make sure WeChat desktop client is installed and logged in.

### 3. Configure `config.yaml`

Create/edit `config.yaml`:

```yaml
openai:
  api_key: "your-openai-api-key-here"  # Replace with your OpenAI API key
  model: "gpt-4o-mini"                 # GPT model to use
  temperature: 0.8                      # Creativity (0.0-1.0)
  max_tokens: 150                       # Max response length

users:
  - nickname: "Friend Name"             # Contact nickname in WeChat
    enabled: true

log_file: "message_logs.txt"
history_log_file: "chat_history.txt"

# Number of historical messages to send to GPT for context
history_context_length: 20
```

### 4. Get OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Create an account or sign in
3. Navigate to API Keys section
4. Create a new API key
5. Copy and paste it into `config.yaml`

## Usage

Run the script:
```bash
python main.py
```

The script will:
1. Connect to WeChat
2. Load chat history for all configured users
3. Analyze your message history to learn your tone
4. Monitor for new messages
5. Auto-reply using GPT with responses that match your style
6. Log all messages to `message_logs.txt`

Press `Ctrl+C` to stop.

## How It Works

### GPT Context Building

The system sends GPT:
1. **System Prompt**: Instructions to mimic your conversational style
2. **Chat History**: Recent conversation history (configurable length)
3. **Current Message**: The new message to respond to

GPT analyzes:
- Your tone (formal/casual, friendly/professional)
- Common phrases and expressions you use
- Length of typical responses
- Emoji usage patterns
- Language style (Chinese/English mix, slang, etc.)

### Message Flow

```
1. Friend sends message
   ↓
2. System logs message & updates chat history
   ↓
3. System sends context to GPT
   ↓
4. GPT generates response matching your style
   ↓
5. System sends reply and logs it
```

## Files

- `main.py` - Main automation script with GPT integration
- `message_supervisor.py` - Message logging module
- `config.yaml` - YAML configuration file
- `message_logs.txt` - All messages log (created automatically)
- `requirements.txt` - Python dependencies

## Configuration Options

### OpenAI Settings

- `api_key`: Your OpenAI API key (required)
- `model`: GPT model (`gpt-4o-mini`, `gpt-4o`, `gpt-3.5-turbo`, etc.)
- `temperature`: Response creativity (0.0 = focused, 1.0 = creative)
- `max_tokens`: Maximum response length

### General Settings

- `users`: List of contacts to monitor and auto-reply to
- `history_context_length`: Number of recent messages to send to GPT
- `log_file`: Path to message log file

## Tips

1. **Longer history = Better context**: Increase `history_context_length` for better tone matching
2. **Temperature tuning**:
   - Lower (0.5-0.7) for consistent, predictable responses
   - Higher (0.8-1.0) for more creative, varied responses
3. **Model selection**:
   - `gpt-4o-mini`: Fast and cost-effective
   - `gpt-4o`: Higher quality, more expensive
4. **Monitor API costs**: Check your OpenAI usage dashboard regularly

## Privacy & Security

- API key is stored locally in `config.yaml` - keep this file secure
- All chat data is sent to OpenAI's API for processing
- Message logs are stored locally in plain text
- Never commit `config.yaml` with your API key to version control

## Troubleshooting

**Chat name not matching?**
- Check the debug output for the exact chat name
- Make sure the nickname in `config.yaml` matches exactly

**GPT not responding?**
- Verify your OpenAI API key is correct
- Check your API usage limits
- Review error messages in console

**Messages not being detected?**
- Ensure WeChat desktop is open and logged in
- Check that the contact name is spelled correctly
