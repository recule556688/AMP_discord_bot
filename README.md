# AMP Discord Bot

A Discord bot for managing game server requests through AMP (Application Management Panel). Users can request game servers via Discord, admins approve/deny requests, and the bot automatically provisions AMP accounts and server instances.

## Features

- **Slash Command Support** - Modern Discord slash commands for all interactions
- **User Request System** - Easy game server requests with autocomplete
- **Admin Management** - Approve/deny requests with detailed tracking
- **AMP Integration** - Automatic user and server provisioning
- **Database Tracking** - SQLite database for request management
- **Modular Design** - Clean, maintainable codebase with best practices

## Quick Start

1. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**

   ```bash
   cp .env.example .env
   # Edit .env with your Discord token and AMP credentials
   ```

3. **Run the Bot**

   ```bash
   python main.py
   ```

## Commands

### User Commands

- `/request [game]` - Request a game server (with autocomplete)
- `/status` - Check your request status
- `/cancel <request_id>` - Cancel a pending request

### Admin Commands

- `/approve <request_id>` - Approve and provision server
- `/deny <request_id> <reason>` - Deny request with reason
- `/pending` - List all pending requests
- `/request_info <request_id>` - Get detailed request info

## Workflow

1. **User requests** a game server using `/request minecraft`
2. **Admin receives** notification in admin channel
3. **Admin approves** using `/approve <id>` or denies with `/deny <id> <reason>`
4. **Bot provisions** AMP user account and server instance
5. **User receives** credentials and server access information

## Architecture

```txt
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Discord User  │───▶│  Discord Bot    │───▶│   AMP Panel     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │ SQLite Database │
                       └─────────────────┘
```

## Project Structure

```txt
AMP_discord_bot/
├── main.py                 # Bot entry point
├── requirements.txt        # Dependencies
├── .env.example           # Configuration template
├── SETUP.md              # Detailed setup guide
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
│   ├── helpers.py        # Discord utilities
│   └── logging.py        # Logging system
└── cogs/
    ├── game_requests.py  # User commands
    └── admin.py          # Admin commands
```

## Technology Stack

- **Discord.py 2.3.2** - Discord API wrapper with slash command support
- **cc-ampapi 1.3.0** - Official AMP API Python library
- **aiosqlite** - Async SQLite database operations
- **loguru** - Advanced logging with better formatting
- **python-dotenv** - Environment configuration management

## Key Features Implemented

### ✅ Slash Commands

- Modern Discord slash commands for all user interactions
- Autocomplete for game selection
- Proper permission handling and error messages

### ✅ AMP Integration

- Updated to use official `cc-ampapi` library
- Automatic user account creation
- Server instance provisioning
- Credential management and delivery

### ✅ Modular Architecture

- Clean separation of concerns
- Cog-based command organization
- Reusable utility functions
- Proper error handling throughout

### ✅ Database Management

- Async SQLite operations
- Request tracking and status management
- User request history
- Admin action logging

### ✅ Configuration Management

- Environment-based configuration
- Game template system
- Flexible settings management
- No hardcoded values

## Requirements

- Python 3.8+
- Discord Bot with appropriate permissions
- Running AMP instance with API access
- SQLite support (built into Python)

## Setup

See [SETUP.md](SETUP.md) for detailed installation and configuration instructions.

## Contributing

This project follows Python best practices:

- Type hints throughout
- Async/await for all I/O operations
- Modular design with clear separation
- Comprehensive error handling
- Detailed logging for debugging

## License

This project is provided as-is for educational and personal use.

## Features

🎮 **Game Server Requests**

- Interactive embed with buttons for different games
- User-friendly request system
- Automatic request tracking

👑 **Admin Management**

- Admin approval/rejection system
- Automatic AMP user creation
- Server instance provisioning
- Request status tracking

🔧 **AMP Integration**

- Automatic user account creation
- Role assignment based on game templates
- Server instance creation
- Credential management

📊 **Database Tracking**

- SQLite database for request management
- Request history and status tracking
- Automatic cleanup of expired requests

## Prerequisites

- Python 3.8+
- Discord Bot Token
- AMP (Application Management Panel) instance
- Required Python packages (see requirements.txt)

## Installation

1. **Clone or download the project files**

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**

   - Copy `.env.example` to `.env`
   - Fill in your configuration:

   ```env
   # Discord Bot Configuration
   DISCORD_TOKEN=your_discord_bot_token_here
   GUILD_ID=your_guild_id_here
   ADMIN_CHANNEL_ID=your_admin_channel_id_here
   GAME_REQUEST_CHANNEL_ID=your_game_request_channel_id_here

   # AMP Configuration
   AMP_HOST=your_amp_host_here
   AMP_PORT=8080
   AMP_USERNAME=your_amp_username_here
   AMP_PASSWORD=your_amp_password_here
   ```

4. **Configure games** (optional)
   - Edit `config/games.py` to add/remove/modify available games
   - Update templates, roles, and requirements as needed

## Discord Bot Setup

1. **Create a Discord Application**

   - Go to https://discord.com/developers/applications
   - Create a new application
   - Go to the "Bot" section and create a bot
   - Copy the bot token

2. **Bot Permissions**
   Your bot needs these permissions:

   - Send Messages
   - Use Slash Commands
   - Embed Links
   - Read Message History
   - Add Reactions
   - Manage Messages

3. **Invite Bot to Server**
   - Go to the "OAuth2" section in Discord Developer Portal
   - Select "bot" scope and required permissions
   - Use the generated URL to invite the bot

## AMP Setup

1. **AMP User Requirements**

   - The bot needs an AMP user with administrative privileges
   - User should have permissions to create users and instances

2. **Game Templates**

   - Ensure your AMP instance has the required game templates
   - Update `config/games.py` with correct template IDs

3. **Roles Configuration**
   - Set up appropriate roles in AMP for each game
   - Update the default roles in `config/games.py`

## Usage

1. **Start the bot**

   ```bash
   python main.py
   ```

2. **Set up the request system**

   - Use `!setup_requests` command in your desired channel (admin only)
   - This creates the interactive embed with game selection buttons

3. **User Flow**

   - Users click buttons to request servers
   - Requests appear in the admin channel
   - Admins approve/reject with buttons
   - Approved users receive AMP credentials via DM

4. **Admin Commands**
   - `!setup_requests` - Set up the game request embed
   - `!pending_requests` - List all pending requests
   - `!my_requests` - Users can check their pending requests

## Configuration

### Games Configuration (`config/games.py`)

- Add new games by creating `GameTemplate` objects
- Configure template IDs, roles, and requirements
- Set display names and emojis

### Settings (`config/settings.py`)

- Modify timeout periods
- Change maximum pending requests per user
- Adjust database paths

### Database

- SQLite database automatically created
- Location configurable in settings
- Automatic cleanup of expired requests

## File Structure

```txt
AMP_discord_bot/
├── main.py                 # Main bot file
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── .gitignore             # Git ignore rules
├── config/
│   ├── settings.py        # Bot configuration
│   └── games.py           # Game templates
├── cogs/
│   ├── admin.py           # Admin commands and approval system
│   └── game_requests.py   # User request handling
├── database/
│   └── db.py              # Database operations
├── models/
│   └── __init__.py        # Data models
├── services/
│   └── amp_service.py     # AMP API integration
└── utils/
    ├── helpers.py         # Utility functions
    └── logging.py         # Logging configuration
```

## Troubleshooting

### Common Issues

1. **Bot not responding**

   - Check Discord token
   - Verify bot permissions
   - Check console for error messages

2. **AMP connection failed**

   - Verify AMP host, port, username, and password
   - Ensure AMP user has admin privileges
   - Check network connectivity

3. **Database errors**

   - Ensure write permissions in database directory
   - Check disk space
   - Verify database path in settings

4. **Missing game templates**
   - Verify template IDs in AMP
   - Update `config/games.py` with correct IDs
   - Check AMP module availability

### Logs

- Bot logs are saved in the `logs/` directory
- Check logs for detailed error information
- Logs rotate daily

## Security Notes

- Keep your `.env` file secure and never commit it to version control
- AMP credentials should have minimal required permissions
- Consider using environment variables in production
- Regularly rotate bot tokens and AMP passwords

## Contributing

Feel free to modify and extend the bot for your needs:

- Add new games in `config/games.py`
- Modify embed designs in `utils/helpers.py`
- Add new commands in the appropriate cogs
- Extend AMP integration in `services/amp_service.py`

## Support

If you encounter issues:

1. Check the logs for error messages
2. Verify your configuration
3. Ensure all dependencies are installed
4. Check AMP and Discord API status

## License

This project is provided as-is for educational and personal use.
