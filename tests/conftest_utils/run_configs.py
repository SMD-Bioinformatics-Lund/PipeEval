import textwrap
from pathlib import Path


class ConfigSamplePaths:
    fq_fw: Path
    fq_rv: Path
    bam: Path
    vcf: Path

    def __init__(self, tmp_path: Path, label: str):
        self.fq_fw = tmp_path / f"{label}_fw.fq"
        self.fq_rv = tmp_path / f"{label}_rv.fq"
        self.bam = tmp_path / f"{label}.bam"
        self.vcf = tmp_path / f"{label}.vcf"

        for path in [self.fq_fw, self.fq_rv, self.bam, self.vcf]:
            path.touch()


def get_pipeline_config(base_dir: Path, tmp_path: Path) -> str:

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()
    (repo_dir / "nextflow.config").write_text("nextflow")

    settings_config_text = textwrap.dedent(
        f"""
        [default]
        start_nextflow_analysis = /usr/bin/env
        log_base_dir = {tmp_path}/log
        trace_base_dir = {tmp_path}/trace
        work_base_dir = {tmp_path}/work
        base = {base_dir}
        repo = {repo_dir}

        [dna-const]
        runscript = main.nf
        datestamp = false
        singularity_version = 3.8.0
        nextflow_version = 21.10.6
        queue = test
        executor = local
        cluster = local
        container = container.sif

        [somatic]
        runscript = main.nf
        datestamp = false
        singularity_version = 3.8.0
        nextflow_version = 21.10.6
        queue = test
        executor = local
        cluster = local
        container = container.sif
        """
    )
    return settings_config_text


def get_run_profile_config() -> str:

    pipeline_config_text = textwrap.dedent(
        """
        [single]
        pipeline = dna-const
        profile = wgs
        samples = s_proband
        default_panel = itchy_nose
        csv_template = dna_const_single.csv

        [duo]
        pipeline = somatic
        profile = panel-1
        case_type = duo
        samples = s_normal,s_tumor
        sample_types = N,T
        default_panel = pain_in_toe
        csv_template = somatic.csv

        [trio]
        pipeline = dna-const
        profile = wgs
        samples = s_proband,s_mother,s_father
        sample_types = proband,mother,father
        default_panel = stiff_neck
        csv_template = dna_const_trio.csv

        [rna]
        pipeline = dna-const
        profile = wgs
        samples = s_rna
        csv_template = rna_const_single.csv
        """
    )
    return pipeline_config_text


class ConfigSamplePathGroup:
    proband: ConfigSamplePaths
    mother: ConfigSamplePaths
    father: ConfigSamplePaths
    tumor: ConfigSamplePaths
    normal: ConfigSamplePaths

    def __init__(
        self,
        proband: ConfigSamplePaths,
        mother: ConfigSamplePaths,
        father: ConfigSamplePaths,
        tumor: ConfigSamplePaths,
        normal: ConfigSamplePaths,
    ):
        self.proband = proband
        self.mother = mother
        self.father = father
        self.tumor = tumor
        self.normal = normal


def get_sample_config(config_sample_paths: ConfigSamplePathGroup) -> str:

    proband = config_sample_paths.proband
    mother = config_sample_paths.mother
    father = config_sample_paths.father
    tumor = config_sample_paths.tumor
    normal = config_sample_paths.normal

    sample_config_text = textwrap.dedent(
        f"""
        [s_proband]
        clarity_pool_id = 0
        clarity_sample_id = sample01
        sex = M
        fq_fw = {proband.fq_fw}
        fq_rv = {proband.fq_rv}
        bam = {proband.bam}
        vcf = {proband.vcf}

        [s_mother]
        clarity_pool_id = 0
        clarity_sample_id = sample02
        sex = F
        fq_fw = {mother.fq_fw}
        fq_rv = {mother.fq_rv}
        bam = {mother.bam}
        vcf = {mother.vcf}

        [s_father]
        clarity_pool_id = 0
        clarity_sample_id = sample03
        sex = M
        fq_fw = {father.fq_fw}
        fq_rv = {father.fq_rv}
        bam = {father.bam}
        vcf = {father.vcf}

        [s_normal]
        clarity_pool_id = 0
        clarity_sample_id = sample05
        sex = F
        fq_fw = {normal.fq_fw}
        fq_rv = {normal.fq_rv}
        bam = {normal.bam}
        vcf = {normal.vcf}

        [s_tumor]
        clarity_pool_id = 0
        clarity_sample_id = sample04
        sex = F
        fq_fw = {tumor.fq_fw}
        fq_rv = {tumor.fq_rv}
        bam = {tumor.bam}
        vcf = {tumor.vcf}
        """
    )

    return sample_config_text
