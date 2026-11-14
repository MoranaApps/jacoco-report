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


def _matches_changed_file(key: str, changed_file: str) -> bool:
    """A report path matches a changed file when it is the whole path or ends it on a directory boundary."""
    return changed_file == key or changed_file.endswith("/" + key)


def _index_workspace_files(root_dir: str) -> dict[str, list[str]]:
    """
    Maps each file name under root_dir to its forward-slash paths relative to root_dir.

    The .git directory is skipped, and directory symlinks are not followed (os.walk default).
    """
    index: dict[str, list[str]] = {}
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [name for name in dirnames if name != ".git"]
        for file_name in filenames:
            relative_path = os.path.relpath(os.path.join(dirpath, file_name), root_dir)
            index.setdefault(file_name, []).append(relative_path.replace(os.sep, "/"))
    return index


class JaCoCoReportParser:
    """
    A class for parsing JaCoCo XML reports and creating CoverageReport instances.
    """

    def __init__(self, changed_files: list[str]):
        self._changed_files: list[str] = changed_files
        # Built on the first source file lookup, then shared by every report this parser reads.
        self._workspace_index: Optional[dict[str, list[str]]] = None

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

    def _find_workspace_paths(self, file_name: str, relative_path: str) -> list[str]:
        """
        Finds the workspace paths of a source file, matched by file name and the directory-boundary rule.

        Parameters:
            file_name: The source file name from the report.
            relative_path: The report's package path plus file name (e.g. "com/example/Example.java").

        Returns:
            The matching forward-slash workspace paths, empty if none exist.
        """
        if self._workspace_index is None:
            workspace = os.getcwd()
            self._workspace_index = _index_workspace_files(workspace)
            logger.debug(
                "Indexed %d files under working directory %s",
                sum(len(paths) for paths in self._workspace_index.values()),
                workspace,
            )
        return [path for path in self._workspace_index.get(file_name, []) if _matches_changed_file(relative_path, path)]

    def _extract_changed_files_stats(self, root: Optional[ET.Element]) -> dict[str, FileCoverage]:
        """
        Extracts changed files coverage statistics from the XML root.

        Paramaters:
            root: The root of the XML tree

        Returns:
            A dictionary containing the changed files coverage statistics
        """

        logger.debug("Extracting changed files coverage statistics from JaCoCo report.")
        changed_files_stats = dict[str, FileCoverage]()

        if root is None:
            logger.error("Root element is None. Cannot extract changed files stats.")
            return changed_files_stats

        # Packages sit directly under <report> or inside <group> elements nested to any depth
        # (e.g. Maven jacoco:report-aggregate wraps each module in a <group>).
        for pck in root.iter("package"):
            logger.debug("Package: %s", pck.attrib["name"])
            for src_file in pck.findall("sourcefile"):
                file_path = pck.attrib["name"]
                file_name = src_file.attrib["name"]
                # The default package has an empty name; a leading "/" would never match a changed file.
                relative_path = f"{file_path}/{file_name}" if file_path else file_name

                keys: list[str] = self._find_workspace_paths(file_name, relative_path)
                if len(keys) == 0:
                    logger.debug(
                        "File '%s' not found in the repository. Working directory: %s",
                        relative_path,
                        os.getcwd(),
                    )
                    keys.append(relative_path)

                for key in keys:
                    if any(_matches_changed_file(key, changed_file) for changed_file in self._changed_files):
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
