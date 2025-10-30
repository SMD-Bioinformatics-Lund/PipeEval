from enum import Enum

MAX_STR_LEN = 50
RUN_ID_PLACEHOLDER = "RUNID"
ASSAY_PLACEHOLDER = "dev"
IS_VCF_PATTERN = ".vcf$|.vcf.gz$"


class VCFType(Enum):
    sv = "sv"
    snv = "snv"
