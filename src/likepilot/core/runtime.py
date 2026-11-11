import threading
import time

from likepilot.core.state import (
    append_agent_log,
    get_agent,
    get_agents,
    get_auto_switch,
    get_provider_login_settings,
    heartbeat_agent,
    update_agent,
)
from likepilot.integrations.networks.facebook import FacebookCommentBot, FacebookFollowBot, FacebookLikeBot
from likepilot.integrations.networks.instagram import InstagramCommentBot, InstagramLikeBot, InstagramLikePostBot
from likepilot.integrations.networks.tiktok import TikTokFollowBot, TikTokLikePostBot
from likepilot.integrations.networks.x import TwitterFavoriteBot, TwitterLikeBot, TwitterRetweetBot
from likepilot.integrations.networks.youtube import YouTubeLikeBot, YouTubeSubscribeBot
from likepilot.integrations.providers.kingdomlikes import (
    KingdomLikesTwitterLikeBot, 
    KingdomLikesTwitterFollowBot, 
    KingdomLikesInstagramLikeBot, 
    KingdomLikesInstagramFollowBot,
    KingdomLikesYouTubeLikeBot,
    KingdomLikesYouTubeSubscribeBot,
    KingdomLikesFacebookLikeBot,
    KingdomLikesFacebookFollowBot,
    KingdomLikesTikTokLikeBot,
    KingdomLikesTikTokFollowBot
)
from likepilot.integrations.providers.youlikehits import (
    YouLikeHitsYouTubeLikeBot,
    YouLikeHitsYouTubeSubscribeBot,
)

PLATFORMS = [
    "Twitter",
    "Twitter Likes",
    "Twitter Retweets",
    "Instagram",
    "Instagram Likes",
    "IG Comments",
    "TikTok",
    "TikTok Likes",
    "YouTube Subs",
    "YouTube Likes",
    "Facebook Subs",
    "Facebook Likes",
    "FB Comments",
]

SITES = ["Like4Like", "KingdomLikes", "YouLikeHits"]

BOT_REGISTRY = {
    "Like4Like": {
        "Twitter": TwitterLikeBot,
        "Twitter Likes": TwitterFavoriteBot,
        "Twitter Retweets": TwitterRetweetBot,
        "Instagram": InstagramLikeBot,
        "Instagram Likes": InstagramLikePostBot,
        "IG Comments": InstagramCommentBot,
        "TikTok": TikTokFollowBot,
        "TikTok Likes": TikTokLikePostBot,
        "YouTube Subs": YouTubeSubscribeBot,
        "YouTube Likes": YouTubeLikeBot,
        "Facebook Subs": FacebookFollowBot,
        "Facebook Likes": FacebookLikeBot,
        "FB Comments": FacebookCommentBot,
    },
    "KingdomLikes": {
        "Twitter": KingdomLikesTwitterFollowBot,
        "Twitter Likes": KingdomLikesTwitterLikeBot,
        "Instagram": KingdomLikesInstagramFollowBot,
        "Instagram Likes": KingdomLikesInstagramLikeBot,
        "TikTok": KingdomLikesTikTokFollowBot,
        "TikTok Likes": KingdomLikesTikTokLikeBot,
        "YouTube Subs": KingdomLikesYouTubeSubscribeBot,
        "YouTube Likes": KingdomLikesYouTubeLikeBot,
        "Facebook Subs": KingdomLikesFacebookFollowBot,
        "Facebook Likes": KingdomLikesFacebookLikeBot,
    },
    "YouLikeHits": {
        "YouTube Subs": YouLikeHitsYouTubeSubscribeBot,
        "YouTube Likes": YouLikeHitsYouTubeLikeBot,
    }
}


TASK_URLS = {
    "Like4Like": {
        "Twitter": "https://www.like4like.org/earn-credits.php?feature=twitter",
        "Twitter Likes": "https://www.like4like.org/user/earn-twitter-favorites.php",
        "Twitter Retweets": "https://www.like4like.org/user/earn-twitter-retweet.php",
        "Instagram": "https://www.like4like.org/user/earn-instagram-follow.php",
        "Instagram Likes": "https://www.like4like.org/user/earn-instagram-like.php",
        "IG Comments": "https://www.like4like.org/user/earn-instagram-comment.php",
        "TikTok": "https://www.like4like.org/user/earn-tiktok-follow.php",
        "TikTok Likes": "https://www.like4like.org/user/earn-tiktok-like.php",
        "YouTube Subs": "https://www.like4like.org/user/earn-youtube-subscribe.php",
        "YouTube Likes": "https://www.like4like.org/user/earn-youtube.php",
        "Facebook Subs": "https://www.like4like.org/user/earn-facebook-subscribes.php",
        "Facebook Likes": "https://www.like4like.org/user/earn-facebook.php",
        "FB Comments": "https://www.like4like.org/user/earn-facebook-comments.php",
    },
    "KingdomLikes": {
        "Twitter": "https://kingdomlikes.com/free_points/twitter-followers",
        "Twitter Likes": "https://kingdomlikes.com/free_points/twitter-likes",
        "Instagram": "https://kingdomlikes.com/free_points/instagram-followers",
        "Instagram Likes": "https://kingdomlikes.com/free_points/instagram-likes",
        "TikTok": "https://kingdomlikes.com/free_points/tiktok-followers",
        "TikTok Likes": "https://kingdomlikes.com/free_points/tiktok-likes",
        "YouTube Subs": "https://kingdomlikes.com/free_points/youtube-subscribe",
        "YouTube Likes": "https://kingdomlikes.com/free_points/youtube-likes",
        "Facebook Subs": "https://kingdomlikes.com/free_points/facebook-followers",
        "Facebook Likes": "https://kingdomlikes.com/free_points/facebook-likes",
    },
    "YouLikeHits": {
        "YouTube Subs": "https://www.youlikehits.com/youtube2.php",
        "YouTube Likes": "https://www.youlikehits.com/youtubelikes.php",
    },
}


ACTIVE_STATUSES = {"Awaiting Login", "Login Success", "Awaiting Social Login", "Running", "Paused"}


class AgentRuntime:
    def __init__(self, thread):
        self.thread = thread
        self.bot = None
        self.started_at = time.time()
        self.last_supervised_at = time.time()
        self.restart_after = 0


class AgentSupervisor:
    def __init__(self):
        self.active_agents = {}
        self.cooldowns = {}
        self.monitor_thread = None
        self.monitor_running = False
        self.lock = threading.RLock()

    def start(self):
        with self.lock:
            if self.monitor_running:
                return
            self.monitor_running = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()

    def _monitor_loop(self):
        while self.monitor_running:
            self._reap_dead_threads()
            self._reconcile_agents()
            time.sleep(2)

    def _reap_dead_threads(self):
        with self.lock:
            dead = [name for name, runtime in self.active_agents.items() if not runtime.thread.is_alive()]
            for name in dead:
                self.active_agents.pop(name, None)

    def _reconcile_agents(self):
        for agent in get_agents():
            name = agent["name"]
            status = get_agent(name)
            if not status:
                continue

            should_run = status["status"] in ACTIVE_STATUSES
            runtime = self.active_agents.get(name)

            if should_run and runtime is None:
                cooldown_until = self.cooldowns.get(name, 0)
                if cooldown_until > time.time():
                    continue
                self._start_worker(name)
            elif not should_run and runtime is not None:
                self._stop_worker(name)

    def _start_worker(self, agent_name):
        with self.lock:
            status = get_agent(agent_name)
            if not status or status["status"] not in ACTIVE_STATUSES:
                return
            runtime = self.active_agents.get(agent_name)
            if runtime and runtime.thread.is_alive():
                return
            thread = threading.Thread(target=self._worker, args=(agent_name,), daemon=True)
            self.active_agents[agent_name] = AgentRuntime(thread)
            thread.start()

    def stop_agent(self, agent_name, timeout_seconds=10):
        """Stop an agent and wait for its worker before allowing deletion/restart."""
        if not get_agent(agent_name):
            return False

        update_agent(agent_name, status="Stopped", session_started_at=None)
        append_agent_log(agent_name, "Supervisor requested stop.", level="SYSTEM")

        with self.lock:
            runtime = self.active_agents.get(agent_name)
            if runtime and runtime.bot:
                try:
                    runtime.bot.stop()
                except Exception as exc:
                    append_agent_log(agent_name, f"Browser stop raised an error: {exc}", level="WARNING")

        if runtime and runtime.thread is not threading.current_thread():
            runtime.thread.join(timeout=max(0, timeout_seconds))
            if runtime.thread.is_alive():
                return False

        with self.lock:
            if self.active_agents.get(agent_name) is runtime:
                self.active_agents.pop(agent_name, None)
            self.cooldowns.pop(agent_name, None)
        return True

    def _stop_worker(self, agent_name):
        self.stop_agent(agent_name)

    def pause_agent(self, agent_name):
        runtime = self.active_agents.get(agent_name)
        if runtime and runtime.bot and runtime.bot.is_running:
            append_agent_log(agent_name, "Supervisor requested pause.", level="SYSTEM")
            runtime.bot.pause()
            return True
        append_agent_log(agent_name, "Pause requested, but no active bot session was available to interrupt.", level="WARNING")
        return False

    def _set_runtime_bot(self, agent_name, bot):
        with self.lock:
            runtime = self.active_agents.get(agent_name)
            if runtime:
                runtime.bot = bot
                runtime.last_supervised_at = time.time()

    def _schedule_retry(self, agent_name, seconds):
        with self.lock:
            self.cooldowns[agent_name] = time.time() + seconds
            runtime = self.active_agents.get(agent_name)
            if runtime:
                runtime.restart_after = self.cooldowns[agent_name]

    def _route_bot_to_task_page(self, agent_name, bot, site, platform):
        task_url = TASK_URLS.get(site, {}).get(platform)
        if not task_url:
            return False
        try:
            bot.driver.get(task_url)
            append_agent_log(agent_name, f"Task page loaded for {platform}.", level="SYSTEM")
            return True
        except Exception as exc:
            append_agent_log(
                agent_name,
                f"Failed to open the {platform} task page: {exc}",
                level="WARNING",
            )
            return False

    def _can_reuse_session(self, session_bot, site):
        if not session_bot or not getattr(session_bot, "driver", None):
            return False
        return getattr(session_bot, "SITE_NAME", None) == site

    def _worker(self, agent_name):
        append_agent_log(agent_name, "Supervisor starting agent worker.", level="SYSTEM")

        try:
            while True:
                status = get_agent(agent_name)
                if not status or status["status"] == "Stopped":
                    break

                runtime = self.active_agents.get(agent_name)
                if runtime and runtime.restart_after and time.time() < runtime.restart_after:
                    heartbeat_agent(agent_name, status=status["status"])
                    time.sleep(1)
                    continue

                site = status.get("site", "Like4Like")
                supported_platforms = list(BOT_REGISTRY.get(site, {}))
                platform = self._resolve_supported_platform(site, status.get("platform"))
                if platform and platform != status.get("platform"):
                    append_agent_log(
                        agent_name,
                        f"Stored platform is not supported by {site}; switching to {platform}.",
                        level="WARNING",
                    )
                    update_agent(agent_name, platform=platform, last_error=None)
                    status["platform"] = platform
                bot_cls = BOT_REGISTRY.get(site, {}).get(platform)

                if not bot_cls:
                    append_agent_log(agent_name, f"Unsupported platform: {site} - {platform}", level="ERROR")
                    update_agent(agent_name, status="Stopped", last_error=f"Unsupported platform: {site} - {platform}", session_started_at=None)
                    break

                provider_login = get_provider_login_settings(site)
                username, password = self._resolve_credentials(status)
                bot = bot_cls(
                    username,
                    password,
                    proxy=status.get("proxy"),
                    auto_login=provider_login["enabled"],
                )
                bot.agent_name = agent_name
                runtime = self.active_agents.get(agent_name)
                existing_bot = runtime.bot if runtime else None
                reuse_session = self._can_reuse_session(existing_bot, site)
                resume_session = (
                    reuse_session
                    and existing_bot is not None
                    and not existing_bot.is_running
                    and existing_bot.exit_reason == "paused"
                    and status["status"] == "Running"
                )

                if resume_session:
                    append_agent_log(agent_name, f"Resuming paused {site} browser session for {platform}.", level="SYSTEM")
                    bot.transfer_session_from(existing_bot)
                    self._set_runtime_bot(agent_name, bot)
                    bot.is_running = True
                    bot.exit_reason = None
                    bot.exit_detail = None
                elif reuse_session:
                    append_agent_log(agent_name, f"Reusing active {site} browser session for {platform}.", level="SYSTEM")
                    bot.transfer_session_from(existing_bot)
                    self._set_runtime_bot(agent_name, bot)
                    bot.is_running = True
                    bot.exit_reason = None
                    bot.exit_detail = None
                    self._route_bot_to_task_page(agent_name, bot, site, platform)
                else:
                    self._set_runtime_bot(agent_name, bot)
                    append_agent_log(agent_name, f"Launching {site} - {platform} session.", level="SYSTEM")
                    bot.start(profile_name=status["chrome_profile"])
                    heartbeat_agent(agent_name, status=status["status"])

                while True:
                    current = get_agent(agent_name)
                    if not current or current["status"] not in {"Awaiting Login", "Login Success"}:
                        break
                    if not bot.is_running:
                        raise RuntimeError("Browser stopped before READY signal.")
                    try:
                        _ = bot.driver.window_handles
                    except Exception:
                        bot.is_running = False
                        raise RuntimeError("Browser window was closed during setup.")
                    if current["status"] == "Awaiting Login" and bot.detect_ready_state():
                        bot.update_credits()
                        update_agent(agent_name, status="Login Success")
                        append_agent_log(
                            agent_name,
                            "Login detected. Session is ready. Press Initialize or READY to open the task page and begin automation.",
                            level="SYSTEM",
                        )
                    latest = get_agent(agent_name)
                    heartbeat_agent(agent_name, status=latest["status"] if latest else current["status"])
                    time.sleep(1)

                current = get_agent(agent_name)
                if not current or current["status"] == "Stopped":
                    break
                if current["status"] == "Paused":
                    append_agent_log(agent_name, "Agent paused before task execution. Waiting for resume.", level="SYSTEM")
                    heartbeat_agent(agent_name, status="Paused")
                    while True:
                        time.sleep(1)
                        current = get_agent(agent_name)
                        if not current or current["status"] == "Stopped":
                            break
                        if current["status"] == "Running":
                            append_agent_log(agent_name, "Resuming paused agent.", level="SYSTEM")
                            heartbeat_agent(agent_name, status="Running")
                            break
                    if not current or current["status"] != "Running":
                        break

                append_agent_log(agent_name, f"{platform} automation started.", level="INFO")
                heartbeat_agent(agent_name, status="Running")
                bot.run()
                refreshed = get_agent(agent_name)
                if refreshed:
                    heartbeat_agent(agent_name, status=refreshed["status"])

                current = get_agent(agent_name)
                if not current or current["status"] == "Stopped":
                    break

                if current["status"] == "Paused":
                    append_agent_log(agent_name, "Agent paused. Waiting for resume.", level="SYSTEM")
                    heartbeat_agent(agent_name, status="Paused")
                    while True:
                        time.sleep(1)
                        current = get_agent(agent_name)
                        if not current or current["status"] == "Stopped":
                            break
                        if current["status"] == "Running":
                            append_agent_log(agent_name, "Resuming paused agent.", level="SYSTEM")
                            heartbeat_agent(agent_name, status="Running")
                            break
                    if not current or current["status"] != "Running":
                        break
                    continue

                if bot.exit_reason == "exhausted":
                    resolution = self._resolve_exhaustion(agent_name, current, platform, bot.exit_detail)
                    next_state = get_agent(agent_name)
                    if next_state and resolution != "manual" and next_state.get("site", site) == site:
                        append_agent_log(agent_name, "Keeping the current browser session open for the next task page.", level="SYSTEM")
                    else:
                        bot.stop()
                        self._set_runtime_bot(agent_name, None)
                    if resolution == "manual":
                        break
                    continue

                if bot.exit_reason == "platform_changed":
                    next_state = get_agent(agent_name)
                    if next_state and next_state.get("site", site) == site:
                        append_agent_log(
                            agent_name,
                            f"{bot.exit_detail or 'Platform changed.'} Reusing the current browser session for the next task page.",
                            level="SYSTEM",
                        )
                        continue
                    bot.stop()
                    self._set_runtime_bot(agent_name, None)
                    continue

                if get_auto_switch():
                    next_platform = self._next_platform(platform, supported_platforms)
                    update_agent(agent_name, platform=next_platform, switch_pending=0, switch_reason=None)
                    append_agent_log(agent_name, f"Switching to {next_platform}.", level="SYSTEM")
                    next_state = get_agent(agent_name)
                    if next_state and next_state.get("site", site) == site:
                        append_agent_log(agent_name, "Keeping the current browser session open for the next task page.", level="SYSTEM")
                        continue
                else:
                    append_agent_log(agent_name, f"{platform} run cycle ended. Cooling down for 60s.", level="INFO")
                    self._schedule_retry(agent_name, 60)
                    time.sleep(2)

                bot.stop()
                self._set_runtime_bot(agent_name, None)

        except Exception as exc:
            append_agent_log(agent_name, f"Worker failure: {exc}", level="CRITICAL")
            update_agent(agent_name, last_error=str(exc))
            current = get_agent(agent_name)
            if current and current["status"] != "Stopped":
                append_agent_log(agent_name, "Retry scheduled in 30s.", level="SYSTEM")
                self._schedule_retry(agent_name, 30)
        finally:
            runtime = self.active_agents.get(agent_name)
            if runtime and runtime.bot:
                runtime.bot.stop()
            self._set_runtime_bot(agent_name, None)

    def _resolve_credentials(self, agent_status):
        site = agent_status.get("site", "Like4Like")
        settings = get_provider_login_settings(site)
        return settings["username"] or None, settings["password"] or None

    @staticmethod
    def _resolve_supported_platform(site, current_platform):
        supported = list(BOT_REGISTRY.get(site, {}))
        if current_platform in supported:
            return current_platform
        return supported[0] if supported else None

    def _next_platform(self, current_platform, supported_platforms=None):
        platforms = list(supported_platforms or PLATFORMS)
        if not platforms:
            return current_platform
        try:
            idx = platforms.index(current_platform)
        except ValueError:
            return platforms[0]
        return platforms[(idx + 1) % len(platforms)]

    def _next_from_chain(self, current_platform, fallback_chain, supported_platforms=None):
        chain = [item.strip() for item in (fallback_chain or "").split(",") if item.strip()]
        supported = set(supported_platforms or PLATFORMS)
        valid_chain = [item for item in chain if item in supported]
        if not valid_chain:
            return None
        if current_platform in valid_chain:
            index = valid_chain.index(current_platform)
            if index + 1 < len(valid_chain):
                return valid_chain[index + 1]
        for platform in valid_chain:
            if platform != current_platform:
                return platform
        return None

    def _resolve_exhaustion(self, agent_name, current, platform, detail):
        supported_platforms = list(BOT_REGISTRY.get(current.get("site", "Like4Like"), {}))
        chain_platform = self._next_from_chain(platform, current.get("fallback_chain"), supported_platforms)
        if chain_platform:
            update_agent(
                agent_name,
                platform=chain_platform,
                status="Running",
                switch_pending=0,
                switch_reason=None,
            )
            append_agent_log(agent_name, detail or f"{platform} exhausted. Switching by chain to {chain_platform}.", level="SYSTEM")
            return "chain"

        fallback_platform = current.get("fallback_platform")
        if fallback_platform and fallback_platform != platform and fallback_platform in supported_platforms:
            update_agent(
                agent_name,
                platform=fallback_platform,
                status="Running",
                switch_pending=0,
                switch_reason=None,
            )
            append_agent_log(agent_name, detail or f"{platform} exhausted. Switching to configured fallback {fallback_platform}.", level="fallback")
            return "fallback"

        if get_auto_switch():
            next_platform = self._next_platform(platform, supported_platforms)
            update_agent(
                agent_name,
                platform=next_platform,
                status="Running",
                switch_pending=0,
                switch_reason=None,
            )
            append_agent_log(agent_name, detail or f"{platform} exhausted. Auto-rotating to {next_platform}.", level="SYSTEM")
            return "auto"

        update_agent(
            agent_name,
            status="Awaiting Switch",
            switch_pending=1,
            switch_reason=detail or f"{platform} exhausted. Choose the next platform.",
        )
        append_agent_log(agent_name, detail or f"{platform} exhausted. Waiting for operator platform choice.", level="INFO")
        return "manual"


supervisor = AgentSupervisor()
