from likepilot.core.auto_updater import AutoUpdater


def test_updater_installation_is_disabled_without_downloading(tmp_path, monkeypatch):
    updater = AutoUpdater()
    updater.update_available = True
    updater.latest_version = "9.9.9"
    updater.release_info = {
        "assets": [{
            "name": "likepilot-release.zip",
            "browser_download_url": "https://example.invalid/likepilot-release.zip",
        }]
    }

    def unexpected_download(*args, **kwargs):
        raise AssertionError("disabled updater must not download or execute packages")

    monkeypatch.setattr("likepilot.core.auto_updater.requests.get", unexpected_download)
    assert updater.install_update() is False
    assert not (tmp_path / "update.zip").exists()
