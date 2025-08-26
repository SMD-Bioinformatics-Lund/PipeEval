from shared.compare import Comparison
from shared.vcf.vcf import ScoredVCF


class VCFPair:
    vcf1: ScoredVCF
    vcf2: ScoredVCF
    comp: Comparison[str]

    def __init__(self, vcf1: ScoredVCF, vcf2: ScoredVCF, comp: Comparison[str]):
        self.vcf1 = vcf1
        self.vcf2 = vcf2
        self.comp = comp
