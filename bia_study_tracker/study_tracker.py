"""
BIA Study Tracker module for analyzing studies and generating reports.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from prettytable import PrettyTable

from bia_study_tracker.utils.API_client import API
from bia_study_tracker.utils.reports import generate_bia_report, generate_detailed_report_file, BIAReport


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_summary_statistics(report: BIAReport) -> Dict[str, int]:
    return {
        "total_studies": report.total_studies,
        "studies_with_images": report.images.n_with,
        "studies_without_images": report.images.n_without,
        "studies_with_datasets": report.dataset.n_with,
        "studies_without_datasets": report.dataset.n_without,
    }


def format_slack_message(report: Dict[str, Any]) -> str:
    stats = report["summary_stats"]
    table = PrettyTable(["Statistic", "Value"])
    table.align = "l"
    table.add_rows(
        [
            ["Total Studies checked", stats["total_studies"]],
            ["Studies With images", stats["studies_with_images"]],
            ["Studies with datasets but no images", stats["studies_without_images"]],
            ["Studies without datasets", stats["studies_without_datasets"]],
        ]
    )
    return table.get_formatted_string()


class BIAStudyTracker:
    def __init__(self, api_endpoint: Optional[str] = None) -> None:
        endpoint = api_endpoint or os.getenv("PUBLIC_SEARCH_API")
        if not endpoint:
            raise ValueError("API endpoint must be provided (param or PUBLIC_SEARCH_API env var)")
        self.client = API(endpoint)
        self._studies_cache: Optional[List[Dict[str, Any]]] = None
        logger.info(f"BIAStudyTracker initialized with endpoint: {endpoint}")


    @property
    def studies_in_bia(self) -> List[Dict[str, Any]]:
        if self._studies_cache is None:
            self._studies_cache = self.client.get_all_studies_from_search("search/fts?query=")
            logger.info(f"Retrieved {len(self._studies_cache)} studies from BIA")
        return self._studies_cache


    def generate_report(self) -> Tuple[Dict[str, Any], str, Path]:
        report = generate_bia_report(self.studies_in_bia)
        logger.info(f"{report.images.n_without} studies without images (showing up to 10): {report.images.accession_ids_without[:10]}")
        logger.info(f"{report.dataset.n_without} studies without datasets (showing up to 10): {report.dataset.accession_ids_without[:10]}")

        summary = get_summary_statistics(report)
        logger.info(f"Summary: {summary}")

        report_dict = report.to_dict() | {"summary_stats": summary}
        msg = format_slack_message(report_dict)

        path = generate_detailed_report_file(report_dict)
        logger.info(f"Detailed report saved to {path}")

        return report_dict, msg, path