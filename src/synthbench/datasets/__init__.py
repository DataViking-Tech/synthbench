from synthbench.datasets.base import Dataset, Question
from synthbench.datasets.eurobarometer import EurobarometerConsumerDataset
from synthbench.datasets.globalopinionqa import GlobalOpinionQADataset
from synthbench.datasets.opinionsqa import OpinionsQADataset
from synthbench.datasets.pewtech import PewTechDataset
from synthbench.datasets.subpop import SubPOPDataset

DATASETS: dict[str, type[Dataset]] = {
    "opinionsqa": OpinionsQADataset,
    "globalopinionqa": GlobalOpinionQADataset,
    "subpop": SubPOPDataset,
    "pewtech": PewTechDataset,
    "eurobarometer": EurobarometerConsumerDataset,
}

__all__ = [
    "Dataset",
    "Question",
    "OpinionsQADataset",
    "GlobalOpinionQADataset",
    "SubPOPDataset",
    "PewTechDataset",
    "EurobarometerConsumerDataset",
    "DATASETS",
]
