from configparser import ConfigParser, SectionProxy
from logging import Logger
from pathlib import Path
import sys
from typing import Dict, List, Optional, Union


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


def parse_mandatory_section_argument(
    section: SectionProxy, section_key: str, logger: Logger, target_key: str
) -> str:
    if not section.get(target_key):
        logger.error(
            f'Mandatory setting "{target_key}" not defined in run type section {section_key}'
        )
        sys.exit(1)
    return section[target_key]


class RunProfileConfig:

    raw_config: Dict[str, str]

    pipeline: str
    profile: str
    # single, trio, tumor_pair
    sample_type: str
    samples: List[str]
    default_panel: Optional[str]

    def __init__(self, logger: Logger, profile_key: str, run_profile_conf: SectionProxy):

        self.raw_config = dict(run_profile_conf)

        self.pipeline = parse_mandatory_section_argument(
            run_profile_conf, profile_key, logger, "pipeline"
        )
        self.profile = parse_mandatory_section_argument(
            run_profile_conf, profile_key, logger, "profile"
        )
        self.sample_type = parse_mandatory_section_argument(
            run_profile_conf, profile_key, logger, "sample_type"
        )
        samples_str = parse_mandatory_section_argument(
            run_profile_conf, profile_key, logger, "samples"
        )
        self.samples = samples_str.split(",")
        self.default_panel = run_profile_conf.get("default_panel")


class RunSettingsConfig:

    _default_settings: SectionProxy
    _pipeline_settings: SectionProxy
    raw_config = Dict[str, str]

    start_nextflow_analysis: str
    log_base_dir: str
    trace_base_dir: str
    work_base_dir: str
    # FIXME: Clearer name. Out base?
    base: str
    datestamp: bool
    queue: str
    executor: str
    cluster: str

    def __init__(
        self,
        logger: Logger,
        default_settings: SectionProxy,
        pipeline_settings: SectionProxy,
        default_settings_key: str,
        pipeline_settings_key: str,
    ):
        self._default_settings = default_settings
        self._pipeline_settings = pipeline_settings

        self.start_nextflow_analysis = str(
            self._parse_setting(
                logger, default_settings_key, pipeline_settings_key, "start_nextflow_analysis"
            )
        )
        self.log_base_dir = str(
            self._parse_setting(logger, default_settings_key, pipeline_settings_key, "log_base_dir")
        )
        self.trace_base_dir = str(
            self._parse_setting(
                logger, default_settings_key, pipeline_settings_key, "trace_base_dir"
            )
        )
        self.work_base_dir = str(
            self._parse_setting(
                logger, default_settings_key, pipeline_settings_key, "work_base_dir"
            )
        )
        self.base = str(
            self._parse_setting(logger, default_settings_key, pipeline_settings_key, "base")
        )
        self.datestamp = bool(
            self._parse_setting(logger, default_settings_key, pipeline_settings_key, "datestamp")
        )
        self.queue = str(
            self._parse_setting(logger, default_settings_key, pipeline_settings_key, "queue")
        )
        self.executor = str(
            self._parse_setting(logger, default_settings_key, pipeline_settings_key, "executor")
        )
        self.cluster = str(
            self._parse_setting(logger, default_settings_key, pipeline_settings_key, "cluster")
        )

    def _parse_setting(
        self,
        logger: Logger,
        default_settings_key: str,
        pipeline_settings_key: str,
        setting_key: str,
        data_type: str = "string",
    ) -> Union[str, bool]:
        target_section = None
        if self._pipeline_settings.get(setting_key):
            target_section = self._pipeline_settings
        elif self._default_settings.get(setting_key):
            target_section = self._default_settings

        if not target_section:
            logger.error(
                f'Did not find setting "{setting_key}" in neither "{pipeline_settings_key}" or "{default_settings_key}"'
            )
            sys.exit(1)

        if data_type == "string":
            return target_section[setting_key]
        elif data_type == "bool":
            parsed_bool = bool(target_section.getboolean(setting_key))
            return parsed_bool
        else:
            raise ValueError(f"Unknown data_type: {data_type}, known are string and bool")


class SampleConfig:
    def __init__(self):
        pass


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

        if not self.config_parser.has_section("pipeline-default"):
            logger.error(f'Run type section "pipeline-default" needs to be specified')
            sys.exit(1)

        self.run_settings_config = RunSettingsConfig(
            logger,
            self.config_parser["pipeline-default"],
            self.config_parser[pipeline_setting_key],
            "pipeline-default",
            pipeline_setting_key,
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
