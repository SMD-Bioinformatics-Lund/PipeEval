from configparser import ConfigParser, SectionProxy
from logging import Logger
import sys
from typing import Dict, List, Optional, Union


def parse_mandatory_section_argument(
    section: SectionProxy, section_key: str, logger: Logger, target_key: str
) -> str:
    if not section.get(target_key):
        existing_fields = section.keys()
        logger.error(
            f'Mandatory setting "{target_key}" not defined in run type section "{section_key}". (Currently defined fields are : {", ".join(existing_fields)})'
        )
        sys.exit(1)
    return section[target_key]


class SampleConfig:

    id: str
    clarity_pool_id: int
    clarity_sample_id: str
    sex: str
    type: str
    fq_fw: Optional[str]
    fq_rv: Optional[str]
    bam: Optional[str]
    vcf: Optional[str]

    def __init__(self, logger: Logger, key: str, sample_section: SectionProxy):

        self.id = parse_mandatory_section_argument(sample_section, key, logger, "id")
        self.clarity_pool_id = int(
            parse_mandatory_section_argument(sample_section, key, logger, "clarity_pool_id")
        )
        self.clarity_sample_id = parse_mandatory_section_argument(
            sample_section, key, logger, "clarity_sample_id"
        )
        self.sex = parse_mandatory_section_argument(sample_section, key, logger, "sex")
        self.type = parse_mandatory_section_argument(sample_section, key, logger, "type")

        self.fq_fw = sample_section.get("fq_fw")
        self.fq_rv = sample_section.get("fq_rv")
        self.bam = sample_section.get("bam")
        self.vcf = sample_section.get("vcf")


class RunProfileConfig:

    raw_config: Dict[str, str]

    pipeline: str
    profile_name: str
    # single, trio, tumor_pair
    sample_type: str
    samples: List[str]
    default_panel: Optional[str]

    def __init__(self, logger: Logger, profile_key: str, run_profile_conf: SectionProxy):

        self.raw_config = dict(run_profile_conf)

        self.pipeline = parse_mandatory_section_argument(
            run_profile_conf, profile_key, logger, "pipeline"
        )
        self.profile_name = parse_mandatory_section_argument(
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
    repo: str
    # FIXME: Clearer name. Out base?
    base: str
    baseline_repo: str
    datestamp: bool
    queue: str
    executor: str
    cluster: str

    singularity_version: str
    nextflow_version: str
    container: str
    runscript: str

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

        self.singularity_version = str(
            self._parse_setting(
                logger, default_settings_key, pipeline_settings_key, "singularity_version"
            )
        )
        self.nextflow_version = str(
            self._parse_setting(
                logger, default_settings_key, pipeline_settings_key, "nextflow_version"
            )
        )
        self.container = str(
            self._parse_setting(logger, default_settings_key, pipeline_settings_key, "container")
        )
        self.runscript = str(
            self._parse_setting(logger, default_settings_key, pipeline_settings_key, "runscript")
        )

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
        self.repo = str(
            self._parse_setting(logger, default_settings_key, pipeline_settings_key, "repo")
        )
        self.baseline_repo = str(
            self._parse_setting(
                logger, default_settings_key, pipeline_settings_key, "baseline_repo", mandatory=False
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

    def get_items(self):
        
        combined_settings = {}
        for key, val in self._default_settings.items():
            combined_settings[key] = val
        
        for key, val in self._pipeline_settings.items():
            combined_settings[key] = val

        return combined_settings.items()

    def _parse_setting(
        self,
        logger: Logger,
        default_settings_key: str,
        pipeline_settings_key: str,
        setting_key: str,
        data_type: str = "string",
        mandatory: bool = True,
    ) -> Union[str, bool, None]:
        target_section = None
        if self._pipeline_settings.get(setting_key):
            target_section = self._pipeline_settings
        elif self._default_settings.get(setting_key):
            target_section = self._default_settings

        if not target_section and mandatory:
            logger.error(
                f'Did not find setting "{setting_key}" in neither "{pipeline_settings_key}" or "{default_settings_key}"'
            )
            sys.exit(1)

        if not target_section:
            return None

        if data_type == "string":
            return target_section[setting_key]
        elif data_type == "bool":
            parsed_bool = bool(target_section.getboolean(setting_key))
            return parsed_bool
        else:
            raise ValueError(f"Unknown data_type: {data_type}, known are string and bool")


class RunConfig:

    config_parser: ConfigParser
    profile: RunProfileConfig
    settings: RunSettingsConfig
    samples: Dict[str, SampleConfig] = {}

    run_type: str

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

        self.settings = RunSettingsConfig(
            logger,
            self.config_parser["pipeline-default"],
            self.config_parser[pipeline_setting_key],
            "pipeline-default",
            pipeline_setting_key,
        )

        for sample in self.profile.samples:
            sample_key = f"sample-{sample}"
            if not self.config_parser.has_section(sample_key):
                logger.error(f'Sample key "{sample_key}" not found in config')
                sys.exit(1)

            sample_config = SampleConfig(logger, sample_key, self.config_parser[sample_key])
            self.samples[sample_key] = sample_config

    def get_sample_conf(self, sample_id: str, is_stub: bool) -> SectionProxy:
        case_settings = self.config_parser[sample_id]
        # if is_stub:
        #     stub_case =
        return case_settings

    def get_run_type_settings(self) -> Dict[str, str]:
        return dict(self.config_parser[self.run_type])

    def get_setting_entries(self) -> Dict[str, str]:
        key_vals = {}
        for key, val in self.settings.get_items():
            key_vals[key] = val
        return key_vals

    def get_profile_entries(self, run_type: str) -> Dict[str, str]:
        key_vals = {}
        for key, val in self.config_parser[run_type].items():
            key_vals[key] = val
        return key_vals