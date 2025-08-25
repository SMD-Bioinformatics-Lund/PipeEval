from pathlib import Path
import textwrap


def test_import():
    print("Hello")


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


def get_pipeline_config() -> str:
    settings_config_text = textwrap.dedent(
        """
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


def get_profile_config(base_dir: Path, tmp_path: Path) -> str:

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()
    (repo_dir / "nextflow.config").write_text("nextflow")

    pipeline_config_text = textwrap.dedent(
        f"""
        [single]
        pipeline = dna-const
        profile = wgs
        sample_type = single
        samples = proband
        default_panel = OMIM

        [duo]
        pipeline = somatic
        profile = panel-1
        sample_type = duo
        samples = tumor,normal
        default_panel = OMIM

        [trio]
        pipeline = dna-const
        profile = wgs
        sample_type = trio
        samples = proband,mother,father
        default_panel = OMIM
        """
    )
    return pipeline_config_text


def get_sample_config(tmp_path: Path) -> str:

    # Dummy input files
    proband = ConfigSamplePaths(tmp_path, "proband")
    mother = ConfigSamplePaths(tmp_path, "mother")
    father = ConfigSamplePaths(tmp_path, "father")
    tumor = ConfigSamplePaths(tmp_path, "tumor")
    normal = ConfigSamplePaths(tmp_path, "normal")

    sample_config_text = textwrap.dedent(
        f"""
        [proband]
        id = proband
        clarity_pool_id = 0
        clarity_sample_id = sample01
        sex = M
        type = proband
        fq_fw = {proband.fq_fw}
        fq_rv = {proband.fq_rv}
        bam = {proband.bam}
        vcf = {proband.vcf}

        [mother]
        id = sample_mother
        clarity_pool_id = 0
        clarity_sample_id = sample02
        sex = F
        type = mother
        fq_fw = {mother.fq_fw}
        fq_rv = {mother.fq_rv}
        bam = {mother.bam}
        vcf = {mother.vcf}

        [father]
        id = sample_father
        clarity_pool_id = 0
        clarity_sample_id = sample03
        sex = M
        type = father
        fq_fw = {father.fq_fw}
        fq_rv = {father.fq_rv}
        bam = {father.bam}
        vcf = {father.vcf}

        [tumor]
        id = sample_tumor
        clarity_pool_id = 0
        clarity_sample_id = sample04
        sex = F
        type = tumor
        fq_fw = {tumor.fq_fw}
        fq_rv = {tumor.fq_rv}
        bam = {tumor.bam}
        vcf = {tumor.vcf}

        [normal]
        id = sample_normal
        clarity_pool_id = 0
        clarity_sample_id = sample05
        sex = F
        type = normal
        fq_fw = {normal.fq_fw}
        fq_rv = {normal.fq_rv}
        bam = {normal.bam}
        vcf = {normal.vcf}
        """
    )

    return sample_config_text
