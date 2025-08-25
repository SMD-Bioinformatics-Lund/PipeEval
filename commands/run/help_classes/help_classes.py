from configparser import ConfigParser, SectionProxy
from logging import Logger
from pathlib import Path
import sys
from typing import Dict, List, Optional, Union





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
