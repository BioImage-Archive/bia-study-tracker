from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Dict, Any
import pandas as pd
import logging


logger = logging.getLogger(__name__)

@dataclass
class Statistics:
    studies_with: List[str]
    studies_without: List[str]


@dataclass
class BIAReport:
    total_studies: int
    image: Statistics
    dataset: Statistics

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_studies": self.total_studies,
            "image": {
                "studies_with": self.image.studies_with,
                "studies_without": self.image.studies_without,
            },
            "dataset": {
                "studies_with": self.dataset.studies_with,
                "studies_without": self.dataset.studies_without,
            },
        }


def _categorize_studies(studies: List[Dict[str, Any]]) -> List[List[str]]:
    with_images, without_datasets = [], []
    for study in studies:
        acc = study["accession_id"]
        datasets = study.get("dataset")
        if not datasets:
            without_datasets.append(acc)
            continue
        if any(_has_images(ds) for ds in datasets):
            with_images.append(acc)

    all_ids = {study["accession_id"] for study in studies}
    without_images = list(all_ids - set(with_images) - set(without_datasets))
    with_datasets = list(all_ids  - set(without_datasets))
    return [with_images, without_images, with_datasets, without_datasets]


def _has_images(dataset: Dict[str, Any]) -> bool:
    return dataset.get("image_count", 0) > 0 or bool(dataset.get("image"))


def generate_bia_report(studies: List[Dict[str, Any]]) -> BIAReport:
    if not studies:
        raise ValueError("Studies list cannot be empty")

    with_imgs, without_imgs, with_ds, without_ds = _categorize_studies(studies)
    total = len(studies)

    report = BIAReport(
        total_studies=total,
        image=Statistics(with_imgs, without_imgs),
        dataset=Statistics(with_ds, without_ds),
    )
    return report

def generate_object_for_df(data: List) -> List:
    return [
        [
            acc,
            f"https://alpha.bioimagearchive.org/bioimage-archive/study/{acc}",
            f"https://www.ebi.ac.uk/biostudies/BioImages/studies/{acc}",
        ]
        for acc in data
    ]


def generate_detailed_report_file(
    report: Dict[str, Any],
    output: Path
) -> Path:
    """Generate a detailed Excel report with two sheets:
       - Studies with datasets but no images
       - Studies without datasets
    """
    logging.info(f"Generating detailed report file {output}")
    # Sheet 1: studies with datasets but no images
    no_img_data = generate_object_for_df(report["image"]["studies_without"])
    df_no_images = pd.DataFrame(no_img_data, columns=["accession_id", "alpha_url", "original_study_url"])

    # Sheet 2: studies without datasets
    no_ds_data = generate_object_for_df(report["dataset"]["studies_without"])
    df_no_datasets = pd.DataFrame(no_ds_data, columns=["accession_id", "alpha_url", "original_study_url"])

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for df, sheet in [(df_no_images, "no_images"), (df_no_datasets, "no_datasets")]:
            df.to_excel(writer, sheet_name=sheet, index=False)
            workbook = writer.book
            worksheet = writer.sheets[sheet]

            # Bold headers
            header_format = workbook.add_format({"bold": True})
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)

            # Auto-adjust column widths
            for i, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, max_len)
            logger.info(f"Added sheet {sheet} to the detailed report file {output}")

    return output