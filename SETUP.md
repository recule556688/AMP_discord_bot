# AMP Discord Bot Setup Guide

This guide will help you set up and run the AMP Discord Bot for managing game server requests.

## Prerequisites

1. **Python 3.8+** installed on your system
2. **AMP (Application Management Panel)** instance running
3. **Discord Bot Token** from Discord Developer Portal
4. **Administrator access** to your Discord server

## Installation Steps

### 1. Clone/Download the Project

Download or clone this project to your local machine.

### 2. Install Dependencies

Open a terminal in the project directory and install the required packages:

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

1. Copy `.env.example` to `.env`:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your configuration:

   ```dotenv
   # Discord Bot Configuration
   DISCORD_TOKEN=your_discord_bot_token_here
   GUILD_ID=your_guild_id_here  # Optional: for faster slash command sync during development
   ADMIN_CHANNEL_ID=your_admin_channel_id_here
   GAME_REQUEST_CHANNEL_ID=your_game_request_channel_id_here

   # AMP Configuration
   AMP_HOST=your_amp_host_here
   AMP_PORT=8080
   AMP_USERNAME=your_amp_username_here
   AMP_PASSWORD=your_amp_password_here

   # Database Configuration
   DATABASE_PATH=./database/requests.db

   # Bot Settings
   REQUEST_TIMEOUT_HOURS=24
   MAX_PENDING_REQUESTS_PER_USER=3
   ```

### 4. Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section and create a bot
4. Copy the bot token to your `.env` file
5. Enable the following bot permissions:

   - Send Messages
   - Use Slash Commands
   - Embed Links
   - Read Message History
   - Manage Messages (optional, for cleanup)

6. Invite the bot to your server with these permissions

### 5. Get Channel IDs

1. Enable Developer Mode in Discord (User Settings > Advanced > Developer Mode)
2. Right-click on your admin channel and copy ID
3. Right-click on your game request channel and copy ID
4. Add these IDs to your `.env` file

### 6. Game Configuration

Edit `config/games.py` to add or modify available games:

```python
GAME_TEMPLATES = {
    "minecraft": {
        "description": "Minecraft Java Edition Server",
        "template": "Minecraft",
        "max_players": 20,
        "supports_mods": True,
        "default_role": "User"
    },
    # Add more games as needed
}
```

### 7. Run the Bot

Start the bot with:

```bash
python main.py
```

The bot will:

- Initialize the database
- Load all cogs (commands)
- Sync slash commands to Discord
- Connect to AMP
- Set status to online

## Available Commands

### User Commands (Slash Commands)

- `/request [game]` - Request a game server
- `/status` - Check your request status
- `/cancel <request_id>` - Cancel a pending request

### Admin Commands (Slash Commands)

- `/approve <request_id>` - Approve a request and provision server
- `/deny <request_id> <reason>` - Deny a request with reason
- `/pending` - List all pending requests
- `/request_info <request_id>` - Get detailed request information

### Legacy Commands (Prefix: !)

- `!setup_requests` - Set up the interactive request system
- `!pending_requests` - List pending requests
- `!my_requests` - Show your pending requests

## Troubleshooting

### Common Issues

1. **Import errors when starting**

   - Make sure all dependencies are installed: `pip install -r requirements.txt`

2. **"Discord token not found"**

   - Check your `.env` file exists and has the correct token

3. **"AMP configuration incomplete"**

   - Verify all AMP settings in `.env` are correct

4. **Slash commands not appearing**

   - Commands sync automatically on startup
   - If using GUILD_ID, commands appear instantly in that server
   - Global sync takes up to 1 hour to propagate

5. **Database errors**

   - Make sure the `database` directory exists
   - Check file permissions for the database file

6. **AMP connection failed**
   - Verify AMP is running and accessible
   - Check AMP host, port, username, and password
   - Ensure the AMP user has sufficient permissions

### Logs

Check the console output for detailed logs about:

- Database initialization
- Cog loading
- AMP connection status
- Command execution
- Errors and warnings

## File Structure

```txt
AMP_discord_bot/
├── main.py                 # Bot entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Environment configuration template
├── config/
│   ├── settings.py        # Settings management
│   └── games.py          # Game configurations
├── database/
│   └── db.py             # Database management
├── models/
│   └── __init__.py       # Data models
├── services/
│   └── amp_service.py    # AMP API integration
├── utils/
│   ├── helpers.py        # Discord helpers
│   └── logging.py        # Logging utilities
└── cogs/
    ├── game_requests.py  # User request commands
    └── admin.py          # Admin commands
```

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review the console logs for error messages
3. Verify your configuration in `.env`
4. Make sure AMP is accessible and running
5. Check Discord bot permissions

For additional help, create an issue with:

- Error messages from the console
- Your configuration (without sensitive tokens/passwords)
- Steps to reproduce the problem
