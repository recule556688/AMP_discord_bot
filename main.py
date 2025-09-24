import asyncio
import discord
from discord.ext import commands
import os
import sys

# Set timezone environment variable to fix UTC timezone issues
os.environ["TZ"] = "UTC"

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from database.db import DatabaseManager
from utils.logging import BotLogger


class AMPDiscordBot(commands.Bot):
    """Main Discord bot class."""

    def __init__(self):
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
            case_insensitive=True,
        )

        self.logger = BotLogger(__name__)
        self.db = DatabaseManager(settings.database_path)

    async def setup_hook(self):
        """Set up the bot when it starts."""
        try:
            # Initialize database
            await self.db.initialize()
            self.logger.info("Database initialized successfully")

            # Load cogs
            await self.load_extension("cogs.game_requests")
            await self.load_extension("cogs.admin")
            self.logger.info("All cogs loaded successfully")

            # Sync slash commands
            if hasattr(settings, "guild_id") and settings.guild_id:
                # Sync to specific guild for faster updates during development
                guild = discord.Object(id=settings.guild_id)
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                self.logger.info(f"Slash commands synced to guild {settings.guild_id}")
            else:
                # Sync globally (takes up to an hour to propagate)
                await self.tree.sync()
                self.logger.info("Slash commands synced globally")

        except Exception as e:
            self.logger.error("Failed to set up bot", e)
            raise

    async def on_ready(self):
        """Called when the bot is ready."""
        self.logger.info(f"Bot is ready! Logged in as {self.user} (ID: {self.user.id})")
        self.logger.info(f"Connected to {len(self.guilds)} guild(s)")

        # Set bot status
        activity = discord.Activity(
            type=discord.ActivityType.watching, name="for game server requests"
        )
        await self.change_presence(activity=activity, status=discord.Status.do_not_disturb)

    async def on_error(self, event, *args, **kwargs):
        """Handle bot errors."""
        self.logger.error(f"Error in event {event}", exc_info=sys.exc_info())

    async def on_command_error(self, ctx, error):
        """Handle command errors."""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore unknown commands

        if isinstance(error, commands.MissingPermissions):
            await ctx.send(
                "❌ You don't have permission to use this command.", ephemeral=True
            )
            return

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"❌ Missing required argument: `{error.param.name}`", ephemeral=True
            )
            return

        if isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Invalid argument: {str(error)}", ephemeral=True)
            return

        # Log unexpected errors
        self.logger.error(f"Command error in {ctx.command}", error)
        await ctx.send(
            "❌ An unexpected error occurred. Please try again later.", ephemeral=True
        )

    async def on_app_command_error(self, interaction, error):
        """Handle slash command errors."""
        if isinstance(error, discord.app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.", ephemeral=True
            )
            return

        if isinstance(error, discord.app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"❌ Command is on cooldown. Try again in {error.retry_after:.2f} seconds.",
                ephemeral=True,
            )
            return

        # Log unexpected errors
        self.logger.error(f"App command error: {error}")

        # Send error message
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ An unexpected error occurred. Please try again later.",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                "❌ An unexpected error occurred. Please try again later.",
                ephemeral=True,
            )

    async def close(self):
        """Clean up when bot shuts down."""
        self.logger.info("Bot is shutting down...")

        # Disconnect AMP service if connected
        amp_cog = self.get_cog("AdminCog")
        if amp_cog and amp_cog.amp_service:
            await amp_cog.amp_service.disconnect()

        await super().close()


async def main():
    """Main function to run the bot."""
    try:
        # Validate settings
        if not settings.discord_token:
            print("❌ Discord token not found. Please check your .env file.")
            return

        if (
            not settings.amp_host
            or not settings.amp_username
            or not settings.amp_password
        ):
            print("❌ AMP configuration incomplete. Please check your .env file.")
            return

        # Create and run bot
        bot = AMPDiscordBot()

        async with bot:
            await bot.start(settings.discord_token)

    except discord.LoginFailure:
        print("❌ Invalid Discord token. Please check your .env file.")
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user.")
    except Exception as e:
        print(f"❌ Critical error: {e}")
