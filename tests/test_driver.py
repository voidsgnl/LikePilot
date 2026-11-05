from likepilot.core.driver import inject_stealth


class FakeFirefoxDriver:
    capabilities = {"browserName": "firefox"}

    def execute_cdp_cmd(self, *_args, **_kwargs):
        raise AssertionError("Firefox must not receive Chrome CDP commands")


class FakeChromeDriver:
    capabilities = {"browserName": "chrome"}

    def __init__(self):
        self.commands = []

    def execute_cdp_cmd(self, command, params):
        self.commands.append((command, params))


def test_firefox_skips_chrome_cdp_stealth():
    inject_stealth(FakeFirefoxDriver())


def test_chrome_keeps_existing_cdp_stealth():
    driver = FakeChromeDriver()

    inject_stealth(driver)

    assert len(driver.commands) == 1
    assert driver.commands[0][0] == "Page.addScriptToEvaluateOnNewDocument"
