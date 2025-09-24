"""
AMP Template Configuration

This file contains the mapping between game names and AMP template IDs.
Update the template IDs to match your AMP panel's template IDs.

To find your template IDs:
1. Go to your AMP web interface
2. Navigate to ADS (Application Deployment Service)
3. Look at "Create New Instance" or "Templates" section
4. Check the URL or browser dev tools to see the template IDs

Example: If your Minecraft template shows "TemplateID=5" in the URL,
change "minecraft": 1 to "minecraft": 5 below.
"""

# Template ID Mapping - UPDATE ONLY THIS FILE TO CHANGE TEMPLATE IDs
# ================================================================
# This is the SINGLE SOURCE OF TRUTH for AMP template IDs
# To add a new game:
# 1. Add the entry here: "game_name": template_id_number
# 2. Add the game to AVAILABLE_GAMES in games.py with template_id="game_name"
# ================================================================
TEMPLATE_IDS = {
    # Game Name: Template ID (number from your AMP panel)
    "minecraft": 1,  # Minecraft Java Edition template ID
    "ark": 3,  # ARK: Survival Evolved template ID
    "cs2": 5,  # Counter Strike 2 template ID
    "gmod": 4,  # Garry's Mod template ID
    # Add more games here as needed:
    # "rust": 6,            # Rust template ID
    # "csgo": 7,            # CS:GO template ID
    # "palworld": 8,        # Palworld template ID
}

# Default template ID if game is not found in mapping above
DEFAULT_TEMPLATE_ID = 1  # Usually Minecraft


def get_template_id(game_name: str) -> int:
    """
    Get the template ID for a given game name.

    Args:
        game_name: The name of the game (e.g., "minecraft", "palworld")

    Returns:
        The template ID number for the game, or default if not found
    """
    return TEMPLATE_IDS.get(game_name.lower(), DEFAULT_TEMPLATE_ID)


def list_available_templates() -> dict:
    """
    Get all available template mappings.

    Returns:
        Dictionary of all game name -> template ID mappings
    """
    return TEMPLATE_IDS.copy()


def add_template(game_name: str, template_id: int):
    """
    Add a new template mapping (runtime addition).

    Args:
        game_name: Name of the game
        template_id: Template ID from AMP panel
    """
    TEMPLATE_IDS[game_name.lower()] = template_id


def update_template_id(game_name: str, template_id: int):
    """
    Update an existing template ID.

    Args:
        game_name: Name of the game to update
        template_id: New template ID from AMP panel
    """
    TEMPLATE_IDS[game_name.lower()] = template_id
