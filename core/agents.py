from core.state import add_agent, get_agents, remove_agent


def init_agents():
    # Agent initialization is handled by the database bootstrap in core.state.
    return None


def save_agents(_agents):
    # The runtime no longer persists agents through a flat JSON file.
    return None
