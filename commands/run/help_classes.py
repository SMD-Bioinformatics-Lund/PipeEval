from configparser import ConfigParser, SectionProxy
from logging import Logger
from pathlib import Path
import sys
from typing import Dict, List, Optional


# def check_valid_config_arguments(
#     config: ConfigParser,
#     run_type: str,
#     start_data: str,
#     base_dir: Optional[Path],
#     repo: Optional[Path],
# ):
#     if not config.has_section(run_type):
#         raise ValueError(f"Valid config keys are: {config.sections()}")
#     valid_start_data = ["fq", "bam", "vcf"]
#     if start_data not in valid_start_data:
#         raise ValueError(f"Valid start_data types are: {', '.join(valid_start_data)}")

#     if base_dir is None:
#         if not check_valid_config_path(config, "settings", "base"):
#             found = config.get("settings", "base")
#             raise ValueError(
#                 f"A valid output base folder must be specified either through the '--base' flag, or in the config['settings']['base']. Found: {found}"
#             )

#     if repo is None:
#         if not check_valid_config_path(config, "settings", "repo"):
#             found = config.get("settings", "repo")
#             raise ValueError(
#                 f"A valid repo must be specified either through the '--repo' flag, or in the config['settings']['repo']. Found: {found}"
#             )


def parse_mandatory_section_argument(section: SectionProxy, section_key: str, logger: Logger, target_key: str) -> str:
    if not section.get(target_key):
        logger.error(
            f'Mandatory setting "{target_key}" not defined in run type section {section_key}'
        )
        sys.exit(1)
    return section[target_key]


class RunProfileConfig:

    profile_config: SectionProxy

    pipeline: str
    profile: str
    # single, trio, tumor_pair
    sample_type: str
    samples: List[str]
    default_panel: Optional[str]

    def __init__(self, logger: Logger, profile_key: str, run_profile_conf: SectionProxy):

        self.profile_config = run_profile_conf

        self.pipeline = parse_mandatory_section_argument(run_profile_conf, profile_key, logger, "pipeline")
        self.profile = parse_mandatory_section_argument(run_profile_conf, profile_key, logger, "profile")
        self.sample_type = parse_mandatory_section_argument(run_profile_conf, profile_key, logger, "sample_type")
        samples_str = parse_mandatory_section_argument(run_profile_conf, profile_key, logger, "samples")
        self.samples = samples_str.split(",")
        self.default_panel = run_profile_conf.get("default_panel")


class RunConfig:

    config_parser: ConfigParser
    profile: RunProfileConfig
    # profile_config: SectionProxy
    # pipeline_config: SectionProxy

    run_type: str

    # Sub object?
    start_nextflow_analysis: str
    executor: str
    cluster: str
    queue: str
    singularity_version: str
    nextflow_version: str
    container: str
    runscript: str

    log_base_dir: str
    trace_base_dir: str
    work_base_dir: str

    base: Path
    baseline_repo: Path
    repo: Path
    datestamp: bool
    trio: bool

    def __init__(self, logger: Logger, config_parser: ConfigParser, run_type: str):
        self.config_parser = config_parser
        self.run_type = run_type

        if not self.config_parser.has_section(run_type):
            logger.error(f'Run type section "{run_type}" needs to be specified in config')
            sys.exit(1)

        self.profile = RunProfileConfig(logger, run_type, config_parser[run_type])

        pipeline_setting_key = f"pipeline-{self.profile.pipeline}"
        if not config_parser.has_section(pipeline_setting_key):
            raise ValueError(
                f"Expected setting key {pipeline_setting_key}, but was not defined in the config file"
            )


    def get_sample_conf(self, sample_id: str, is_stub: bool) -> SectionProxy:
        case_settings = self.config_parser[sample_id]
        # if is_stub:
        #     stub_case =
        return case_settings

    def get_run_type_settings(self) -> Dict[str, str]:
        return dict(self.config_parser[self.run_type])

    def get_setting_entries(self) -> Dict[str, str]:
        key_vals = {}
        for key, val in self.config_parser["settings"].items():
            key_vals[key] = val
        return key_vals

    def get_profile_entries(self, run_type: str) -> Dict[str, str]:
        key_vals = {}
        for key, val in self.config_parser[run_type].items():
            key_vals[key] = val
        return key_vals


class Case:
    def __init__(
        self,
        id: str,
        clarity_pool_id: str,
        clarity_sample_id: str,
        sex: str,
        type: str,
        read1: str,
        read2: str,
        father: Optional[str] = None,
        mother: Optional[str] = None,
        phenotype: str = "healthy",
    ):
        self.id = id
        self.clarity_pool_id = clarity_pool_id
        self.clarity_sample_id = clarity_sample_id
        self.sex = sex
        self.type = type
        self.read1 = read1
        self.read2 = read2
        self.father = father or "0"
        self.mother = mother or "0"
        self.phenotype = phenotype

    def __getitem__(self, key: str) -> str:
        return getattr(self, key)


class CsvEntry:

    headers = [
        "clarity_sample_id",
        "id",
        "type",
        "sex",
        "assay",
        "diagnosis",
        "phenotype",
        "group",
        "father",
        "mother",
        "clarity_pool_id",
        "platform",
        "read1",
        "read2",
        "analysis",
        "priority",
    ]

    case_headers = [
        "clarity_sample_id",
        "id",
        "type",
        "sex",
        "phenotype",
        "father",
        "mother",
        "read1",
        "read2",
    ]

    def __init__(
        self,
        group: str,
        cases: List[Case],
        priority: Optional[str],
        assay: str,
        analysis: str,
        diagnosis: str,
    ):
        self.cases = cases

        self.assay = assay
        self.group = group
        self.clarity_pool_id = "NA"
        self.diagnosis = diagnosis
        self.platform = "illumina"
        self.analysis = analysis
        self.priority = priority or "grace-lowest"

    def header_str(self) -> str:
        return ",".join(self.headers)

    def __getitem__(self, key: str) -> str:
        return getattr(self, key)

    def __str__(self) -> str:
        rows: List[str] = []
        for case in self.cases:
            row: List[str] = []
            for header in self.headers:
                if header in self.case_headers:
                    value = case[header]
                else:
                    value = self[header]
                row.append(value.strip('"'))
            rows.append(",".join(row))
        return "\n".join(rows)

    def write_to_file(self, out_path: str):
        with open(out_path, "w") as out_fh:
            print(self.header_str(), file=out_fh)
            print(str(self), file=out_fh)
