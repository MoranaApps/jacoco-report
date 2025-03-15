"""
A module for scanning input paths for JaCoCo XML files and excluding specified paths.
"""

import glob
import logging
import os

logger = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class JaCoCoReportInputScanner:
    """
    A class for scanning input paths for JaCoCo XML files and excluding specified paths.
    """

    def __init__(self, paths: list[str], exclude_paths: list[str]):
        self.paths: list[str] = paths
        self.exclude_paths: list[str] = exclude_paths

    def scan(self) -> list[str]:
        """
        Scans the input paths for JaCoCo XML files and excludes specified paths.
        Returns a list of absolute paths to the JaCoCo XML files.
        """
        jacoco_files = set()

        # Scan for JaCoCo XML files in the input paths
        for path in self.paths:
            resolved_paths = glob.glob(path, root_dir=".", recursive=True)
            for resolved_path in resolved_paths:
                abs_path = os.path.abspath(resolved_path)

                if os.path.isfile(abs_path) and abs_path.endswith(".xml"):
                    logger.debug("Found 'xml' file: %s", abs_path)
                    jacoco_files.add(abs_path)

        # Exclude specified paths
        for exclude_path in self.exclude_paths:
            for file in glob.glob(exclude_path, recursive=True):
                if file.endswith(".xml"):
                    jacoco_files.discard(os.path.abspath(file))

        return list(jacoco_files)
