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
