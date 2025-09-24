import discord
from datetime import datetime
from typing import List, Optional
from config.games import GameTemplate, get_games_list
from models import GameRequest, RequestStatus


def create_embed(
    title: str = None,
    description: str = None,
    color: discord.Color = discord.Color.blue(),
    timestamp: datetime = None,
) -> discord.Embed:
    """Create a basic discord embed with common parameters."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=timestamp or datetime.utcnow(),
    )
    return embed


def create_game_selection_embed() -> discord.Embed:
    """Create the main game selection embed."""
    embed = discord.Embed(
        title="🎮 Game Server Request",
        description="Select a game to request a server for:",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow(),
    )

    games = get_games_list()
    for game in games:
        embed.add_field(
            name=f"{game.icon_emoji} {game.display_name}",
            value=game.description,
            inline=True,
        )

    embed.set_footer(text="Click a button below to request a server")
    return embed


def create_game_selection_view() -> discord.ui.View:
    """Create the view with buttons for game selection."""
    view = discord.ui.View(timeout=None)  # Persistent view

    games = get_games_list()
    for game in games:
        button = discord.ui.Button(
            label=game.display_name,
            emoji=game.icon_emoji,
            custom_id=f"game_request_{game.name}",
            style=discord.ButtonStyle.secondary,
        )
        view.add_item(button)

    return view


def create_request_confirmation_embed(
    game: GameTemplate, user: discord.Member
) -> discord.Embed:
    """Create confirmation embed for game request."""
    embed = discord.Embed(
        title=f"{game.icon_emoji} {game.display_name} Server Request",
        description=f"Your request for a {game.display_name} server has been submitted!",
        color=discord.Color.green(),
        timestamp=datetime.utcnow(),
    )

    embed.add_field(name="Game", value=game.display_name, inline=True)
    embed.add_field(name="Status", value="⏳ Pending Admin Approval", inline=True)
    embed.add_field(name="Requested by", value=user.mention, inline=True)

    if game.requirements:
        req_text = "\n".join([f"• {k}: {v}" for k, v in game.requirements.items()])
        embed.add_field(name="Server Requirements", value=req_text, inline=False)

    embed.set_footer(text="You will be notified when an admin processes your request")
    return embed


def create_admin_approval_embed(
    request: GameRequest, game: GameTemplate, user: discord.Member
) -> discord.Embed:
    """Create admin approval embed."""
    embed = discord.Embed(
        title=f"🔔 New Server Request - {game.display_name}",
        description="A user has requested a new game server",
        color=discord.Color.orange(),
        timestamp=datetime.utcnow(),
    )

    embed.add_field(
        name="User", value=f"{user.mention} ({user.display_name})", inline=True
    )
    embed.add_field(
        name="Game", value=f"{game.icon_emoji} {game.display_name}", inline=True
    )
    embed.add_field(name="Request ID", value=str(request.id), inline=True)

    embed.add_field(
        name="User Info",
        value=f"ID: {user.id}\nJoined: {getattr(user, 'joined_at', 'N/A').strftime('%Y-%m-%d') if hasattr(user, 'joined_at') and user.joined_at else 'N/A'}",
        inline=True,
    )
    embed.add_field(
        name="Account Created", value=user.created_at.strftime("%Y-%m-%d"), inline=True
    )
    embed.add_field(
        name="Roles",
        value=(
            ", ".join([role.name for role in user.roles[1:]])
            if hasattr(user, "roles") and user.roles
            else "None"
        ),
        inline=True,
    )

    if game.requirements:
        req_text = "\n".join([f"• {k}: {v}" for k, v in game.requirements.items()])
        embed.add_field(name="Server Requirements", value=req_text, inline=False)

    embed.set_footer(
        text=f"Request submitted at {request.requested_at.strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )
    return embed


def create_admin_approval_view(request_id: int) -> discord.ui.View:
    """Create admin approval view with buttons."""
    import logging

    logger = logging.getLogger("discord.bot")

    view = discord.ui.View(timeout=None)
    logger.debug(f"Creating approval view for request {request_id}")

    approve_button = discord.ui.Button(
        label="Approve",
        emoji="✅",
        custom_id=f"approve_request_{request_id}",
        style=discord.ButtonStyle.success,
    )
    logger.debug(f"Created approve button with ID: {approve_button.custom_id}")

    reject_button = discord.ui.Button(
        label="Reject",
        emoji="❌",
        custom_id=f"reject_request_{request_id}",
        style=discord.ButtonStyle.danger,
    )
    logger.debug(f"Created reject button with ID: {reject_button.custom_id}")

    view.add_item(approve_button)
    view.add_item(reject_button)

    logger.debug(f"View has {len(view.children)} children after adding buttons")
    return view


def create_status_update_embed(
    request: GameRequest,
    game: GameTemplate,
    approved: bool,
    admin: discord.Member,
    amp_user: Optional[str] = None,
    instance: Optional[str] = None,
) -> discord.Embed:
    """Create status update embed for the user."""
    if approved:
        embed = discord.Embed(
            title=f"✅ Request Approved - {game.display_name}",
            description=f"Your {game.display_name} server request has been approved!",
            color=discord.Color.green(),
            timestamp=datetime.utcnow(),
        )

        embed.add_field(
            name="Game", value=f"{game.icon_emoji} {game.display_name}", inline=True
        )
        embed.add_field(name="Approved by", value=admin.mention, inline=True)
        embed.add_field(name="Request ID", value=str(request.id), inline=True)

        if amp_user:
            embed.add_field(name="AMP Username", value=f"`{amp_user}`", inline=False)

        if instance:
            embed.add_field(name="Server Instance", value=f"`{instance}`", inline=False)

        embed.add_field(
            name="Next Steps",
            value="• Check your DMs for AMP login credentials\n• Server setup may take a few minutes\n• Contact an admin if you need help",
            inline=False,
        )

    else:
        embed = discord.Embed(
            title=f"❌ Request Rejected - {game.display_name}",
            description=f"Your {game.display_name} server request has been rejected.",
            color=discord.Color.red(),
            timestamp=datetime.utcnow(),
        )

        embed.add_field(
            name="Game", value=f"{game.icon_emoji} {game.display_name}", inline=True
        )
        embed.add_field(name="Rejected by", value=admin.mention, inline=True)
        embed.add_field(name="Request ID", value=str(request.id), inline=True)

        if request.notes:
            embed.add_field(name="Reason", value=request.notes, inline=False)

        embed.add_field(
            name="What's Next?",
            value="You can submit a new request anytime or contact an admin for more information.",
            inline=False,
        )

    embed.set_footer(
        text=f"Processed at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )
    return embed


def format_user_info(user: discord.Member) -> str:
    """Format user information for logging."""
    return f"{user.display_name} ({user.name}#{user.discriminator}) [ID: {user.id}]"


def format_request_summary(request: GameRequest, game: GameTemplate) -> str:
    """Format request summary for logging."""
    return f"Request #{request.id}: {game.display_name} for {request.username} ({request.status.value})"


def truncate_text(text: str, max_length: int = 1024) -> str:
    """Truncate text to fit Discord embed limits."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
