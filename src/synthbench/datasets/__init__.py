from synthbench.datasets.base import Dataset, Question
from synthbench.datasets.opinionsqa import OpinionsQADataset

DATASETS: dict[str, type[Dataset]] = {
    "opinionsqa": OpinionsQADataset,
}

__all__ = ["Dataset", "Question", "OpinionsQADataset", "DATASETS"]
