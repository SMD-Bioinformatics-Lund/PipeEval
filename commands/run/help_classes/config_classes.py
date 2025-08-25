from configparser import ConfigParser, SectionProxy
from logging import Logger
from pathlib import Path
import sys
from typing import Dict, List, Optional, Union

from shared.util import load_config


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

    config: ConfigParser

    pipeline: str
    profile: str
    # single, trio, tumor_pair
    sample_type: str
    samples: List[str]
    default_panel: Optional[str]

    def __init__(self, logger: Logger, run_profile: str, conf_path: Path):

        config = ConfigParser()
        config.read(conf_path)

        if run_profile not in self.config.keys():
            available = ", ".join(self.config.keys())
            logger.error(
                f'Provided profile not present among available entries in the run profile config. Provided: "{run_profile}", available: "{available}"'
            )

        profile_section = self.config[run_profile]

        self.pipeline = parse_mandatory_section_argument(profile_section, run_profile, logger, "pipeline")
        self.profile = parse_mandatory_section_argument(profile_section, run_profile, logger, "profile")
        self.sample_type = parse_mandatory_section_argument(
            profile_section, run_profile, logger, "sample_type"
        )
        samples_str = parse_mandatory_section_argument(profile_section, run_profile, logger, "samples")

        self.samples = samples_str.split(",")
        self.default_panel = profile_section.get("default_panel")


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
                logger,
                default_settings_key,
                pipeline_settings_key,
                "baseline_repo",
                mandatory=False,
            )
        )
        self.base = str(
            self._parse_setting(logger, default_settings_key, pipeline_settings_key, "base")
        )
        self.datestamp: bool = self._parse_setting(
            logger, default_settings_key, pipeline_settings_key, "datestamp", data_type="bool"
        )  # type: ignore[assignment]

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

    run_profile: RunProfileConfig
    settings: RunSettingsConfig
    samples: Dict[str, SampleConfig] = {}

    def __init__(
        self,
        logger: Logger,
        run_profile: str,
        profile_config_path: Path,
        pipeline_config_path: Path,
        sample_config_path: Path,
    ):

        self.run_profile = RunProfileConfig(logger, run_profile, profile_config_path)

        self.settings = RunSettingsConfig(
            logger,
            self.settings_config["pipeline-default"],
            self.settings_config[pipeline_setting_key],
            "pipeline-default",
            pipeline_setting_key,
        )

        pipeline_setting_key = f"pipeline-{self.run_profile.pipeline}"
        if not config_parser.has_section(pipeline_setting_key):
            raise ValueError(
                f"Expected setting key {pipeline_setting_key}, but was not defined in the config file"
            )

        if not self.settings_config.has_section("pipeline-default"):
            logger.error(f'Run type section "pipeline-default" needs to be specified')
            sys.exit(1)

        for sample in self.run_profile.samples:
            sample_key = f"sample-{sample}"
            if not self.settings_config.has_section(sample_key):
                logger.error(f'Sample key "{sample_key}" not found in config')
                sys.exit(1)

            sample_config = SampleConfig(logger, sample_key, self.settings_config[sample_key])
            self.samples[sample_key] = sample_config

    def get_sample_conf(self, sample_id: str) -> SectionProxy:
        case_settings = self.settings_config[f"sample-{sample_id}"]
        return case_settings

    def get_run_type_settings(self) -> Dict[str, str]:
        return dict(self.settings_config[self.run_profile.profile])

    def get_setting_entries(self) -> Dict[str, str]:
        key_vals = {}
        for key, val in self.settings.get_items():
            key_vals[key] = val
        return key_vals

    def get_profile_entries(self, run_profile: str) -> Dict[str, str]:
        key_vals = {}
        for key, val in self.settings_config[run_profile].items():
            key_vals[key] = val
        return key_vals
