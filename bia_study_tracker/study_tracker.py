"""
BIA Study Tracker module for analyzing studies and generating reports.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from bia_study_tracker.utils.API_client import API
from bia_study_tracker.utils.reports import generate_bia_report, generate_detailed_report_file, \
    generate_conversion_report
from bia_study_tracker.settings import get_settings
from datetime import datetime
from bia_ingest.biostudies.find_bia_studies import get_all_bia_studies
from bia_ingest.biostudies.api import SearchResult


logger = logging.getLogger(__name__)

class BIAStudyTracker:
    def __init__(self, api_endpoint: Optional[str] = None) -> None:
        settings = get_settings()
        endpoint = api_endpoint or settings.public_search_api
        if not endpoint:
            raise ValueError("API endpoint must be provided (param or PUBLIC_SEARCH_API env var)")
        self.client = API(endpoint, 100)
        self._studies_cache: Optional[List[Dict[str, Any]]] = None
        self._images_cache: Optional[List[Dict[str, Any]]] = None
        self._biostudies_cache: Optional[List[Dict[str, Any]]] = None
        logger.info(f"BIAStudyTracker initialized with endpoint: {endpoint}")

    @property
    def studies_in_biostudies(self) -> list[SearchResult]:
        if self._biostudies_cache is None:
            self._biostudies_cache = get_all_bia_studies(100)
            logger.info(f"Retrieved {len(self._biostudies_cache)} studies from BioStudies.")
        return self._biostudies_cache

    @property
    def studies_in_bia(self) -> List[Dict[str, Any]]:
        if self._studies_cache is None:
            self._studies_cache = self.client.get_all_objects_from_search("search/fts?query=")
            logger.info(f"Retrieved {len(self._studies_cache)} studies from BIA")
        return self._studies_cache

    @property
    def images_in_bia(self) -> List[Dict[str, Any]]:
        if self._images_cache is None:
            self._images_cache = self.client.get_all_objects_from_search("search/fts/image?query=")
            logger.info(f"Retrieved {len(self._images_cache)} images from BIA")
        return self._images_cache

    def generate_report(self) -> Tuple[Dict[str, Any], Path]:
        report = generate_bia_report(self.studies_in_bia, self.studies_in_biostudies)
        logger.info(f"{len(report.image.studies_without)} studies without images (showing up to 5): {report.image.studies_without[:5]}")
        logger.info(f"{len(report.dataset.studies_without)} studies without datasets (showing up to 5): {report.dataset.studies_without[:5]}")

        summary = report.get_summary_statistics()
        logger.info(f"Summary: {summary}")

        report_dict = report.to_dict() | {"summary_stats": summary, "summary_cols": ["Statistic", "Value"]}
        detailed_report = generate_conversion_report(self.studies_in_bia, self.images_in_bia, report_dict["image"]["studies_with"])
        path = generate_detailed_report_file(report_dict, detailed_report, Path(f"{datetime.now().strftime("%d-%b-%Y")}-detailed_report.xlsx"))
        logger.info(f"Detailed report saved to {path}")

        return report_dict, path