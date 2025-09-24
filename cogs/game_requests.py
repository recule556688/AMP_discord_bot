import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime
from typing import Optional

from config.settings import settings
from config.games import get_game_by_name, get_games_list, AVAILABLE_GAMES
from database.db import DatabaseManager
from models import GameRequest, RequestStatus
from utils.logging import BotLogger
from utils.helpers import (
    create_embed,
    create_game_selection_embed,
    create_game_selection_view,
    create_request_confirmation_embed,
    format_user_info,
    format_request_summary,
)


class GameRequestsCog(commands.Cog):
    @app_commands.command(
        name="how_to_request",
        description="Show instructions for requesting a game server (EN/FR)",
    )
    @app_commands.default_permissions(administrator=True)
    async def how_to_request_slash(self, interaction: discord.Interaction):
        """Send an attractive embed explaining how to request a game server (EN/FR) as a slash command."""
        request_channel_id = getattr(settings, "game_request_channel_id", None)
        request_channel_mention = (
            f"<#{request_channel_id}>" if request_channel_id else "the request channel"
        )
        max_pending = settings.max_pending_requests_per_user

        embed = discord.Embed(
            title="🎮 How to Request a Game Server | Comment demander un serveur",
            description=(
                f"**ENGLISH**\n"
                f"1️⃣ Go to {request_channel_mention}.\n"
                "2️⃣ Use `/request` or the button to select your game.\n"
                "3️⃣ A private thread will be created for your request.\n"
                "4️⃣ You and admins can discuss in the thread.\n"
                "5️⃣ Admins approve or deny in the thread.\n"
                "6️⃣ If approved, you'll get your server credentials via DM.\n\n"
                f"**Note:** You can have up to **{max_pending}** pending requests.\n\n"
                "**FRANÇAIS**\n"
                f"1️⃣ Rendez-vous dans {request_channel_mention}.\n"
                "2️⃣ Utilisez `/request` ou le bouton pour choisir votre jeu.\n"
                "3️⃣ Un fil privé sera créé pour votre demande.\n"
                "4️⃣ Vous et les admins pourrez discuter dans ce fil.\n"
                "5️⃣ Les admins approuvent ou refusent dans le fil.\n"
                "6️⃣ Si accepté, vous recevrez vos identifiants par message privé.\n\n"
                f"**Note :** Vous pouvez avoir jusqu'à **{max_pending}** demandes en attente."
            ),
            color=discord.Color.purple(),
        )
        embed.add_field(
            name="✨ What happens next? | Que se passe-t-il après ?",
            value=(
                "- Admins will review your request in the thread.\n"
                "- You may be asked for more info.\n"
                "- Once approved, your server will be provisioned and details sent to you.\n"
                "- If denied, you will be notified with a reason.\n\n"
                "- Les admins examineront votre demande dans le fil.\n"
                "- On pourra vous demander plus d'infos.\n"
                "- Si accepté, le serveur sera créé et les infos envoyées.\n"
                "- Si refusé, vous recevrez la raison."
            ),
            inline=False,
        )
        embed.set_footer(
            text="If you have questions, ask an admin! | Si vous avez des questions, contactez un admin !"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.command(
        name="how_to_request",
        help="Send instructions for requesting a game server (EN/FR).",
    )
    @commands.has_permissions(administrator=True)
    async def how_to_request(self, ctx: commands.Context):
        """Send an attractive embed explaining how to request a game server (EN/FR)."""
        # Get the request channel mention from .env
        request_channel_id = getattr(settings, "game_request_channel_id", None)
        request_channel_mention = (
            f"<#{request_channel_id}>" if request_channel_id else "the request channel"
        )
        max_pending = settings.max_pending_requests_per_user

        embed = discord.Embed(
            title="🎮 How to Request a Game Server | Comment demander un serveur",
            description=(
                f"**ENGLISH**\n"
                f"1️⃣ Go to {request_channel_mention}.\n"
                "2️⃣ Use `/request` or the button to select your game.\n"
                "3️⃣ A private thread will be created for your request.\n"
                "4️⃣ You and admins can discuss in the thread.\n"
                "5️⃣ Admins approve or deny in the thread.\n"
                "6️⃣ If approved, you'll get your server credentials via DM.\n\n"
                f"**Note:** You can have up to **{max_pending}** pending requests.\n\n"
                "**FRANÇAIS**\n"
                f"1️⃣ Rendez-vous dans {request_channel_mention}.\n"
                "2️⃣ Utilisez `/request` ou le bouton pour choisir votre jeu.\n"
                "3️⃣ Un fil privé sera créé pour votre demande.\n"
                "4️⃣ Vous et les admins pourrez discuter dans ce fil.\n"
                "5️⃣ Les admins approuvent ou refusent dans le fil.\n"
                "6️⃣ Si accepté, vous recevrez vos identifiants par message privé.\n\n"
                f"**Note :** Vous pouvez avoir jusqu'à **{max_pending}** demandes en attente."
            ),
            color=discord.Color.purple(),
        )
        embed.add_field(
            name="✨ What happens next? | Que se passe-t-il après ?",
            value=(
                "- Admins will review your request in the thread.\n"
                "- You may be asked for more info.\n"
                "- Once approved, your server will be provisioned and details sent to you.\n"
                "- If denied, you will be notified with a reason.\n\n"
                "- Les admins examineront votre demande dans le fil.\n"
                "- On pourra vous demander plus d'infos.\n"
                "- Si accepté, le serveur sera créé et les infos envoyées.\n"
                "- Si refusé, vous recevrez la raison."
            ),
            inline=False,
        )
        embed.set_footer(
            text="If you have questions, ask an admin! | Si vous avez des questions, contactez un admin !"
        )
        await ctx.send(embed=embed)

    """Handles game server requests from users."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = DatabaseManager(settings.database_path)
        self.logger = BotLogger(__name__)
        self.cleanup_expired_requests.start()

    def cog_unload(self):
        """Clean up when cog is unloaded."""
        self.cleanup_expired_requests.cancel()

    @tasks.loop(hours=1)
    async def cleanup_expired_requests(self):
        """Clean up expired requests every hour."""
        try:
            await self.db.expire_old_requests(settings.request_timeout_hours)
            self.logger.info("Cleaned up expired requests")
        except Exception as e:
            self.logger.error("Failed to clean up expired requests", e)

    @cleanup_expired_requests.before_loop
    async def before_cleanup(self):
        """Wait for bot to be ready before starting cleanup."""
        await self.bot.wait_until_ready()

    @commands.command(name="setup_requests")
    @commands.has_permissions(administrator=True)
    async def setup_game_requests(self, ctx: commands.Context):
        """Set up the game request embed and buttons."""
        try:
            # Create the embed and view
            embed = create_game_selection_embed()
            view = create_game_selection_view()

            # Add the callback to the view buttons
            for item in view.children:
                if isinstance(item, discord.ui.Button):
                    item.callback = self.game_request_callback

            # Send the message
            message = await ctx.send(embed=embed, view=view)

            # Add the view to persistent views
            self.bot.add_view(view, message_id=message.id)

            await ctx.send(
                "✅ Game request system set up successfully!", ephemeral=True
            )
            self.logger.log_admin_action(
                ctx.author.id,
                format_user_info(ctx.author),
                "Setup game request system",
                message_id=message.id,
            )

        except Exception as e:
            await ctx.send("❌ Failed to set up game request system.", ephemeral=True)
            self.logger.error("Failed to set up game request system", e)

    async def game_request_callback(self, interaction: discord.Interaction):
        """Handle game request button clicks."""
        try:
            # Extract game name from custom_id
            custom_id = interaction.data.get("custom_id", "")
            if not custom_id.startswith("game_request_"):
                await interaction.response.send_message(
                    "❌ Invalid request.", ephemeral=True
                )
                return

            game_name = custom_id.replace("game_request_", "")
            game = get_game_by_name(game_name)

            if not game:
                await interaction.response.send_message(
                    "❌ Game not found.", ephemeral=True
                )
                return

            # Check if user has too many pending requests
            user_requests = await self.db.get_user_pending_requests(interaction.user.id)
            if len(user_requests) >= settings.max_pending_requests_per_user:
                await interaction.response.send_message(
                    f"❌ You already have {len(user_requests)} pending request(s). "
                    f"Please wait for them to be processed before submitting new ones.",
                    ephemeral=True,
                )
                return

            # Allow multiple requests for the same game, as long as under the global limit

            # Create the request
            request = GameRequest(
                user_id=interaction.user.id,
                username=format_user_info(interaction.user),
                game_name=game_name,
                status=RequestStatus.PENDING,
                requested_at=datetime.utcnow(),
                message_id=interaction.message.id,
            )

            # Save to database
            request_id = await self.db.create_request(request)
            request.id = request_id

            # Send confirmation to user (ephemeral only, not in thread)
            embed = create_request_confirmation_embed(game, interaction.user)
            await interaction.response.send_message(embed=embed, ephemeral=False)

            # Notify admin channel (thread creation and admin view)
            await self._notify_admins(request, game, interaction.user)

            self.logger.log_user_action(
                interaction.user.id,
                format_user_info(interaction.user),
                "Submitted game request",
                game=game_name,
                request_id=request_id,
            )

        except Exception as e:
            await interaction.response.send_message(
                "❌ An error occurred while processing your request. Please try again later.",
                ephemeral=True,
            )
            self.logger.error("Failed to process game request", e)

    async def _notify_admins(self, request: GameRequest, game, user):
        """Notify admins about a new request by creating a private thread."""
        try:
            request_channel = self.bot.get_channel(settings.game_request_channel_id)
            if not request_channel or not isinstance(
                request_channel, discord.TextChannel
            ):
                self.logger.error(
                    f"Request channel {settings.game_request_channel_id} not found or not a text channel"
                )
                return

            from utils.helpers import (
                create_admin_approval_embed,
                create_admin_approval_view,
            )

            embed = create_admin_approval_embed(request, game, user)
            view = create_admin_approval_view(request.id)

            # Get admin cog
            admin_cog = self._get_admin_cog()
            if not admin_cog:
                self.logger.error("AdminCog not found! Buttons will not work.")
                # Send embed without buttons as fallback
                await request_channel.send(embed=embed)
                return
            else:
                self.logger.debug("AdminCog found successfully")

            # Add callbacks to approval buttons
            for item in view.children:
                if isinstance(item, discord.ui.Button):
                    if item.custom_id.startswith("approve_request_"):
                        item.callback = admin_cog.approve_request_callback
                        self.logger.debug(
                            f"Set approve callback for button {item.custom_id}"
                        )
                    elif item.custom_id.startswith("reject_request_"):
                        item.callback = admin_cog.reject_request_callback
                        self.logger.debug(
                            f"Set reject callback for button {item.custom_id}"
                        )

            # Create a private thread for the request
            thread_name = f"{user.display_name}-{game.display_name}-req#{request.id}"
            thread = await request_channel.create_thread(
                name=thread_name,
                type=discord.ChannelType.private_thread,
                invitable=False,
            )
            # Add the user to the thread
            await thread.add_user(user)
            # Add all admins to the thread
            guild = request_channel.guild
            admin_role = discord.utils.get(guild.roles, permissions__administrator=True)
            if admin_role:
                for member in admin_role.members:
                    try:
                        await thread.add_user(member)
                    except Exception:
                        pass

            # Post the embed and view in the thread
            message = await thread.send(embed=embed, view=view)

            # Update request with admin message ID and thread ID
            await self.db.update_request_status(
                request.id,
                RequestStatus.PENDING,
                admin_message_id=message.id,
                amp_user_id=None,
                amp_instance_id=None,
                notes=None,
                processed_by=None,
                thread_id=thread.id,
            )

            # Add view to persistent views
            self.bot.add_view(view, message_id=message.id)
            self.logger.info(
                f"Created thread '{thread_name}' ({thread.id}) and posted approval message {message.id}"
            )

        except Exception as e:
            self.logger.error("Failed to notify admins (thread workflow)", e)
            # Fallback: send embed in the request channel
            try:
                await request_channel.send(embed=embed)
            except Exception as fallback_error:
                self.logger.error("Fallback notification also failed", fallback_error)

    def _get_admin_cog(self):
        """Get the admin cog."""
        return self.bot.get_cog("AdminCog")

    @commands.command(name="my_requests")
    async def my_requests(self, ctx: commands.Context):
        """Show user's pending requests."""
        try:
            requests = await self.db.get_user_pending_requests(ctx.author.id)

            if not requests:
                await ctx.send("You have no pending requests.", ephemeral=True)
                return

            embed = discord.Embed(
                title="Your Pending Requests",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow(),
            )

            for request in requests:
                game = get_game_by_name(request.game_name)
                game_display = game.display_name if game else request.game_name

                embed.add_field(
                    name=f"{game.icon_emoji if game else '🎮'} {game_display}",
                    value=f"Request #{request.id}\nSubmitted: {request.requested_at.strftime('%Y-%m-%d %H:%M')}",
                    inline=True,
                )

            embed.set_footer(text=f"Total: {len(requests)} pending request(s)")
            await ctx.send(embed=embed, ephemeral=True)

        except Exception as e:
            await ctx.send("❌ Failed to retrieve your requests.", ephemeral=True)
            self.logger.error("Failed to get user requests", e)

    # Slash Commands

    @app_commands.command(name="request", description="Request a game server")
    @app_commands.describe(game="The type of game server to request")
    async def request_game_server(
        self, interaction: discord.Interaction, game: Optional[str] = None
    ):
        """Request a game server via slash command."""
        if not game:
            # Show available games
            embed = create_embed(
                title="Available Game Servers",
                description="Here are the available game types you can request:",
                color=discord.Color.blue(),
            )

            for game_template in AVAILABLE_GAMES:
                embed.add_field(
                    name=f"{game_template.icon_emoji} {game_template.display_name}",
                    value=f"**Description:** {game_template.description}\n"
                    f"**Requirements:** {game_template.requirements or 'None'}\n"
                    f"**Role:** {game_template.default_role}",
                    inline=True,
                )

            embed.set_footer(text="Use /request <game> to request a server")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        game = game.lower()

        # Check if game exists
        game_template = get_game_by_name(game)
        if not game_template:
            embed = create_embed(
                title="Invalid Game",
                description=f"'{game}' is not a supported game type.",
                color=discord.Color.red(),
            )
            available_games = [g.name for g in AVAILABLE_GAMES]
            embed.add_field(
                name="Available Games",
                value=", ".join(available_games),
                inline=False,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check if user has too many pending requests
        user_requests = await self.db.get_user_pending_requests(interaction.user.id)
        if len(user_requests) >= settings.max_pending_requests_per_user:
            await interaction.response.send_message(
                f"❌ You already have {len(user_requests)} pending request(s). "
                f"Please wait for them to be processed before submitting new ones.",
                ephemeral=True,
            )
            return

        # Check if user already has a pending request for this game
        for request in user_requests:
            if request.game_name == game:
                await interaction.response.send_message(
                    f"❌ You already have a pending request for {game.title()}.",
                    ephemeral=True,
                )
                return

        # Create new request
        request = GameRequest(
            user_id=interaction.user.id,
            username=format_user_info(interaction.user),
            game_name=game,
            status=RequestStatus.PENDING,
            requested_at=datetime.utcnow(),
        )

        try:
            request_id = await self.db.create_request(request)
            request.id = request_id

            from utils.helpers import format_requirements

            embed = create_embed(
                title="Game Server Request Submitted",
                description=f"Your request for a {game_template.display_name} server has been submitted!",
                color=discord.Color.green(),
            )

            details = (
                f"**Request ID:** `{request_id}`\n"
                f"**Game:** {game_template.display_name}\n"
                f"**Template:** `{game_template.template_id}`\n"
                f"**Requirements:**\n{format_requirements(game_template.requirements)}"
            )
            embed.add_field(
                name="Request Details",
                value=details,
                inline=False,
            )

            embed.add_field(
                name="What's Next?",
                value="Your request will be reviewed by an administrator. "
                "You'll be notified when it's approved or if more information is needed.",
                inline=False,
            )

            embed.set_footer(
                text=f"Request ID: {request_id} • Today at {datetime.utcnow().strftime('%I:%M %p')}"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

            # Notify admin channel with buttons
            await self._notify_admins(request, game_template, interaction.user)

            self.logger.log_user_action(
                interaction.user.id,
                format_user_info(interaction.user),
                "Submitted game request",
                game=game,
                request_id=request_id,
            )

        except Exception as e:
            self.logger.error(f"Error creating game request: {e}")
            embed = create_embed(
                title="Request Failed",
                description="There was an error submitting your request. Please try again later.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="status", description="Check the status of your current requests"
    )
    async def check_request_status(self, interaction: discord.Interaction):
        """Check the status of your current requests via slash command."""
        try:
            requests = await self.db.get_user_pending_requests(interaction.user.id)

            if not requests:
                embed = create_embed(
                    title="No Active Requests",
                    description="You don't have any pending requests.",
                    color=discord.Color.blue(),
                )
                embed.add_field(
                    name="Make a Request",
                    value="Use `/request <game>` to request a game server.",
                    inline=False,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            embed = create_embed(
                title="Your Request Status",
                description=f"Here are your current requests:",
                color=discord.Color.blue(),
            )

            for request in requests:
                embed.add_field(
                    name=f"Request #{request.id}",
                    value=f"**Game:** {request.game_name.title()}\n"
                    f"**Status:** {request.status.value.title()}\n"
                    f"**Requested:** <t:{int(request.requested_at.timestamp())}:R>",
                    inline=True,
                )

            embed.set_footer(text=f"Total: {len(requests)} pending request(s)")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Error checking request status: {e}")
            embed = create_embed(
                title="Status Check Failed",
                description="There was an error checking your request status. Please try again.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="cancel", description="Cancel one of your pending requests"
    )
    @app_commands.describe(request_id="The ID of the request to cancel")
    async def cancel_request(self, interaction: discord.Interaction, request_id: int):
        """Cancel a pending request via slash command."""
        try:
            # Get the request and verify ownership
            request = await self.db.get_request_by_id(request_id)

            if not request:
                embed = create_embed(
                    title="Request Not Found",
                    description=f"No request found with ID {request_id}.",
                    color=discord.Color.red(),
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if request.user_id != interaction.user.id:
                embed = create_embed(
                    title="Access Denied",
                    description="You can only cancel your own requests.",
                    color=discord.Color.red(),
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if request.status != RequestStatus.PENDING:
                embed = create_embed(
                    title="Cannot Cancel",
                    description=f"Request #{request_id} is currently '{request.status.value}' and cannot be cancelled.",
                    color=discord.Color.red(),
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Cancel the request
            await self.db.update_request_status(request_id, RequestStatus.CANCELLED)

            embed = create_embed(
                title="Request Cancelled",
                description=f"Your request #{request_id} for {request.game_name.title()} has been cancelled.",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

            self.logger.log_user_action(
                interaction.user.id,
                format_user_info(interaction.user),
                "Cancelled request",
                request_id=request_id,
            )

        except Exception as e:
            self.logger.error(f"Error cancelling request {request_id}: {e}")
            embed = create_embed(
                title="Cancellation Failed",
                description="There was an error cancelling your request. Please try again.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @request_game_server.autocomplete("game")
    async def game_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for game parameter."""
        available_games = [game.name for game in AVAILABLE_GAMES]
        return [
            app_commands.Choice(name=game.title(), value=game)
            for game in available_games
            if current.lower() in game.lower()
        ][
            :25
        ]  # Discord limit is 25 choices


async def setup(bot: commands.Bot):
    """Set up the cog."""
    await bot.add_cog(GameRequestsCog(bot))
