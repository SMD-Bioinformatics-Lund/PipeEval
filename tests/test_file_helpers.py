import logging
from types import SimpleNamespace

import pytest

from commands.run.file_helpers import get_replace_map
from commands.run.help_classes.config_classes import RunProfileConfig, SampleConfig


@pytest.fixture
def logger():
    return logging.getLogger("test_get_replace_map")

@pytest.fixture
def sample_config(logger: logging.Logger) -> SampleConfig:
    sample_section = {
        "id": "sample-1",
        "sample_type": "proband",
        "sex": "F",
        "fq_fw": "sample1-R1.fastq.gz",
        "fq_rv": "sample1-R2.fastq.gz",
        "bam": "sample-1.bam",
        "vcf": "sample-1.vcf",
    }
    # defaults.update(overrides)

    return SampleConfig(logger, sample_section, "sample-1", "proband")

@pytest.fixture
def run_profile_config(logger: logging.Logger) -> RunProfileConfig:

    profile_section = {
        "pipeline": "test-pipeline",
        "csv_template": "csv template placeholder",
        "samples": "sample-1",
        "sample_types": "proband",
        "default_panel": "panel-A",
    }

    return RunProfileConfig(logger, "run profile", "name", profile_section)


def test_get_replace_map_basic(logger, run_profile_config, sample_config):

    replace_map = get_replace_map(
        logger,
        "fq",
        [sample_config],
        "run-123",
        run_profile_config,
    )

    assert replace_map.get("<id proband>") == "sample-1"
    assert replace_map.get("<group>") == "run-123"
    assert replace_map.get("<sex proband>") == "F"
    assert replace_map.get("<default_panel>") == "panel-A"
    assert replace_map.get("<read1 proband>") == "sample1-R1.fastq.gz"
    assert replace_map.get("<read2 proband>") == "sample1-R2.fastq.gz"


# def test_get_replace_map_vcf_adds_bai_suffix(logger):
#     sample = sample_config(vcf="proband.vcf")

#     replace_map = get_replace_map(
#         logger,
#         starting_run_from="vcf",
#         sample=sample,
#         run_label="run-456",
#         default_panel=None,
#         case_type="single",
#         all_sample_ids=["sample-1"],
#         all_sample_types=["proband"],
#     )

#     assert replace_map["<read1 proband>"] == "proband.vcf"
#     assert replace_map["<read2 proband>"] == "proband.vcf.bai"


# def test_get_replace_map_bam_missing_file_exits(logger):
#     sample = sample_config(bam=None)
#     run_profile = run_profile_config()

#     with pytest.raises(SystemExit):
#         get_replace_map(
#             logger,
#             starting_run_from="bam",
#             sample=[sample],
#             run_label="run-789",
#         )


# def test_get_replace_map_invalid_starting_run_from_raises_value_error(logger):
#     sample = sample_config()

#     with pytest.raises(ValueError):
#         get_replace_map(
#             logger,
#             starting_run_from="invalid",
#             sample=sample,
#             run_label="run-789",
#             default_panel=None,
#             case_type="single",
#             all_sample_ids=["sample-1"],
#             all_sample_types=["proband"],
#         )
