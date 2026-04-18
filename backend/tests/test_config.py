from pathlib import Path

from app.core.config import ENV_FILE_PATH, PROJECT_ROOT, Settings


def test_settings_env_file_points_to_repo_root():
    assert PROJECT_ROOT.name == "News-intelligence-agent"
    assert ENV_FILE_PATH == PROJECT_ROOT / ".env"
    assert Path(Settings.model_config["env_file"]) == ENV_FILE_PATH
