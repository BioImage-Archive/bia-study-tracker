from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
import logging
from bia_ingest.biostudies.api import SearchResult
from bia_study_tracker.settings import get_settings


settings = get_settings()

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
    biostudies: Statistics

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

    def get_summary_statistics(self) -> Dict[str, int]:
        return {
            "Total Studies checked in Search API": self.total_studies,
            "Total Studies checked in Biostudies API (/BioImages)": len(self.biostudies.studies_with) + len(self.biostudies.studies_without),
            "Studies in BioStudies and BIA": len(self.biostudies.studies_with),
            "Studies in BioStudies and not in BIA": len(self.biostudies.studies_without),
            "Studies in BIA with datasets": len(self.dataset.studies_with),
            "Studies in BIA without datasets": len(self.dataset.studies_without),
            "Studies in BIA with images": len(self.image.studies_with),
            "Studies in BIA with datasets but no images": len(self.image.studies_without),
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
    return [with_images, without_images, with_datasets, without_datasets, all_ids]


def _has_images(dataset: Dict[str, Any]) -> bool:
    return dataset.get("image_count", 0) > 0 or bool(dataset.get("image"))


def generate_bia_report(studies_in_bia: List[Dict[str, Any]], studies_in_biostudies: List[SearchResult]) -> BIAReport:
    if not studies_in_bia:
        raise ValueError("Studies list cannot be empty")

    with_imgs, without_imgs, with_ds, without_ds, all_ids = _categorize_studies(studies_in_bia)
    total = len(studies_in_bia)
    in_bia, not_in_bia = [], []
    for study in studies_in_biostudies:
        if study.accession in all_ids:
            in_bia.append(study.accession)
        else:
            not_in_bia.append(study.accession)

    report = BIAReport(
        total_studies=total,
        image=Statistics(with_imgs, without_imgs),
        dataset=Statistics(with_ds, without_ds),
        biostudies=Statistics(in_bia, not_in_bia),
    )
    return report

def has_attribute(image: dict, attr: str) -> bool:
    return attr in [m.get("name") for m in image.get("additional_metadata", [])]

def generate_conversion_report(
    studies: List[Dict[str, Any]],
    images: List[Dict[str, Any]],
    studies_with_images: List[str]
) -> Dict[str, Any]:

    image_lookup = {d["uuid"]: d for d in images}
    report: Dict[str, Any] = {}

    for study in studies:
        accession_id = study["accession_id"]
        if accession_id not in studies_with_images:
            continue

        datasets = study.get("dataset", [])
        study_images = [img for ds in datasets if "image" in ds for img in ds["image"]]
        n_images = len(study_images)

        n_img_rep = n_thumbnail = n_img_rep_have_zarr = 0
        warnings: Dict[str, List[str]] = {
            "missing_rep": [],
            "missing_static_display": [],
            "missing_thumbnail": [],
            "missing_zarr": [],
            "out_of_sync": [],
        }

        example_image_uri = [ds.get("example_image_uri")[0] for ds in study.get("dataset", []) if len(ds.get("example_image_uri")) > 0]
        n_static_display = len(example_image_uri)
        for i in study_images:
            uuid = i.get("uuid")
            img = image_lookup.get(uuid)

            if not img:
                warnings["out_of_sync"].append(uuid)
                continue

            if has_attribute(img, "image_thumbnail_uri"):
                n_thumbnail += 1
            else:
                warnings["missing_thumbnail"].append(uuid)

            if n_static_display == 0:
                warnings["missing_static_display"].append(uuid)

            reps = img.get("representation", [])
            if not reps:
                warnings["missing_rep"].append(uuid)
                continue

            n_img_rep += len(reps)
            n_img_rep_have_zarr += sum(
                1 for rep in reps if rep.get("image_format", "").endswith("ome.zarr")
            )

            if n_img_rep_have_zarr == 0:
                warnings["missing_zarr"].append(uuid)

        # Compact grouped log for this study
        warnings = {k: v for k, v in warnings.items() if v}
        for category, uuids in warnings.items():
            if uuids:
                logger.warning(
                    f"[{accession_id}] {category.replace('_', ' ').title()} "
                    f"({len(uuids)}): {', '.join(uuids[:5])}"
                    f"{' ...' if len(uuids) > 5 else ''}"
                )

        report[accession_id] = {
            "website_url": f"{settings.public_website_url}/{accession_id}",
            "n_images": n_images,
            "n_thumbnail": n_thumbnail,
            "n_static_display": n_static_display,
            "n_img_rep": n_img_rep,
            "n_img_rep_have_zarr": n_img_rep_have_zarr,
            "warnings": warnings if len(warnings)>0 else "",  # keep dict instead of huge string
        }

    return report


def generate_object_for_df(data: List) -> List:
    return [
        [
            acc,
            f"{settings.public_website_url}/{acc}",
            f"https://www.ebi.ac.uk/biostudies/BioImages/studies/{acc}",
        ]
        for acc in data
    ]


def generate_detailed_report_file(
    report: Dict[str, Any],
    conversion_report:  Dict[str, Any],
    output: Path
) -> Path:
    """Generate a detailed Excel report with two sheets:
       - Studies with datasets but no images
       - Studies without datasets
    """
    logging.info(f"Generating detailed report file {output}")
    # Sheet 1: Summary sheet
    df_summary = pd.DataFrame.from_dict(report["summary_stats"], orient="index") \
                  .reset_index() \
                  .rename(columns={"index": report["summary_cols"][0], 0: report["summary_cols"][1]})

    # Sheet 2: studies with datasets but no images
    no_img_data = generate_object_for_df(report["image"]["studies_without"])
    df_no_images = pd.DataFrame(no_img_data, columns=["accession_id", "alpha_url", "original_study_url"])

    # Sheet 3: studies without datasets
    no_ds_data = generate_object_for_df(report["dataset"]["studies_without"])
    df_no_datasets = pd.DataFrame(no_ds_data, columns=["accession_id", "alpha_url", "original_study_url"])

    # Sheet 4: Conversion report
    df_conversion_report = pd.DataFrame.from_dict(conversion_report, orient="index")\
                            .reset_index(names="accession_id")\
                            .sort_values("accession_id")

    sheets_to_add = [(df_summary, "summary_stats"),
                     (df_no_images, "no_images"),
                     (df_no_datasets, "no_datasets"),
                     (df_conversion_report, "conversion_report")]

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for df, sheet in sheets_to_add:
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