from synthbench.datasets.base import Dataset, Question
from synthbench.datasets.opinionsqa import OpinionsQADataset
from synthbench.datasets.globalopinionqa import GlobalOpinionQADataset

DATASETS: dict[str, type[Dataset]] = {
    "opinionsqa": OpinionsQADataset,
    "globalopinionqa": GlobalOpinionQADataset,
}

__all__ = [
    "Dataset",
    "Question",
    "OpinionsQADataset",
    "GlobalOpinionQADataset",
    "DATASETS",
]
