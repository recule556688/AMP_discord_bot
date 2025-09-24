import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import asyncio

from config.settings import settings
from config.games import get_game_by_name
from config.templates import (
    get_template_id,
    list_available_templates,
    update_template_id,
)
from database.db import DatabaseManager
from models import RequestStatus
from services.amp_service import AMPService
from utils.logging import BotLogger
from utils.helpers import (
    create_status_update_embed,
    format_user_info,
    format_request_summary,
    create_embed,
)


class AdminCog(commands.Cog):
    """Handles admin functions for game requests."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = DatabaseManager(settings.database_path)
        self.amp_service = AMPService(
            settings.amp_host,
            settings.amp_port,
            settings.amp_username,
            settings.amp_password,
        )
        self.logger = BotLogger(__name__)

    @commands.Cog.listener()
    async def on_ready(self):
        """Initialize AMP connection when bot is ready."""
        await self._ensure_amp_connection()
        await self._register_persistent_views()

    async def _register_persistent_views(self):
        """Register persistent views for approve/deny buttons."""
        try:
            # Get all pending requests that might have admin messages
            pending_requests = await self.db.get_pending_requests()

            for request in pending_requests:
                if hasattr(request, "admin_message_id") and request.admin_message_id:
                    # Create a view for this request
                    from utils.helpers import create_admin_approval_view

                    view = create_admin_approval_view(request.id)

                    # Set up callbacks
                    for item in view.children:
                        if isinstance(item, discord.ui.Button):
                            if item.custom_id.startswith("approve_request_"):
                                item.callback = self.approve_request_callback
                            elif item.custom_id.startswith("reject_request_"):
                                item.callback = self.reject_request_callback

                    # Add the view to persistent views
                    self.bot.add_view(view, message_id=request.admin_message_id)

            self.logger.info(
                f"Registered persistent views for {len(pending_requests)} pending requests"
            )

        except Exception as e:
            self.logger.error("Failed to register persistent views", e)

    async def _ensure_amp_connection(self):
        """Ensure AMP service is connected."""
        if not await self.amp_service.check_connection():
            connected = await self.amp_service.connect()
            if not connected:
                self.logger.error("Failed to connect to AMP service")
            else:
                self.logger.info("Connected to AMP service")

    @commands.command(name="pending_requests")
    @commands.has_permissions(administrator=True)
    async def list_pending_requests(self, ctx: commands.Context):
        """List all pending requests."""
        try:
            requests = await self.db.get_pending_requests()

            if not requests:
                await ctx.send("✅ No pending requests.", ephemeral=True)
                return

            embed = discord.Embed(
                title="Pending Game Server Requests",
                color=discord.Color.orange(),
                timestamp=ctx.message.created_at,
            )

            for request in requests[:10]:  # Limit to 10 to avoid embed limits
                game = get_game_by_name(request.game_name)
                game_display = game.display_name if game else request.game_name

                embed.add_field(
                    name=f"#{request.id} - {game.icon_emoji if game else '🎮'} {game_display}",
                    value=f"User: {request.username}\nSubmitted: {request.requested_at.strftime('%Y-%m-%d %H:%M')}",
                    inline=True,
                )

            if len(requests) > 10:
                embed.set_footer(
                    text=f"Showing 10 of {len(requests)} requests. Use command with ID for specific request."
                )
            else:
                embed.set_footer(text=f"Total: {len(requests)} pending request(s)")

            await ctx.send(embed=embed, ephemeral=True)

        except Exception as e:
            await ctx.send("❌ Failed to retrieve pending requests.", ephemeral=True)
            self.logger.error("Failed to get pending requests", e)

    async def approve_request_callback(self, interaction: discord.Interaction):
        """Handle request approval button clicks."""
        try:
            # Check permissions
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    "❌ You don't have permission to do this.", ephemeral=True
                )
                return

            # Extract request ID
            custom_id = interaction.data.get("custom_id", "")
            if not custom_id.startswith("approve_request_"):
                await interaction.response.send_message(
                    "❌ Invalid request.", ephemeral=True
                )
                return

            request_id = int(custom_id.replace("approve_request_", ""))

            # Defer the response as this might take a while
            await interaction.response.defer(ephemeral=True)

            # Get the request
            request = await self.db.get_request(request_id)
            if not request:
                await interaction.followup.send("❌ Request not found.", ephemeral=True)
                return

            if request.status != RequestStatus.PENDING:
                await interaction.followup.send(
                    f"❌ Request already {request.status.value}.", ephemeral=True
                )
                return

            # Get game info
            game = get_game_by_name(request.game_name)
            if not game:
                await interaction.followup.send(
                    "❌ Game configuration not found.", ephemeral=True
                )
                return

            # Get the user
            user = self.bot.get_user(request.user_id)
            if not user:
                await interaction.followup.send("❌ User not found.", ephemeral=True)
                return

            # Process the approval
            success, amp_user_name, instance_name = await self._process_approval(
                request, game, user
            )

            if success:
                # Update database
                await self.db.update_request_status(
                    request_id,
                    RequestStatus.APPROVED,
                    processed_by=interaction.user.id,
                    notes="Approved by admin",
                    amp_user_id=amp_user_name,
                    amp_instance_id=instance_name,
                )

                # Update the admin message
                await self._update_admin_message(
                    interaction.message, request, game, True, interaction.user
                )

                # Notify the user
                await self._notify_user_approval(
                    user, request, game, interaction.user, amp_user_name, instance_name
                )

                await interaction.followup.send(
                    f"✅ Request #{request_id} approved successfully!", ephemeral=True
                )

                self.logger.log_admin_action(
                    interaction.user.id,
                    format_user_info(interaction.user),
                    "Approved request",
                    target_user=request.username,
                    request_id=request_id,
                    game=request.game_name,
                )
            else:
                await interaction.followup.send(
                    f"❌ Failed to process approval for request #{request_id}.",
                    ephemeral=True,
                )

        except Exception as e:
            await interaction.followup.send(
                "❌ An error occurred while processing the approval.", ephemeral=True
            )
            self.logger.error("Failed to approve request", e)

    async def reject_request_callback(self, interaction: discord.Interaction):
        """Handle request rejection button clicks."""
        try:
            # Check permissions
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    "❌ You don't have permission to do this.", ephemeral=True
                )
                return

            # Extract request ID
            custom_id = interaction.data.get("custom_id", "")
            if not custom_id.startswith("reject_request_"):
                await interaction.response.send_message(
                    "❌ Invalid request.", ephemeral=True
                )
                return

            request_id = int(custom_id.replace("reject_request_", ""))

            # Get the request
            request = await self.db.get_request(request_id)
            if not request:
                await interaction.response.send_message(
                    "❌ Request not found.", ephemeral=True
                )
                return

            if request.status != RequestStatus.PENDING:
                await interaction.response.send_message(
                    f"❌ Request already {request.status.value}.", ephemeral=True
                )
                return

            # Show modal for rejection reason
            modal = RejectionModal(request_id, self.db, self.bot, self.logger)
            await interaction.response.send_modal(modal)

        except Exception as e:
            await interaction.response.send_message(
                "❌ An error occurred while processing the rejection.", ephemeral=True
            )
            self.logger.error("Failed to reject request", e)

    async def _process_approval(self, request, game, user):
        """Process the approval by creating AMP user and instance."""
        try:
            await self._ensure_amp_connection()

            # Generate AMP username (Discord username + discriminator or ID)
            amp_username = (
                f"{user.name}_{user.discriminator}"
                if user.discriminator != "0"
                else f"{user.name}_{user.id}"
            )
            amp_username = amp_username.lower().replace(" ", "_")[
                :20
            ]  # AMP username limits

            # Create AMP user
            amp_user = await self.amp_service.create_user(
                username=amp_username,
                email=f"{amp_username}@discord.local",  # Placeholder email
                roles=[game.default_role],
                discord_user_id=user.id,
            )

            if not amp_user:
                self.logger.error(f"Failed to create AMP user for {user.name}")
                return False, None, None

            # Create AMP instance
            instance_name = f"{user.name}_{game.name}_server"[:30]
            amp_instance = await self.amp_service.create_instance(
                name=instance_name,
                template=game.template_id,
                owner_id=amp_user.user_id,
                amp_username=amp_username,
            )

            if not amp_instance:
                self.logger.error(f"Failed to create AMP instance for {user.name}")
                return False, amp_user.username, None

            # Send credentials to user via DM
            await self._send_credentials_dm(user, amp_user, game)

            return True, amp_user.username, amp_instance.instance_id

        except Exception as e:
            self.logger.error("Error processing approval", e)
            return False, None, None

    async def _send_credentials_dm(self, user, amp_user, game):
        """Send AMP credentials to user via DM."""
        try:
            import os

            amp_ip = os.getenv("AMP_IP") or settings.amp_host
            amp_port = settings.amp_port
            embed = discord.Embed(
                title=f"🎮 {game.display_name} Server Access",
                description="Your server has been approved! Here are your access credentials:",
                color=discord.Color.green(),
            )

            embed.add_field(
                name="AMP Panel URL",
                value=f"http://{amp_ip}",
                inline=False,
            )
            embed.add_field(
                name="Username", value=f"`{amp_user.username}`", inline=True
            )
            embed.add_field(
                name="Password", value=f"||{amp_user.password}||", inline=True
            )

            embed.add_field(
                name="Important Notes",
                value="• Keep these credentials safe\n• Your server may take a few minutes to fully initialize\n• Contact an admin if you need help",
                inline=False,
            )

            embed.set_footer(
                text="This message will not be sent again. Save your credentials!"
            )

            await user.send(embed=embed)

        except discord.Forbidden:
            self.logger.warning(f"Could not send DM to {user.name} - DMs disabled")
        except Exception as e:
            self.logger.error("Failed to send credentials DM", e)

    async def _update_admin_message(self, message, request, game, approved, admin):
        """Update the admin message after processing."""
        try:
            status = "✅ APPROVED" if approved else "❌ REJECTED"
            color = discord.Color.green() if approved else discord.Color.red()

            embed = discord.Embed(
                title=f"{status} - {game.display_name} Request",
                description=f"Request #{request.id} has been {status.lower()}",
                color=color,
                timestamp=message.created_at,
            )

            embed.add_field(name="User", value=request.username, inline=True)
            embed.add_field(
                name="Game", value=f"{game.icon_emoji} {game.display_name}", inline=True
            )
            embed.add_field(name="Processed by", value=admin.mention, inline=True)

            # Remove the buttons
            await message.edit(embed=embed, view=None)

        except Exception as e:
            self.logger.error("Failed to update admin message", e)

    async def _notify_user_approval(
        self, user, request, game, admin, amp_user_name, instance_name
    ):
        """Notify user about approval."""
        try:
            embed = create_status_update_embed(
                request,
                game,
                True,
                admin,
                amp_user=amp_user_name,
                instance=instance_name,
            )

            # Try to send in the original channel first
            channel = self.bot.get_channel(settings.game_request_channel_id)
            if channel:
                await channel.send(f"{user.mention}", embed=embed)

        except Exception as e:
            self.logger.error("Failed to notify user of approval", e)

    # Slash Commands for Admins

    @app_commands.command(name="approve", description="Approve a game server request")
    @app_commands.describe(request_id="The ID of the request to approve")
    @app_commands.default_permissions(administrator=True)
    async def approve_request_slash(
        self, interaction: discord.Interaction, request_id: int
    ):
        """Approve a request via slash command."""
        try:
            # Defer the response as this might take a while
            await interaction.response.defer(ephemeral=True)

            # Get the request
            request = await self.db.get_request_by_id(request_id)
            if not request:
                await interaction.followup.send("❌ Request not found.", ephemeral=True)
                return

            if request.status != RequestStatus.PENDING:
                await interaction.followup.send(
                    f"❌ Request already {request.status.value}.", ephemeral=True
                )
                return

            # Get game info
            game = get_game_by_name(request.game_name)
            if not game:
                await interaction.followup.send(
                    "❌ Game configuration not found.", ephemeral=True
                )
                return

            # Get the user
            user = self.bot.get_user(request.user_id)
            if not user:
                await interaction.followup.send("❌ User not found.", ephemeral=True)
                return

            # Process the approval
            success, amp_user_name, instance_name = await self._process_approval(
                request, game, user
            )

            if success:
                # Update database
                await self.db.update_request_status(
                    request_id,
                    RequestStatus.APPROVED,
                    processed_by=interaction.user.id,
                    notes="Approved by admin",
                    amp_user_id=amp_user_name,
                    amp_instance_id=instance_name,
                )

                # Notify the user
                await self._notify_user_approval(
                    user, request, game, interaction.user, amp_user_name, instance_name
                )

                await interaction.followup.send(
                    f"✅ Request #{request_id} approved successfully!", ephemeral=True
                )

                self.logger.log_admin_action(
                    interaction.user.id,
                    format_user_info(interaction.user),
                    "Approved request",
                    target_user=request.username,
                    request_id=request_id,
                    game=request.game_name,
                )
            else:
                await interaction.followup.send(
                    f"❌ Failed to process approval for request #{request_id}.",
                    ephemeral=True,
                )

        except Exception as e:
            await interaction.followup.send(
                "❌ An error occurred while processing the approval.", ephemeral=True
            )
            self.logger.error("Failed to approve request", e)

    @app_commands.command(name="deny", description="Deny a game server request")
    @app_commands.describe(
        request_id="The ID of the request to deny",
        reason="The reason for denying the request",
    )
    @app_commands.default_permissions(administrator=True)
    async def deny_request_slash(
        self, interaction: discord.Interaction, request_id: int, reason: str
    ):
        """Deny a request via slash command."""
        try:
            # Get the request
            request = await self.db.get_request_by_id(request_id)
            if not request:
                await interaction.response.send_message(
                    "❌ Request not found.", ephemeral=True
                )
                return

            if request.status != RequestStatus.PENDING:
                await interaction.response.send_message(
                    f"❌ Request already {request.status.value}.", ephemeral=True
                )
                return

            # Update database
            await self.db.update_request_status(
                request_id,
                RequestStatus.REJECTED,
                processed_by=interaction.user.id,
                notes=reason,
            )

            # Get game and user info
            game = get_game_by_name(request.game_name)
            user = self.bot.get_user(request.user_id)

            # Notify the user
            if user:
                try:
                    embed = create_embed(
                        title="❌ Request Denied",
                        description=f"Your request for {request.game_name.title()} has been denied.",
                        color=discord.Color.red(),
                    )

                    embed.add_field(
                        name="Request Details",
                        value=f"**Request ID:** {request_id}\n"
                        f"**Game:** {request.game_name.title()}\n"
                        f"**Status:** Denied",
                        inline=False,
                    )

                    embed.add_field(name="Reason", value=reason, inline=False)

                    embed.add_field(
                        name="What's Next?",
                        value="You can submit a new request if you address the issues mentioned above.",
                        inline=False,
                    )

                    embed.set_footer(text=f"Denied by {interaction.user.display_name}")

                    # Try to notify in the channel
                    channel = self.bot.get_channel(settings.game_request_channel_id)
                    if channel:
                        await channel.send(f"{user.mention}", embed=embed)

                except Exception as e:
                    self.logger.error("Failed to notify user of denial", e)

            await interaction.response.send_message(
                f"✅ Request #{request_id} denied successfully!", ephemeral=True
            )

            self.logger.log_admin_action(
                interaction.user.id,
                format_user_info(interaction.user),
                "Denied request",
                target_user=request.username if request else "Unknown",
                request_id=request_id,
                reason=reason,
            )

        except Exception as e:
            await interaction.response.send_message(
                "❌ An error occurred while processing the denial.", ephemeral=True
            )
            self.logger.error("Failed to deny request", e)

    @app_commands.command(
        name="pending", description="List all pending game server requests"
    )
    @app_commands.default_permissions(administrator=True)
    async def list_pending_slash(self, interaction: discord.Interaction):
        """List pending requests via slash command."""
        try:
            requests = await self.db.get_pending_requests()

            if not requests:
                embed = create_embed(
                    title="No Pending Requests",
                    description="✅ There are no pending requests at this time.",
                    color=discord.Color.green(),
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            embed = create_embed(
                title="Pending Game Server Requests",
                description=f"There are {len(requests)} pending request(s):",
                color=discord.Color.orange(),
            )

            for i, request in enumerate(
                requests[:10]
            ):  # Limit to 10 to avoid embed limits
                game_display = request.game_name.title()

                embed.add_field(
                    name=f"#{request.id} - 🎮 {game_display}",
                    value=f"**User:** {request.username}\n"
                    f"**Submitted:** <t:{int(request.requested_at.timestamp())}:R>",
                    inline=True,
                )

            if len(requests) > 10:
                embed.set_footer(
                    text=f"Showing 10 of {len(requests)} requests. Use /approve or /deny with specific request IDs."
                )
            else:
                embed.set_footer(
                    text=f"Use /approve <id> or /deny <id> <reason> to process requests"
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                "❌ Failed to retrieve pending requests.", ephemeral=True
            )
            self.logger.error("Failed to get pending requests", e)

    @app_commands.command(
        name="request_info",
        description="Get detailed information about a specific request",
    )
    @app_commands.describe(request_id="The ID of the request to view")
    @app_commands.default_permissions(administrator=True)
    async def request_info_slash(
        self, interaction: discord.Interaction, request_id: int
    ):
        """Get detailed request information via slash command."""
        try:
            request = await self.db.get_request_by_id(request_id)

            if not request:
                await interaction.response.send_message(
                    "❌ Request not found.", ephemeral=True
                )
                return

            embed = create_embed(
                title=f"Request #{request_id} Details",
                description=f"Detailed information about this request:",
                color=discord.Color.blue(),
            )

            # Get user info
            user = self.bot.get_user(request.user_id)
            user_info = (
                f"{user.mention} ({user.display_name})" if user else request.username
            )

            embed.add_field(
                name="User Information",
                value=f"**User:** {user_info}\n" f"**User ID:** {request.user_id}",
                inline=False,
            )

            embed.add_field(
                name="Request Information",
                value=f"**Game:** {request.game_name.title()}\n"
                f"**Status:** {request.status.value.title()}\n"
                f"**Submitted:** <t:{int(request.requested_at.timestamp())}:F>",
                inline=False,
            )

            if hasattr(request, "processed_by") and request.processed_by:
                processed_by = self.bot.get_user(request.processed_by)
                processed_info = (
                    processed_by.display_name
                    if processed_by
                    else f"User ID: {request.processed_by}"
                )
                embed.add_field(
                    name="Processing Information",
                    value=f"**Processed By:** {processed_info}\n"
                    f"**Notes:** {getattr(request, 'notes', 'None')}",
                    inline=False,
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                "❌ Failed to retrieve request information.", ephemeral=True
            )
            self.logger.error("Failed to get request info", e)

    @app_commands.command(name="templates", description="Manage AMP template IDs")
    @app_commands.describe(
        action="Action to perform: list, update",
        game_name="Name of the game (for update action)",
        template_id="New template ID (for update action)",
    )
    @app_commands.default_permissions(administrator=True)
    async def manage_templates(
        self,
        interaction: discord.Interaction,
        action: str,
        game_name: str = None,
        template_id: int = None,
    ):
        """Manage AMP template IDs without editing code."""
        try:
            if action.lower() == "list":
                # List all current template mappings
                templates = list_available_templates()

                embed = create_embed(
                    title="📋 AMP Template IDs",
                    description="Current template ID mappings:",
                    color=discord.Color.blue(),
                )

                for game, tid in templates.items():
                    embed.add_field(
                        name=f"🎮 {game.title()}",
                        value=f"Template ID: **{tid}**",
                        inline=True,
                    )

                embed.add_field(
                    name="📝 How to Update",
                    value="Use `/templates update <game_name> <template_id>` to change template IDs",
                    inline=False,
                )

                await interaction.response.send_message(embed=embed, ephemeral=True)

            elif action.lower() == "update":
                if not game_name or template_id is None:
                    await interaction.response.send_message(
                        "❌ For update action, you must provide both game_name and template_id",
                        ephemeral=True,
                    )
                    return

                # Update the template ID
                old_id = get_template_id(game_name)
                update_template_id(game_name, template_id)

                embed = create_embed(
                    title="✅ Template Updated",
                    description=f"Template ID for **{game_name}** updated successfully!",
                    color=discord.Color.green(),
                )

                embed.add_field(
                    name="Changes",
                    value=f"**{game_name.title()}**: {old_id} → **{template_id}**",
                    inline=False,
                )

                embed.add_field(
                    name="⚠️ Note",
                    value="This change is temporary and will reset when the bot restarts.\nTo make it permanent, edit `config/templates.py`",
                    inline=False,
                )

                await interaction.response.send_message(embed=embed, ephemeral=True)

                self.logger.log_admin_action(
                    interaction.user.id,
                    format_user_info(interaction.user),
                    f"Updated template ID for {game_name}",
                    old_value=str(old_id),
                    new_value=str(template_id),
                )

            else:
                await interaction.response.send_message(
                    "❌ Invalid action. Use 'list' or 'update'", ephemeral=True
                )

        except Exception as e:
            await interaction.response.send_message(
                "❌ Failed to manage templates.", ephemeral=True
            )
            self.logger.error("Failed to manage templates", e)


class RejectionModal(discord.ui.Modal):
    """Modal for getting rejection reason."""

    def __init__(
        self, request_id: int, db: DatabaseManager, bot: commands.Bot, logger: BotLogger
    ):
        super().__init__(title="Reject Request")
        self.request_id = request_id
        self.db = db
        self.bot = bot
        self.logger = logger

        self.reason = discord.ui.TextInput(
            label="Rejection Reason",
            placeholder="Enter the reason for rejecting this request...",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=True,
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Get the request
            request = await self.db.get_request(self.request_id)
            if not request:
                await interaction.response.send_message(
                    "❌ Request not found.", ephemeral=True
                )
                return

            # Update database
            await self.db.update_request_status(
                self.request_id,
                RequestStatus.REJECTED,
                processed_by=interaction.user.id,
                notes=self.reason.value,
            )

            # Get game and user info
            game = get_game_by_name(request.game_name)
            user = self.bot.get_user(request.user_id)

            # Update the admin message
            embed = discord.Embed(
                title=f"❌ REJECTED - {game.display_name if game else request.game_name} Request",
                description=f"Request #{request.id} has been rejected",
                color=discord.Color.red(),
                timestamp=interaction.created_at,
            )

            embed.add_field(name="User", value=request.username, inline=True)
            embed.add_field(
                name="Game",
                value=f"{game.icon_emoji if game else '🎮'} {game.display_name if game else request.game_name}",
                inline=True,
            )
            embed.add_field(
                name="Rejected by", value=interaction.user.mention, inline=True
            )
            embed.add_field(name="Reason", value=self.reason.value, inline=False)

            await interaction.response.edit_message(embed=embed, view=None)

            # Notify the user
            if user and game:
                try:
                    request.notes = self.reason.value
                    notify_embed = create_status_update_embed(
                        request, game, False, interaction.user
                    )

                    channel = self.bot.get_channel(settings.game_request_channel_id)
                    if channel:
                        await channel.send(f"{user.mention}", embed=notify_embed)

                except Exception as e:
                    self.logger.error("Failed to notify user of rejection", e)

            self.logger.log_admin_action(
                interaction.user.id,
                format_user_info(interaction.user),
                "Rejected request",
                target_user=request.username,
                request_id=self.request_id,
                reason=self.reason.value,
            )

        except Exception as e:
            await interaction.response.send_message(
                "❌ An error occurred while processing the rejection.", ephemeral=True
            )
            self.logger.error("Failed to process rejection", e)


async def setup(bot: commands.Bot):
    """Set up the cog."""
    await bot.add_cog(AdminCog(bot))
