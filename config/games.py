from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class GameTemplate:
    """Configuration for a game template in AMP."""

    name: str
    display_name: str
    description: str
    template_id: str
    default_role: str
    icon_emoji: str
    requirements: Optional[Dict[str, str]] = None


@dataclass
class ServerTemplate:
    """Configuration for server creation."""

    name: str
    memory_mb: int = 2048
    java_version: str = "17"
    auto_start: bool = True


# Available games configuration
# Note: template_id values must match keys in templates.py TEMPLATE_IDS
# To change AMP template IDs, edit templates.py, not this file!
AVAILABLE_GAMES: List[GameTemplate] = [
    GameTemplate(
        name="minecraft",
        display_name="Minecraft",
        description="Create a Minecraft server",
        template_id="minecraft",  # References templates.py key
        default_role="minecraft_admin",
        icon_emoji="🟫",
        requirements={"min_memory": "2048", "java_version": "17"},
    ),
    GameTemplate(
        name="ark",
        display_name="ARK: Survival Evolved",
        description="Create an ARK server",
        template_id="ark",  # References templates.py key
        default_role="ark_admin",
        icon_emoji="🦕",
        requirements={"min_memory": "8192"},
    ),
    GameTemplate(
        name="cs2",
        display_name="Counter-Strike 2",
        description="Create a CS2 server",
        template_id="cs2",  # References templates.py key
        default_role="cs2_admin",
        icon_emoji="🔫",
        requirements={"min_memory": "8192"},
    ),
    GameTemplate(
        name="gmod",
        display_name="Garry's Mod",
        description="Create a Garry's Mod server",
        template_id="gmod",  # References templates.py key
        default_role="gmod_admin",
        icon_emoji="🔧",
        requirements={"min_memory": "4096"},
    ),
]

# Server templates by game
SERVER_TEMPLATES: Dict[str, ServerTemplate] = {
    "minecraft": ServerTemplate("Minecraft Server", 2048, "17"),
    "ark": ServerTemplate("ARK Server", 8192),
    "cs2": ServerTemplate("CS2 Server", 8192),
    "gmod": ServerTemplate("Garry's Mod Server", 4096),
}


def get_game_by_name(name: str) -> Optional[GameTemplate]:
    """Get game template by name."""
    return next((game for game in AVAILABLE_GAMES if game.name == name), None)


def get_games_list() -> List[GameTemplate]:
    """Get list of all available games."""
    return AVAILABLE_GAMES.copy()
