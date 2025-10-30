import logging
from types import SimpleNamespace

import pytest

from commands.run.file_helpers import get_replace_map


@pytest.fixture
def logger():
    return logging.getLogger("test_get_replace_map")


def make_sample(**overrides):
    defaults = {
        "id": "sample-1",
        "sample_type": "proband",
        "sex": "F",
        "fq_fw": "sample-1_R1.fastq.gz",
        "fq_rv": "sample-1_R2.fastq.gz",
        "bam": "sample-1.bam",
        "vcf": "sample-1.vcf",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_get_replace_map_fq_with_default_panel_trio(logger):
    sample = make_sample()

    replace_map = get_replace_map(
        logger,
        starting_run_from="fq",
        sample=sample,
        run_label="run-123",
        default_panel="panel-A",
        case_type="trio",
        all_sample_ids=["sample-1", "father-1", "mother-1"],
        all_sample_types=["proband", "father", "mother"],
    )

    assert replace_map == {
        "<id proband>": "sample-1",
        "<group>": "run-123",
        "<sex proband>": "F",
        "<default_panel>": "panel-A",
        "<read1 proband>": "sample-1_R1.fastq.gz",
        "<read2 proband>": "sample-1_R2.fastq.gz",
        "<father>": "father-1",
        "<mother>": "mother-1",
    }


def test_get_replace_map_vcf_adds_bai_suffix(logger):
    sample = make_sample(vcf="proband.vcf")

    replace_map = get_replace_map(
        logger,
        starting_run_from="vcf",
        sample=sample,
        run_label="run-456",
        default_panel=None,
        case_type="single",
        all_sample_ids=["sample-1"],
        all_sample_types=["proband"],
    )

    assert replace_map["<read1 proband>"] == "proband.vcf"
    assert replace_map["<read2 proband>"] == "proband.vcf.bai"


def test_get_replace_map_bam_missing_file_exits(logger):
    sample = make_sample(bam=None)

    with pytest.raises(SystemExit):
        get_replace_map(
            logger,
            starting_run_from="bam",
            sample=sample,
            run_label="run-789",
            default_panel=None,
            case_type="single",
            all_sample_ids=["sample-1"],
            all_sample_types=["proband"],
        )


def test_get_replace_map_invalid_starting_run_from_raises_value_error(logger):
    sample = make_sample()

    with pytest.raises(ValueError):
        get_replace_map(
            logger,
            starting_run_from="invalid",
            sample=sample,
            run_label="run-789",
            default_panel=None,
            case_type="single",
            all_sample_ids=["sample-1"],
            all_sample_types=["proband"],
        )
