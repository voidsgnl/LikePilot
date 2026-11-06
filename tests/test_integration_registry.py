from likepilot.core.runtime import BOT_REGISTRY, SITES, TASK_URLS
from likepilot.integrations.providers.youlikehits import YouLikeHitsYouTubeSubscribeBot


def test_every_registered_provider_action_has_a_task_url():
    assert set(BOT_REGISTRY) == set(SITES)
    assert set(TASK_URLS) == set(SITES)

    for provider in SITES:
        assert BOT_REGISTRY[provider]
        assert set(BOT_REGISTRY[provider]) == set(TASK_URLS[provider])
        assert all(callable(getattr(bot_class, "run", None)) for bot_class in BOT_REGISTRY[provider].values())


def test_youlikehits_youtube_subscribe_route_is_registered():
    assert BOT_REGISTRY["YouLikeHits"]["YouTube Subs"] is YouLikeHitsYouTubeSubscribeBot
    assert TASK_URLS["YouLikeHits"]["YouTube Subs"] == YouLikeHitsYouTubeSubscribeBot.TARGET_URL
