from pathlib import Path

import pytest

from tests.conftest_utils.run_configs import (
    ConfigSamplePathGroup,
    ConfigSamplePaths,
    get_pipeline_config,
    get_run_profile_config,
    get_sample_config,
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


@pytest.fixture
def config_sample_paths(tmp_path: Path) -> ConfigSamplePathGroup:

    proband = ConfigSamplePaths(tmp_path, "proband")
    mother = ConfigSamplePaths(tmp_path, "mother")
    father = ConfigSamplePaths(tmp_path, "father")
    tumor = ConfigSamplePaths(tmp_path, "tumor")
    normal = ConfigSamplePaths(tmp_path, "normal")
    rna = ConfigSamplePaths(tmp_path, "rna")

    group = ConfigSamplePathGroup(proband, mother, father, tumor, normal, rna)
    return group


@pytest.fixture()
def get_run_config_paths(
    tmp_path: Path, base_dir: Path, config_sample_paths: ConfigSamplePathGroup
) -> RunConfigs:

    run_profile_config = get_run_profile_config()
    run_profile_config_path = tmp_path / "profile_config.ini"
    run_profile_config_path.write_text(run_profile_config)

    pipeline_config = get_pipeline_config(base_dir, tmp_path)
    pipeline_config_path = tmp_path / "pipeline_config.ini"
    pipeline_config_path.write_text(pipeline_config)

    sample_config_content = get_sample_config(config_sample_paths)
    sample_config_path = tmp_path / "sample_config.ini"
    sample_config_path.write_text(sample_config_content)

    return RunConfigs(pipeline_config_path, run_profile_config_path, sample_config_path)
