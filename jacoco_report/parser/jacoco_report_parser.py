"""
A module for parsing JaCoCo XML reports and creating CoverageReport instances.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Optional

from jacoco_report.model.counter import Counter
from jacoco_report.model.coverage import Coverage
from jacoco_report.model.module import Module
from jacoco_report.model.report_file_coverage import ReportFileCoverage
from jacoco_report.model.file_coverage import FileCoverage

logger = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class JaCoCoReportParser:
    """
    A class for parsing JaCoCo XML reports and creating CoverageReport instances.
    """

    def __init__(self, changed_files: list[str], modules: dict[str, Module]):
        self._changed_files: list[str] = changed_files
        self._modules: dict[str, Module] = modules

    def parse(self, report_path: str) -> ReportFileCoverage:
        """
        Parses the JaCoCo XML report and creates a CoverageReport instance.

        Parameters:
            report_path: The path to the JaCoCo XML report.

        Returns:
            A CoverageReport instance.
        """
        logger.debug("Parsing JaCoCo XML report: %s", report_path)
        tree: ET.ElementTree = ET.parse(report_path)
        root: ET.Element = tree.getroot()

        # check name attribute exists
        if "name" not in root.attrib:
            logger.error("Failed to find name attribute in JaCoCo report: %s", {report_path})
            name = report_path
        else:
            name = root.attrib["name"]

        # Extract overall stats and changed files stats from the XML
        overall_stats: Coverage = self._extract_overall_stats(root)
        changed_files_stats: dict[str, FileCoverage] = self._extract_changed_files_stats(root)

        # detect module name
        if self._modules != {}:
            module_name = self._detect_module_name(report_path)
        else:
            module_name = None

        return ReportFileCoverage(report_path, name, overall_stats, changed_files_stats, module_name)

    def _extract_overall_stats(self, root: ET.Element) -> Coverage:
        """
        Extracts overall coverage statistics from the XML root.

        Paramaters:
            root: The root of the XML tree

        Returns:
            A dictionary containing the overall coverage statistics
        """
        logger.debug("Extracting overall coverage statistics from JaCoCo report.")
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
            res = root.find(f"counter[@type='{counter_type}']").attrib[counter_name]
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

    def _extract_changed_files_stats(self, root: ET.Element) -> dict:
        """
        Extracts changed files coverage statistics from the XML root.

        Paramaters:
            root: The root of the XML tree

        Returns:
            A dictionary containing the changed files coverage statistics
        """
        logger.debug("Extracting changed files coverage statistics from JaCoCo report.")
        changed_files_stats = {}

        for pck in root.findall("package"):
            logger.debug("Package: %s", pck.attrib["name"])
            for src_file in pck.findall("sourcefile"):
                file_path = pck.attrib["name"]
                file_name = src_file.attrib["name"]

                key = f"{file_path}/{file_name}"
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

    def _detect_module_name(self, report_path: str) -> Optional[str]:
        """
        Detects the module name from the report path.

        Parameters:
            report_path: The path to the JaCoCo XML report.

        Returns:
            The module name.
        """
        logger.debug("Detecting module name from report path.")

        for module_name, module in self._modules.items():
            if f"/{module.root_path}/" in report_path:
                return module_name

        logger.error("No module name detected for module path: %s", report_path)
        return None
