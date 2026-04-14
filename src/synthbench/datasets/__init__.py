from synthbench.datasets.base import Dataset, Question
from synthbench.datasets.eurobarometer import EurobarometerConsumerDataset
from synthbench.datasets.globalopinionqa import GlobalOpinionQADataset
from synthbench.datasets.gss import GSSDataset
from synthbench.datasets.michigan import MichiganSentimentDataset
from synthbench.datasets.ntia import NTIADataset
from synthbench.datasets.opinionsqa import OpinionsQADataset
from synthbench.datasets.pewtech import PewTechDataset
from synthbench.datasets.subpop import SubPOPDataset
from synthbench.datasets.wvs import WVSDataset

DATASETS: dict[str, type[Dataset]] = {
    "opinionsqa": OpinionsQADataset,
    "globalopinionqa": GlobalOpinionQADataset,
    "subpop": SubPOPDataset,
    "pewtech": PewTechDataset,
    "eurobarometer": EurobarometerConsumerDataset,
    "ntia": NTIADataset,
    "michigan": MichiganSentimentDataset,
    "wvs": WVSDataset,
    "gss": GSSDataset,
}

__all__ = [
    "Dataset",
    "Question",
    "OpinionsQADataset",
    "GlobalOpinionQADataset",
    "SubPOPDataset",
    "PewTechDataset",
    "EurobarometerConsumerDataset",
    "NTIADataset",
    "MichiganSentimentDataset",
    "WVSDataset",
    "GSSDataset",
    "DATASETS",
]
