from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Dict, Any
import pandas as pd


@dataclass
class Statistics:
    n_with: int
    n_without: int
    accession_ids_without: List[str]


@dataclass
class BIAReport:
    total_studies: int
    images: Statistics
    dataset: Statistics

    def to_dict(self) -> Dict[str, Any]:
        return {
            "Total studies checked": self.total_studies,
            "images": {
                "with": self.images.n_with,
                "without": self.images.n_without,
                "studies_without_images_accession_ids": self.images.accession_ids_without,
            },
            "dataset": {
                "with": self.dataset.n_with,
                "without": self.dataset.n_without,
                "studies_without_datasets_accession_ids": self.dataset.accession_ids_without,
            },
        }


def _categorize_studies(studies: List[Dict[str, Any]]) -> Tuple[List[str], List[str], List[str]]:
    with_images, without_datasets = [], []
    for hit in studies:
        study = hit["_source"]
        acc = study["accession_id"]
        datasets = study.get("dataset")
        if not datasets:
            without_datasets.append(acc)
            continue
        if any(_has_images(ds) for ds in datasets):
            with_images.append(acc)

    all_ids = {hit["_source"]["accession_id"] for hit in studies}
    without_images = list(all_ids - set(with_images) - set(without_datasets))
    return with_images, without_images, without_datasets


def _has_images(dataset: Dict[str, Any]) -> bool:
    return dataset.get("image_count", 0) > 0 or bool(dataset.get("image"))


def generate_bia_report(studies: List[Dict[str, Any]]) -> BIAReport:
    if not studies:
        raise ValueError("Studies list cannot be empty")

    with_imgs, without_imgs, without_datasets = _categorize_studies(studies)
    total = len(studies)
    with_datasets = total - len(without_datasets)

    report = BIAReport(
        total_studies=total,
        images=Statistics(len(with_imgs), len(without_imgs), without_imgs),
        dataset=Statistics(with_datasets, len(without_datasets), without_datasets),
    )
    return report


def generate_detailed_report_file(
    report: Dict[str, Any],
    output: Path = Path("detailed_report.xlsx")
) -> Path:
    """Generate a detailed Excel report with two sheets:
       - Studies with datasets but no images
       - Studies without datasets
    """
    # Sheet 1: studies with datasets but no images
    no_img_data = [
        [
            acc,
            f"https://alpha.bioimagearchive.org/bioimage-archive/study/{acc}",
            f"https://www.ebi.ac.uk/biostudies/BioImages/studies/{acc}",
        ]
        for acc in report["images"]["studies_without_images_accession_ids"]
    ]
    df_no_images = pd.DataFrame(no_img_data, columns=["accession_id", "alpha_url", "original_study_url"])

    # Sheet 2: studies without datasets
    no_ds_data = [
        [
            acc,
            f"https://alpha.bioimagearchive.org/bioimage-archive/study/{acc}",
            f"https://www.ebi.ac.uk/biostudies/BioImages/studies/{acc}",
        ]
        for acc in report["dataset"]["studies_without_datasets_accession_ids"]
    ]
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

    return output