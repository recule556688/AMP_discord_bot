"""
Discord UI Views for the AMP Discord Bot.
"""

import discord
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cogs.admin import AdminCog


class AdminApprovalView(discord.ui.View):
    """View with approve/reject buttons for admin requests."""

    def __init__(self, request_id: int, admin_cog: "AdminCog"):
        super().__init__(timeout=None)
        self.request_id = request_id
        self.admin_cog = admin_cog

    @discord.ui.button(
        label="Approve",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="approve_request",
    )
    async def approve_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Handle approve button clicks."""
        # Modify the interaction data to include the request ID
        interaction.data["custom_id"] = f"approve_request_{self.request_id}"
        await self.admin_cog.approve_request_callback(interaction)

    @discord.ui.button(
        label="Reject",
        emoji="❌",
        style=discord.ButtonStyle.danger,
        custom_id="reject_request",
    )
    async def reject_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Handle reject button clicks."""
        # Modify the interaction data to include the request ID
        interaction.data["custom_id"] = f"reject_request_{self.request_id}"
        await self.admin_cog.reject_request_callback(interaction)


class PersistentAdminApprovalView(discord.ui.View):
    """Persistent view that survives bot restarts."""

    def __init__(self, request_id: int):
        super().__init__(timeout=None)
        self.request_id = request_id

        # Create buttons with unique custom IDs
        approve_button = discord.ui.Button(
            label="Approve",
            emoji="✅",
            custom_id=f"approve_request_{request_id}",
            style=discord.ButtonStyle.success,
        )

        reject_button = discord.ui.Button(
            label="Reject",
            emoji="❌",
            custom_id=f"reject_request_{request_id}",
            style=discord.ButtonStyle.danger,
        )

        # Add buttons to view
        self.add_item(approve_button)
        self.add_item(reject_button)

    def set_callbacks(self, admin_cog):
        """Set the callbacks after the admin cog is available."""
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                if item.custom_id.startswith("approve_request_"):
                    item.callback = admin_cog.approve_request_callback
                elif item.custom_id.startswith("reject_request_"):
                    item.callback = admin_cog.reject_request_callback
