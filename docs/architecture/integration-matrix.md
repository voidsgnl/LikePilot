# Provider / network / action integration matrix

This document describes the combinations the runtime actually routes. A combination is considered **registered** only when it has both a concrete bot class in `BOT_REGISTRY` and a task-page URL in `TASK_URLS`. A class existing in a source file by itself does not make it selectable by an agent.

## Runtime route

1. An agent stores a provider (`site`) and task family (`platform`).
2. `AgentSupervisor._worker()` resolves that pair through `BOT_REGISTRY[site][platform]`.
3. `AgentSupervisor._route_bot_to_task_page()` uses the matching `TASK_URLS[site][platform]` when initializing or handing off a session.
4. The selected adapter runs the provider task flow and performs its platform-specific social action.
5. The adapter submits the provider confirmation and polls for a credit increase. The shared provider base only permits task-window closure when credit collection is explicitly confirmed.

The route registry and URL map must remain key-for-key identical. Unsupported pairs are not silently substituted; the runtime logs an unsupported platform and stops that agent.

## Registered combinations

| Provider | Agent task label | Social network | Action | Runtime adapter |
|---|---|---|---|---|
| Like4Like | Twitter | X (Twitter) | Follow | `TwitterLikeBot` |
| Like4Like | Twitter Likes | X (Twitter) | Like | `TwitterFavoriteBot` |
| Like4Like | Twitter Retweets | X (Twitter) | Repost/retweet | `TwitterRetweetBot` |
| Like4Like | Instagram | Instagram | Follow | `InstagramLikeBot` |
| Like4Like | Instagram Likes | Instagram | Like | `InstagramLikePostBot` |
| Like4Like | IG Comments | Instagram | Comment | `InstagramCommentBot` |
| Like4Like | TikTok | TikTok | Follow | `TikTokFollowBot` |
| Like4Like | TikTok Likes | TikTok | Like | `TikTokLikePostBot` |
| Like4Like | YouTube Subs | YouTube | Subscribe | `YouTubeSubscribeBot` |
| Like4Like | YouTube Likes | YouTube | Like | `YouTubeLikeBot` |
| Like4Like | Facebook Subs | Facebook | Follow | `FacebookFollowBot` |
| Like4Like | Facebook Likes | Facebook | Like | `FacebookLikeBot` |
| Like4Like | FB Comments | Facebook | Comment | `FacebookCommentBot` |
| KingdomLikes | Twitter | X (Twitter) | Follow | `KingdomLikesTwitterFollowBot` |
| KingdomLikes | Twitter Likes | X (Twitter) | Like | `KingdomLikesTwitterLikeBot` |
| KingdomLikes | Instagram | Instagram | Follow | `KingdomLikesInstagramFollowBot` |
| KingdomLikes | Instagram Likes | Instagram | Like | `KingdomLikesInstagramLikeBot` |
| KingdomLikes | TikTok | TikTok | Follow | `KingdomLikesTikTokFollowBot` |
| KingdomLikes | TikTok Likes | TikTok | Like | `KingdomLikesTikTokLikeBot` |
| KingdomLikes | YouTube Subs | YouTube | Subscribe | `KingdomLikesYouTubeSubscribeBot` |
| KingdomLikes | YouTube Likes | YouTube | Like | `KingdomLikesYouTubeLikeBot` |
| KingdomLikes | Facebook Subs | Facebook | Follow | `KingdomLikesFacebookFollowBot` |
| KingdomLikes | Facebook Likes | Facebook | Like | `KingdomLikesFacebookLikeBot` |
| YouLikeHits | YouTube Subs | YouTube | Subscribe | `YouLikeHitsYouTubeSubscribeBot` |
| YouLikeHits | YouTube Likes | YouTube | Like | `YouLikeHitsYouTubeLikeBot` |

**Current count:** 25 registered provider/task combinations: 13 Like4Like, 10 KingdomLikes, and 2 YouLikeHits.

## Important distinctions and gaps

- Agent task labels are legacy product-facing names, not always literal action names. For example, `Twitter` means the X/Twitter follow task; `Twitter Likes` is the like task.
- The network modules under `integrations/networks/` implement Like4Like-specific flows. KingdomLikes and YouLikeHits have provider-specific classes in their respective provider modules. The shared provider base supplies common browser, login, credit, logging, and task-window lifecycle behavior; it does not imply that every provider supports every network action.
- YouLikeHits also contains a YouTube Subscribe adapter. It previously was not present in the runtime registry or task URL map, so an agent could not select it. It is now registered under `YouTube Subs` and routed to its declared `TARGET_URL`.
- No YouLikeHits routes are currently registered for Facebook, Instagram, TikTok, or X/Twitter.
- KingdomLikes has no registered comment task routes.
- Like4Like and KingdomLikes expose the same ten common follow/like/subscribe task families, while Like4Like additionally exposes X retweets and Facebook/Instagram comments.
- A registered route is evidence of code/configuration wiring, not proof that a third-party site's current selectors, authentication, or live reward confirmation still work. Live provider/browser verification remains a separate acceptance step.

## Regression guard

`tests/test_integration_registry.py` asserts that each provider has a non-empty registry, every registered provider/task pair has a task URL, every provider/task URL pair has a bot class, and the YouLikeHits YouTube Subscribe route points to the adapter's own target URL. Update this matrix and the test whenever a route is added, removed, or renamed.
