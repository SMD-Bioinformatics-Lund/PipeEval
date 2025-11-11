import logging
from types import SimpleNamespace

import pytest

from commands.run.file_helpers import get_replace_map
from commands.run.help_classes.config_classes import RunProfileConfig, SampleConfig


@pytest.fixture
def logger():
    return logging.getLogger("test_get_replace_map")


@pytest.fixture
def proband_config(logger: logging.Logger) -> SampleConfig:

    sample_id = "sample-1"
    sample_type = "proband"

    sample_section = {
        "id": sample_id,
        "sample_type": sample_type,
        "sex": "M",
        "fq_fw": "sample1-R1.fastq.gz",
        "fq_rv": "sample1-R2.fastq.gz",
        "bam": "sample-1.bam",
        "vcf": "sample-1.vcf",
    }

    return SampleConfig(logger, sample_section, sample_id, sample_type)


@pytest.fixture
def mother_config(logger: logging.Logger) -> SampleConfig:

    sample_id = "sample-2"
    sample_type = "mother"

    sample_section = {
        "id": sample_id,
        "sample_type": sample_type,
        "sex": "F",
        "fq_fw": "sample2-R1.fastq.gz",
        "fq_rv": "sample2-R2.fastq.gz",
        "bam": "sample-2.bam",
    }

    return SampleConfig(logger, sample_section, sample_id, sample_type)


@pytest.fixture
def father_config(logger: logging.Logger) -> SampleConfig:

    sample_id = "sample-3"
    sample_type = "father"

    sample_section = {
        "id": sample_id,
        "sample_type": sample_type,
        "sex": "M",
        "fq_fw": "sample3-R1.fastq.gz",
        "fq_rv": "sample3-R2.fastq.gz",
        "bam": "sample-3.bam",
    }

    return SampleConfig(logger, sample_section, sample_id, sample_type)


def test_get_replace_map_single(logger: logging.Logger, proband_config: SampleConfig):

    profile_section = {
        "pipeline": "test-pipeline",
        "csv_template": "csv template placeholder",
        "samples": "sample-1",
        "sample_types": "proband",
        "default_panel": "panel-A",
    }

    profile_config = RunProfileConfig(logger, "run profile", "name", profile_section)

    replace_map = get_replace_map(
        logger,
        "fq",
        [proband_config],
        "run-123",
        profile_config,
    )

    # Special cases
    assert replace_map.get("<group>") == "run-123"
    assert replace_map.get("<read1 proband>") == "sample1-R1.fastq.gz"
    assert replace_map.get("<read2 proband>") == "sample1-R2.fastq.gz"

    # Generic profile
    assert replace_map.get("<pipeline>") == "test-pipeline"
    assert replace_map.get("<default_panel>") == "panel-A"

    # Sample generic
    assert replace_map.get("<id proband>") == "sample-1"
    assert replace_map.get("<sex proband>") == "M"


def test_get_replace_map_single_bam(logger: logging.Logger, proband_config: SampleConfig):

    profile_section = {
        "pipeline": "test-pipeline",
        "csv_template": "csv template placeholder",
        "samples": "sample-1",
        "sample_types": "proband",
        "default_panel": "panel-A",
    }

    profile_config = RunProfileConfig(logger, "run profile", "name", profile_section)

    replace_map = get_replace_map(
        logger,
        "bam",
        [proband_config],
        "run-123",
        profile_config,
    )

    # Special cases
    assert replace_map.get("<group>") == "run-123"
    assert replace_map.get("<read1 proband>") == "sample-1.bam"
    assert replace_map.get("<read2 proband>") == "sample-1.bam.bai"

    # Generic profile
    assert replace_map.get("<pipeline>") == "test-pipeline"
    assert replace_map.get("<default_panel>") == "panel-A"

    # Sample generic
    assert replace_map.get("<id proband>") == "sample-1"
    assert replace_map.get("<sex proband>") == "M"


def test_get_replace_map_trio(
    logger: logging.Logger,
    proband_config: SampleConfig,
    mother_config: SampleConfig,
    father_config: SampleConfig,
):

    profile_section = {
        "pipeline": "test-pipeline",
        "csv_template": "csv template placeholder",
        "samples": "sample-1,sample-2,sample-3",
        "sample_types": "proband,mother,father",
        "default_panel": "panel-A",
    }

    profile_config = RunProfileConfig(logger, "run profile", "name", profile_section)

    replace_map = get_replace_map(
        logger,
        "fq",
        [proband_config, mother_config, father_config],
        "run-123",
        profile_config,
    )

    # Special cases
    assert replace_map.get("<group>") == "run-123"
    assert replace_map.get("<read1 proband>") == "sample1-R1.fastq.gz"
    assert replace_map.get("<read2 proband>") == "sample1-R2.fastq.gz"
    assert replace_map.get("<read1 mother>") == "sample2-R1.fastq.gz"
    assert replace_map.get("<read2 mother>") == "sample2-R2.fastq.gz"
    assert replace_map.get("<read1 father>") == "sample3-R1.fastq.gz"
    assert replace_map.get("<read2 father>") == "sample3-R2.fastq.gz"

    # Generic profile
    assert replace_map.get("<pipeline>") == "test-pipeline"
    assert replace_map.get("<default_panel>") == "panel-A"

    # Sample generic
    assert replace_map.get("<id proband>") == "sample-1"
    assert replace_map.get("<id mother>") == "sample-2"
    assert replace_map.get("<id father>") == "sample-3"
    assert replace_map.get("<sex proband>") == "M"
    assert replace_map.get("<sex mother>") == "F"
    assert replace_map.get("<sex father>") == "M"


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
