"""
A module for parsing JaCoCo XML reports and creating CoverageReport instances.
"""

import logging
import os
import xml.etree.ElementTree as ET
from typing import Optional

from jacoco_report.model.counter import Counter
from jacoco_report.model.coverage import Coverage
from jacoco_report.model.report_file_coverage import ReportFileCoverage
from jacoco_report.model.file_coverage import FileCoverage

logger = logging.getLogger(__name__)


class JaCoCoReportParser:
    """
    A class for parsing JaCoCo XML reports and creating CoverageReport instances.
    """

    def __init__(self, changed_files: list[str]):
        self._changed_files: list[str] = changed_files

    def parse(self, report_path: str, group_name: Optional[str] = None) -> ReportFileCoverage:
        """
        Parses the JaCoCo XML report and creates a ReportFileCoverage instance.

        Parameters:
            report_path: The path to the JaCoCo XML report.
            group_name: The report group this report belongs to (None if no groups configured).

        Returns:
            A ReportFileCoverage instance.
        """
        logger.debug("Parsing JaCoCo XML report: %s", report_path)
        tree: ET.ElementTree[ET.Element] = ET.parse(report_path)
        root: Optional[ET.Element] = tree.getroot()

        # check name attribute exists
        if root is not None and "name" not in root.attrib:
            logger.error("Failed to find name attribute in JaCoCo report: %s", {report_path})
            name = report_path
        else:
            name = root.attrib["name"] if root is not None else report_path

        # Extract overall stats and changed files stats from the XML
        overall_stats: Coverage = self._extract_overall_stats(root)
        changed_files_stats: dict[str, FileCoverage] = self._extract_changed_files_stats(root)

        return ReportFileCoverage(report_path, name, overall_stats, changed_files_stats, group_name)

    def _extract_overall_stats(self, root: Optional[ET.Element]) -> Coverage:
        """
        Extracts overall coverage statistics from the XML root.

        Paramaters:
            root: The root of the XML tree

        Returns:
            A dictionary containing the overall coverage statistics
        """
        logger.debug("Extracting overall coverage statistics from JaCoCo report.")

        if root is None:
            logger.error("Root element is None. Cannot extract overall stats.")
            return Coverage(
                instruction=Counter(missed=0, covered=0),
                branch=Counter(missed=0, covered=0),
                line=Counter(missed=0, covered=0),
                complexity=Counter(missed=0, covered=0),
                method=Counter(missed=0, covered=0),
                clazz=Counter(missed=0, covered=0),
            )

        instruction: Counter = Counter(
            missed=self.__get_int(root, "INSTRUCTION", "missed"),
            covered=self.__get_int(root, "INSTRUCTION", "covered"),
        )
        branch: Counter = Counter(
            missed=self.__get_int(root, "BRANCH", "missed"),
            covered=self.__get_int(root, "BRANCH", "covered"),
        )
        line: Counter = Counter(
            missed=self.__get_int(root, "LINE", "missed"),
            covered=self.__get_int(root, "LINE", "covered"),
        )
        complexity: Counter = Counter(
            missed=self.__get_int(root, "COMPLEXITY", "missed"),
            covered=self.__get_int(root, "COMPLEXITY", "covered"),
        )
        method: Counter = Counter(
            missed=self.__get_int(root, "METHOD", "missed"),
            covered=self.__get_int(root, "METHOD", "covered"),
        )
        clazz: Counter = Counter(
            missed=self.__get_int(root, "CLASS", "missed"),
            covered=self.__get_int(root, "CLASS", "covered"),
        )

        overall_stats = Coverage(instruction, branch, line, complexity, method, clazz)
        return overall_stats

    def __get_int(self, root: ET.Element, counter_type: str, counter_name: str) -> int:
        try:
            elem = root.find(f"counter[@type='{counter_type}']")
            res = elem.attrib[counter_name] if elem is not None else 0
            return int(res)
        except AttributeError:
            logger.warning("Failed to find %s counter in JaCoCo report. Zero will be used.", counter_type)
            return 0
        except KeyError:
            logger.error("Failed to find %s counter in JaCoCo report.", counter_type)
            return 0
        except ValueError:
            logger.error("Failed to parse %s counter from JaCoCo report.", counter_type)
            return 0

    def _extract_changed_files_stats(self, root: Optional[ET.Element]) -> dict[str, FileCoverage]:
        """
        Extracts changed files coverage statistics from the XML root.

        Paramaters:
            root: The root of the XML tree

        Returns:
            A dictionary containing the changed files coverage statistics
        """

        def find_file(root_dir: str, relative_path: str) -> list[str]:
            paths: list[str] = []
            for dirpath, *_ in os.walk(root_dir):
                full_path = os.path.join(dirpath, relative_path)
                if os.path.isfile(full_path):
                    paths.append(os.path.relpath(full_path, root_dir))
            return paths

        logger.debug("Extracting changed files coverage statistics from JaCoCo report.")
        changed_files_stats = dict[str, FileCoverage]()

        if root is None:
            logger.error("Root element is None. Cannot extract changed files stats.")
            return changed_files_stats

        for pck in root.findall("package"):
            logger.debug("Package: %s", pck.attrib["name"])
            for src_file in pck.findall("sourcefile"):
                file_path = pck.attrib["name"]
                file_name = src_file.attrib["name"]

                keys: list[str] = find_file(os.getcwd(), f"{file_path}/{file_name}")
                if len(keys) == 0:
                    logger.debug(
                        "File '%s/%s' not found in the repository. Working directory: %s",
                        file_path,
                        file_name,
                        os.getcwd(),
                    )
                    keys.append(f"{file_path}/{file_name}")

                for key in keys:
                    if any(key in changed_file for changed_file in self._changed_files):
                        logger.debug("File '%s' is in the list of changed files.", key)
                        file_coverage = FileCoverage(
                            file_path=file_path,
                            file_name=file_name,
                            instruction=Counter(
                                missed=self.__get_int(src_file, "INSTRUCTION", "missed"),
                                covered=self.__get_int(src_file, "INSTRUCTION", "covered"),
                            ),
                            branch=Counter(
                                missed=self.__get_int(src_file, "BRANCH", "missed"),
                                covered=self.__get_int(src_file, "BRANCH", "covered"),
                            ),
                            line=Counter(
                                missed=self.__get_int(src_file, "LINE", "missed"),
                                covered=self.__get_int(src_file, "LINE", "covered"),
                            ),
                            complexity=Counter(
                                missed=self.__get_int(src_file, "COMPLEXITY", "missed"),
                                covered=self.__get_int(src_file, "COMPLEXITY", "covered"),
                            ),
                            method=Counter(
                                missed=self.__get_int(src_file, "METHOD", "missed"),
                                covered=self.__get_int(src_file, "METHOD", "covered"),
                            ),
                            clazz=Counter(
                                missed=self.__get_int(src_file, "CLASS", "missed"),
                                covered=self.__get_int(src_file, "CLASS", "covered"),
                            ),
                        )

                        changed_files_stats[key] = file_coverage
                    else:
                        logger.debug("File '%s' is not in the list of changed files.", key)

        return changed_files_stats

