import sys
from configparser import ConfigParser
from logging import Logger
from pathlib import Path
from typing import Dict, List, Optional, Union

from shared.util import parse_bool_from_string

DEFAULT_SECTION = "default"


def parse_mandatory_section_argument(
    logger: Logger, section: Dict[str, str], section_name: str, target_key: str
) -> str:
    if not section.get(target_key):
        existing_fields = section.keys()
        logger.error(
            f'Mandatory setting "{target_key}" not defined in config section "{section_name}". (Currently defined fields are : {", ".join(existing_fields)})'
        )
        sys.exit(1)
    return section[target_key]


class SampleConfig:

    config_section: Dict[str, str]

    id: str
    sex: str
    fq_fw: Optional[str]
    fq_rv: Optional[str]
    bam: Optional[str]
    vcf: Optional[str]

    sample_type: str

    def __init__(
        self,
        logger: Logger,
        sample_section: Dict[str, str],
        section_name: str,
        sample_type: str,
    ):

        self.config_section = dict(sample_section.items())

        self.config_section["id"] = section_name

        self.id = section_name
        self.sex = parse_mandatory_section_argument(
            logger, self.config_section, section_name, "sex"
        )

        self.fq_fw = sample_section.get("fq_fw")
        self.fq_rv = sample_section.get("fq_rv")
        self.bam = sample_section.get("bam")
        self.vcf = sample_section.get("vcf")

        self.sample_type = sample_type

    def items(self):
        return self.config_section.items()


class RunProfileConfig:

    # config: ConfigParser
    config_section: Dict[str, str]

    # single, trio, paired_tumor - calculated from sample types
    case_type: str

    pipeline: str
    run_profile: str
    pipeline_profile: Optional[str]
    samples: List[str]
    sample_types: List[str]
    default_panel: Optional[str]

    csv_template: str

    def __init__(
        self,
        logger: Logger,
        run_profile: str,
        profile_section_name: str,
        profile_section: Dict[str, str],
    ):

        self.run_profile = run_profile
        self.config_section = profile_section

        self.pipeline = parse_mandatory_section_argument(
            logger, profile_section, profile_section_name, "pipeline"
        )
        self.pipeline_profile = profile_section.get("pipeline_profile")
        self.csv_template = parse_mandatory_section_argument(
            logger, profile_section, profile_section_name, "csv_template"
        )

        samples_str = parse_mandatory_section_argument(
            logger, profile_section, profile_section_name, "samples"
        )
        self.samples = samples_str.split(",")

        sample_types_str = profile_section.get("sample_types")

        if not sample_types_str:
            logger.info(
                "No sample_types section in run_profile. Defaulting to 'proband'."
            )
            self.sample_types = ["proband"]
        else:
            self.sample_types = sample_types_str.split(",")

        if len(self.samples) != len(self.sample_types):
            logger.error(
                f'Different number of samples and sample types. Found samples: "{samples_str}" and sample_types "{sample_types_str}"'
            )
            sys.exit(1)

        self.case_type = self._detect_case_type(logger, self.sample_types)

        self.default_panel = profile_section.get("default_panel")

    def _detect_case_type(self, logger: Logger, sample_types: List[str]) -> str:
        if len(sample_types) == 1:
            return "single"
        elif len(sample_types) == 2:
            sorted_types = sorted(sample_types)
            if sorted_types == ["N", "T"]:
                return "paired_tumor"
            logger.error(
                f"Only known sample type combination for two entries are types 'N' and 'T'. Found: {sorted_types}"
            )
        elif len(sample_types) == 3:
            sorted_types = sorted(sample_types)
            if sorted_types == ["father", "mother", "proband"]:
                return "trio"
            logger.error(
                f"Only known sample type combination for three entries are types 'proband', 'mother' and 'father'. Found: {sorted_types}"
            )
        else:
            logger.error(
                f"Only cases with 1, 2 or 3 samples are supported. Found: {len(sample_types)}"
            )
        sys.exit(1)

    def items(self):
        return self.config_section.items()


class PipelineSettingsConfig:

    _default_settings: Dict[str, str]
    _pipeline_settings: Dict[str, str]
    raw_config = Dict[str, str]

    pipeline: str

    start_nextflow_analysis: str
    log_base_dir: str
    trace_base_dir: str
    work_base_dir: str
    repo: str
    out_base: str
    baseline_repo: str
    datestamp: bool
    queue: str
    executor: str
    cluster: str

    nextflow_configs: List[Path] = []

    singularity_version: str
    nextflow_version: str
    container: str
    runscript: str

    def __init__(
        self,
        logger: Logger,
        pipeline: str,
        default_settings: Dict[str, str],
        pipeline_settings: Dict[str, str],
    ):

        self.pipeline = pipeline

        self._default_settings = default_settings
        self._pipeline_settings = pipeline_settings

        self.singularity_version = str(
            self._parse_setting(logger, "singularity_version")
        )
        self.nextflow_version = str(self._parse_setting(logger, "nextflow_version"))
        self.container = str(self._parse_setting(logger, "container"))
        self.runscript = str(self._parse_setting(logger, "runscript"))

        self.start_nextflow_analysis = str(
            self._parse_setting(logger, "start_nextflow_analysis")
        )
        self.log_base_dir = str(self._parse_setting(logger, "log_base_dir"))
        self.trace_base_dir = str(self._parse_setting(logger, "trace_base_dir"))
        self.work_base_dir = str(self._parse_setting(logger, "work_base_dir"))
        self.repo = str(self._parse_setting(logger, "repo"))
        self.baseline_repo = str(
            self._parse_setting(
                logger,
                "baseline_repo",
                mandatory=False,
            )
        )
        self.out_base = str(self._parse_setting(logger, "base"))
        self.datestamp: bool = self._parse_setting(
            logger, "datestamp", data_type="bool"
        )  # type: ignore[assignment]

        self.nextflow_configs = [
            Path(p)
            for p in self._parse_list(logger, "nextflow_configs", mandatory=False)
        ]

        self.queue = str(self._parse_setting(logger, "queue"))
        self.executor = str(self._parse_setting(logger, "executor"))
        self.cluster = str(self._parse_setting(logger, "cluster"))

    def get_items(self):

        combined_settings = {}
        for key, val in self._default_settings.items():
            combined_settings[key] = val

        for key, val in self._pipeline_settings.items():
            combined_settings[key] = val

        return combined_settings.items()

    def _parse_list(
        self, logger: Logger, setting_key: str, mandatory: bool = True
    ) -> List[str]:
        parsed_setting = self._parse_setting(logger, setting_key, "string", mandatory)
        if parsed_setting is None:
            return []
        else:
            return str(parsed_setting).split(",")

    def _parse_setting(
        self,
        logger: Logger,
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
                f'Did not find setting "{setting_key}" in neither "{self.pipeline}" or "{DEFAULT_SECTION}"'
            )
            sys.exit(1)

        if not target_section:
            return None

        if data_type == "string":
            return target_section[setting_key]
        elif data_type == "bool":
            str_value = target_section[setting_key]
            return parse_bool_from_string(str_value)
        else:
            raise ValueError(
                f"Unknown data_type: {data_type}, known are string and bool"
            )


class RunConfig:

    run_profile_key: str
    run_profile: RunProfileConfig
    general_settings: PipelineSettingsConfig
    all_samples: Dict[str, SampleConfig]

    def __init__(
        self,
        logger: Logger,
        run_profile: str,
        profile_config_path: Path,
        pipeline_config_path: Path,
        sample_config_path: Path,
    ):
        self.all_samples = {}
        self.run_profile_key = run_profile

        self.run_profile = self._get_run_profile_config(
            logger, str(profile_config_path), run_profile
        )

        self.general_settings = self._get_pipeline_config(
            logger, str(pipeline_config_path)
        )

        sample_config_parser = ConfigParser()
        sample_config_parser.read(sample_config_path)

        sample_types = self.run_profile.sample_types

        for i, sample in enumerate(self.run_profile.samples):
            if sample not in sample_config_parser.keys():
                sections = ", ".join(sample_config_parser.keys())
                logger.error(
                    f'Expected to find "{sample}", found sections: "{sections}"'
                )
                sys.exit(1)
            section = sample_config_parser[sample]
            section_dict = dict(section.items())
            sample_config = SampleConfig(
                logger, section_dict, section.name, sample_types[i]
            )
            self.all_samples[sample] = sample_config

    def get_sample_conf(self, sample_id: str) -> SampleConfig:
        case_settings = self.all_samples[sample_id]
        return case_settings

    def get_setting_entries(self) -> Dict[str, str]:
        key_vals = {}
        for key, val in self.general_settings.get_items():
            key_vals[key] = val
        return key_vals

    def get_profile_entries(self) -> Dict[str, str]:

        key_vals = {}
        for key, val in self.run_profile.items():
            key_vals[key] = val
        return key_vals

    def _get_run_profile_config(
        self, logger: Logger, path: str, run_profile: str
    ) -> RunProfileConfig:
        config = ConfigParser()
        config.read(path)
        if run_profile not in config.keys():
            ignore = {"DEFAULT"}
            available = ", ".join(set(config.keys()) - ignore)
            logger.error(
                f"Provided run profile not present among available entries in the run profile config. Provided: {run_profile}, available: {available}"
            )
            sys.exit(1)
        profile_section = dict(config[run_profile].items())
        profile_section_name = config[run_profile].name
        run_config = RunProfileConfig(
            logger, run_profile, profile_section_name, profile_section
        )
        return run_config

    def _get_pipeline_config(
        self, logger: Logger, pipeline_config_path: str
    ) -> PipelineSettingsConfig:
        pipeline_config = ConfigParser()
        pipeline_config.read(pipeline_config_path)
        if self.run_profile.pipeline not in pipeline_config.keys():
            available = ", ".join(pipeline_config.keys())
            logger.error(
                f'Target pipeline "{self.run_profile.pipeline}" not found as an entry in the pipeline config. Available entries are: "{available}"'
            )
            sys.exit(1)
        pipeline_default_settings = dict(pipeline_config[DEFAULT_SECTION].items())
        pipeline_settings = dict(pipeline_config[self.run_profile.pipeline].items())

        config = PipelineSettingsConfig(
            logger,
            self.run_profile.pipeline,
            pipeline_default_settings,
            pipeline_settings,
        )

        return config
