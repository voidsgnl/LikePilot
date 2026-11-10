import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "src" / "likepilot" / "dashboard"


def _dashboard_routes():
    source = (DASHBOARD / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    routes = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if not isinstance(decorator.func, ast.Attribute) or decorator.func.attr != "route":
                continue
            if decorator.args and isinstance(decorator.args[0], ast.Constant):
                routes.setdefault(decorator.args[0].value, set()).add(node.name)
    return routes


def test_dashboard_has_dedicated_workspace_routes():
    routes = _dashboard_routes()
    expected = {
        "/dashboard",
        "/agents",
        "/agents/<path:agent_name>",
        "/providers",
        "/platforms",
        "/analytics",
        "/analytics/<analytics_view>",
        "/settings/browser",
        "/settings/providers",
        "/api/settings/providers",
        "/settings/agents/new",
        "/settings/agents/manage",
        "/operations/<operation_view>",
    }
    assert expected.issubset(routes)


def test_dedicated_workspace_templates_exist():
    templates = DASHBOARD / "templates"
    expected = {
        "dashboard.html",
        "agents.html",
        "agent_detail.html",
        "providers.html",
        "platforms.html",
        "analytics.html",
        "settings_browser.html",
        "settings_providers.html",
        "settings_create_agent.html",
        "settings_manage_agents.html",
        "operations.html",
    }
    assert expected.issubset({path.name for path in templates.glob("*.html")})


def test_analytics_does_not_present_fabricated_telemetry():
    analytics_template = (DASHBOARD / "templates" / "analytics.html").read_text(encoding="utf-8")
    analytics_script = (DASHBOARD / "static" / "analytics.js").read_text(encoding="utf-8")

    assert "45% higher success rate" not in analytics_template
    assert "87%" not in analytics_template
    assert "Math.random()" not in analytics_script


def test_workspace_navigation_exposes_all_primary_destinations():
    layout = (DASHBOARD / "templates" / "layout.html").read_text(encoding="utf-8")
    for path in ("/dashboard", "/agents", "/analytics", "/settings/browser", "/platforms"):
        assert f'href="{path}"' in layout
    assert "url_for('provider_settings')" in layout
    assert "url_for('operations', operation_view=key)" in layout
    assert layout.count('class="pill-link') == 4
    assert 'class="pill-nav"' in layout
    assert 'class="primary-nav"' not in layout
    assert 'class="topbar"' in layout
    assert 'class="icon-rail"' not in layout
    assert 'id="sidebar"' not in layout
    assert 'class="context-nav"' in layout


def test_chart_library_is_loaded_only_on_analytics():
    layout = (DASHBOARD / "templates" / "layout.html").read_text(encoding="utf-8")
    analytics = (DASHBOARD / "templates" / "analytics.html").read_text(encoding="utf-8")
    assert "cdn.jsdelivr.net/npm/chart.js" not in layout
    assert "cdn.jsdelivr.net/npm/chart.js" in analytics


def test_agent_directory_uses_compact_inventory_columns():
    template = (DASHBOARD / "templates" / "agents.html").read_text(encoding="utf-8")
    script = (DASHBOARD / "static" / "agents-directory.js").read_text(encoding="utf-8")
    assert "Session gain" not in template
    assert "Last heartbeat" not in template
    assert "directory-total" not in script


def test_agent_workspace_keeps_only_operational_metrics():
    template = (DASHBOARD / "templates" / "agent_detail.html").read_text(encoding="utf-8")
    script = (DASHBOARD / "static" / "agent-detail.js").read_text(encoding="utf-8")

    assert 'id="agent-credits"' in template
    assert 'id="agent-gain"' in template
    assert 'id="agent-platform-select" aria-label="Select platform" hidden' in template
    assert 'id="agent-confirm-platform" hidden' in template
    assert 'id="agent-peak"' not in template
    assert 'id="agent-samples"' not in template
    assert "actionAvailability" in script
    assert "ready: agent.status === 'Awaiting Login'" in script
    assert "initialize: agent.status === 'Login Success'" in script
    assert "Awaiting Social Login" in script
    assert "Sign in to the social platform in the open browser window" in script


def test_agent_workspace_separates_runtime_details_from_configuration():
    template = (DASHBOARD / "templates" / "agent_detail.html").read_text(encoding="utf-8")

    assert 'id="agent-heartbeat"' in template
    assert 'id="agent-session-start"' in template
    assert 'href="/settings/agents/manage"' in template
    assert "Manage saved agents" in template


def test_overview_update_indicator_has_a_matching_template_element():
    template = (DASHBOARD / "templates" / "dashboard.html").read_text(encoding="utf-8")
    script = (DASHBOARD / "static" / "overview.js").read_text(encoding="utf-8")

    assert 'id="overview-updated"' in template
    assert "getElementById('overview-updated')" in script
    assert "Recent activity" in template
    assert "Open agent workspace" in template


def test_agent_directory_uses_one_contextual_empty_state():
    template = (DASHBOARD / "templates" / "agents.html").read_text(encoding="utf-8")
    script = (DASHBOARD / "static" / "agents-directory.js").read_text(encoding="utf-8")

    assert 'id="directory-empty"' not in template
    assert "No agents configured. Create an agent to get started." in script
    assert "No agents match these filters." in script


def test_global_header_keeps_only_actionable_status_and_navigation():
    layout = (DASHBOARD / "templates" / "layout.html").read_text(encoding="utf-8")
    script = (DASHBOARD / "static" / "dashboard.js").read_text(encoding="utf-8")

    assert 'id="live-updates-pill"' in layout
    assert 'class="top-actions"' in layout
    assert 'id="agent-quick-switch"' not in layout
    assert 'id="session-badge"' not in layout
    assert 'id="clock"' not in layout
    assert "renderSessionBadge" not in script
    assert "updateClock" not in script


def test_analytics_shows_missing_history_without_placeholder_values():
    template = (DASHBOARD / "templates" / "analytics.html").read_text(encoding="utf-8")
    script = (DASHBOARD / "static" / "analytics.js").read_text(encoding="utf-8")

    assert "hasHistory" in script
    assert "hasHistory ? (metrics.latest_credits ?? '—') : '—'" in script
    assert "1250, 1280, 1320" not in script
    assert "initializePredictionChart" not in script
    assert "Captured balance history." in template


def test_login_screen_uses_four_ring_vault():
    template = (DASHBOARD / "templates" / "login.html").read_text(encoding="utf-8")
    styles = (DASHBOARD / "static" / "auth.css").read_text(encoding="utf-8")
    script = (DASHBOARD / "static" / "login.js").read_text(encoding="utf-8")

    assert 'class="vault-orbit"' in template
    assert template.count('class="character-ring"') == 4
    assert 'name="username"' in template
    assert 'name="password"' in template
    assert "character-ring" in script
    assert "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" in script
    assert "vault-orbit" in styles
    assert "pilot-flight.svg" not in template
    assert "brand-mark.svg" in template


def test_dashboard_shell_avoids_redundant_copy_and_loading_motion():
    template = (DASHBOARD / "templates" / "layout.html").read_text(encoding="utf-8")
    styles = (DASHBOARD / "static" / "console-theme.css").read_text(encoding="utf-8")
    overview = (DASHBOARD / "templates" / "dashboard.html").read_text(encoding="utf-8")

    assert 'class="topbar-eyebrow"' not in template
    assert 'class="page-subtitle"' not in template
    assert "Loading agents." not in template
    assert "animation:none!important" in styles
    assert "Loading runtime…" not in overview


def test_database_operations_exposes_schema_only():
    template = (DASHBOARD / "templates" / "operations.html").read_text(encoding="utf-8")
    script = (DASHBOARD / "static" / "operations.js").read_text(encoding="utf-8")
    source = (DASHBOARD / "app.py").read_text(encoding="utf-8")

    assert 'id="ops-db-view-data"' not in template
    assert 'id="ops-db-preview"' not in template
    assert "row_count" not in script
    assert "/api/operations/database/table?" not in script
    assert "/api/operations/database/table" not in source
    assert "SELECT * FROM" not in source
    assert "foreign_key_list" in source
    assert "index_list" in source
    assert "index_info" in source


def test_analytics_and_settings_pages_avoid_repeated_headings():
    analytics = (DASHBOARD / "templates" / "analytics.html").read_text(encoding="utf-8")
    create_agent = (DASHBOARD / "templates" / "settings_create_agent.html").read_text(encoding="utf-8")
    manage_agents = (DASHBOARD / "templates" / "settings_manage_agents.html").read_text(encoding="utf-8")
    browser = (DASHBOARD / "templates" / "settings_browser.html").read_text(encoding="utf-8")

    assert "Historical analysis" not in analytics
    assert "Live stream" not in analytics
    assert "Review the balance line" not in analytics
    assert "Loading analytics." not in analytics
    assert "Provisioning" not in create_agent
    assert "Agent setup" not in create_agent
    assert "Loading configured agents." not in manage_agents
    assert "Configuration inventory" not in manage_agents
    assert "Default browser" not in browser
    assert "Browser used for new sessions" not in browser
    assert "restart running agents" in browser


def test_provider_login_is_system_level_not_agent_level():
    create_agent = (DASHBOARD / "templates" / "settings_create_agent.html").read_text(encoding="utf-8")
    manage_script = (DASHBOARD / "static" / "settings.js").read_text(encoding="utf-8")
    runtime = (ROOT / "src" / "likepilot" / "core" / "runtime.py").read_text(encoding="utf-8")
    provider_template = (DASHBOARD / "templates" / "settings_providers.html").read_text(encoding="utf-8")

    assert "new-agent-login-user" not in create_agent
    assert "new-agent-login-password" not in create_agent
    assert "edit-login-user-" not in manage_script
    assert "edit-login-password-" not in manage_script
    assert "get_provider_login_settings(site)" in runtime
    assert 'auto_login=provider_login["enabled"]' in runtime
    assert 'data-provider-login-enabled' in provider_template
    assert 'data-provider-login-username' in provider_template
    assert 'data-provider-login-password' in provider_template


def test_workspace_navigation_styles_are_cached_for_release():
    import re

    service_worker = (DASHBOARD / "static" / "sw.js").read_text(encoding="utf-8")
    cache_version = re.search(r"const STATIC_CACHE = 'likepilot-static-(v[0-9.]+)'", service_worker)
    assert cache_version
    assert re.search(rf"\b{re.escape(cache_version.group(1))}\b", service_worker)
    assert "'/static/auth.css'" in service_worker
    assert "'/static/login.js'" in service_worker
    assert "'/static/pilot-flight.svg'" not in service_worker
    assert "/favicon/brand-mark.svg" in service_worker
    assert "'/static/workspace-navigation.css'" in service_worker
    assert "'/static/floating-dashboard.css'" in service_worker
