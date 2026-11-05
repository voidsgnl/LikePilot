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


def test_dashboard_navigation_omits_static_catalog_pages():
    layout = (DASHBOARD / "templates" / "layout.html").read_text(encoding="utf-8")
    assert 'href="/providers"' not in layout
    assert 'href="/platforms"' not in layout


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
    assert "Agent snapshot" in template


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
    assert 'id="agent-quick-switch"' in layout
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
    assert "Summary of recorded credit snapshots." in template
