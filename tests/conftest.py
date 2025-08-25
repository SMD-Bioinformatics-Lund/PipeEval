import textwrap
from pathlib import Path

import pytest

from tests.conftest_utils.run_configs import (
    ConfigSamplePaths,
    get_profile_config,
    get_sample_config,
    get_pipeline_config,
    test_import,
)


@pytest.fixture()
def base_dir(tmp_path: Path) -> Path:
    base_dir = tmp_path / "results"
    base_dir.mkdir()
    return base_dir


class RunConfigs:
    def __init__(self, pipeline: Path, profile: Path, samples: Path):
        self.pipeline_settings = pipeline
        self.run_profile = profile
        self.samples = samples


@pytest.fixture()
def run_configs(tmp_path: Path, base_dir: Path) -> RunConfigs:

    pipeline_config = get_pipeline_config(base_dir, tmp_path)
    pipeline_config_path = tmp_path / "pipeline_config.ini"
    pipeline_config_path.write_text(pipeline_config)

    profile_config = get_profile_config()
    profile_config_path = tmp_path / "profile_config.ini"
    profile_config_path.write_text(profile_config)

    sample_config_content = get_sample_config(tmp_path)
    sample_config_path = tmp_path / "sample_config.ini"
    sample_config_path.write_text(sample_config_content)

    return RunConfigs(pipeline_config_path, profile_config_path, sample_config_path)
