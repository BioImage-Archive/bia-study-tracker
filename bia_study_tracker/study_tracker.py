"""
BIA Study Tracker module for analyzing studies and generating reports.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from bia_study_tracker.utils.API_client import API
from bia_study_tracker.utils.reports import generate_bia_report, generate_detailed_report_file, BIAReport


logger = logging.getLogger(__name__)


def get_summary_statistics(report: BIAReport) -> Dict[str, int]:
    return {
        "Total Studies checked in Search": report.total_studies,
        "Studies with datasets": len(report.dataset.studies_with),
        "Studies without datasets": len(report.dataset.studies_without),
        "Studies with images": len(report.image.studies_with),
        "Studies with datasets but no images": len(report.image.studies_without),
    }

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


    def generate_report(self) -> Tuple[Dict[str, Any], Path]:
        report = generate_bia_report(self.studies_in_bia)
        logger.info(f"{len(report.image.studies_without)} studies without images (showing up to 5): {report.image.studies_without[:5]}")
        logger.info(f"{len(report.dataset.studies_without)} studies without datasets (showing up to 5): {report.dataset.studies_without[:5]}")

        summary = get_summary_statistics(report)
        logger.info(f"Summary: {summary}")

        report_dict = report.to_dict() | {"summary_stats": summary, "summary_cols": ["Statistic", "Value"]}

        path = generate_detailed_report_file(report_dict, Path("detailed_report.xlsx"))
        logger.info(f"Detailed report saved to {path}")

        return report_dict, path