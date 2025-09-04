import json
import logging
import os

import pytest
from unittest.mock import patch

from jacoco_report.jacoco_report import JaCoCoReport
from jacoco_report.action_inputs import ActionInputs
from jacoco_report.utils.enums import SensitivityEnum, CommentModeEnum, MetricTypeEnum

comment_no_data_no_baseline = """**JaCoCo Coverage Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 0.0% | 0.0% | ✅ |
| **Changed Files** | 0.0% | 0.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|--------|
| `Module B Report` | 0.0% / 0.0% | 0.0% / 0.0% | ✅/✅ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|

No changed file in reports."""

comment_no_data_with_baseline = """**JaCoCo Coverage Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 0.0% | 0.0% | 0.0% | ✅ |
| **Changed Files** | 0.0% | 0.0% | 0.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `Module B Report` | 0.0% / 0.0% | 0.0% / 0.0% | 0.0% / 0.0% | ✅/✅ |

| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|

No changed file in reports."""

comment_one_file_single_detailed = """TODO"""
comment_one_file_multi_detailed = """TODO"""
comment_one_file_module_detailed = """TODO"""

comment_one_file_single_summary = """TODO"""
comment_one_file_multi_summary = """TODO"""
comment_one_file_module_summary = """TODO"""

comment_one_file_single_minimalist_instruction = """**Custom Title**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 90.0% | 0.0% | ✅ |
| **Changed Files** | 80.0% | 0.0% | ✅ |"""

comment_one_file_single_minimalist_line = """**Custom Title**

| Metric (line) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 80.0% | 0.0% | ✅ |
| **Changed Files** | 60.0% | 0.0% | ✅ |"""

comment_one_file_single_minimalist_branch = """**Custom Title**

| Metric (branch) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 75.0% | 0.0% | ✅ |
| **Changed Files** | 0.0% | 0.0% | ✅ |"""

comment_one_file_single_minimalist_complexity = """**Custom Title**

| Metric (complexity) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 75.0% | 0.0% | ✅ |
| **Changed Files** | 50.0% | 0.0% | ✅ |"""

comment_one_file_single_minimalist_method = """**Custom Title**

| Metric (method) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 100.0% | 0.0% | ✅ |
| **Changed Files** | 0.0% | 0.0% | ✅ |"""

comment_one_file_single_minimalist_class = """**Custom Title**

| Metric (class) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 100.0% | 0.0% | ✅ |
| **Changed Files** | 0.0% | 0.0% | ✅ |"""

comment_one_file_multi_minimalist = """TODO"""
comment_one_file_module_minimalist = """TODO"""

comment_single_minimalist_instruction = """**JaCoCo Coverage Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 92.0% | 75.0% | ✅ |
| **Changed Files** | 89.71% | 80.0% | ✅ |"""

comment_single_minimalist_instruction_summary = """**JaCoCo Coverage Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 92.0% | 75.0% | ✅ |
| **Changed Files** | 89.71% | 80.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|--------|
| `Module Large Report` | 91.33% / 90.0% | 75.0% / 80.0% | ✅/✅ |
| `Module Small Report` | 97.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `notification: API Module Report` | 95.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `notification: Client HTTP Module Report` | 90.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `notification: Plugins Module Report` | 92.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `user-info:  Controller Module Report` | 93.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `user-info: API Module Report` | 95.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 75.0% / 80.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 75.0% / 80.0% | ✅/✅ |"""

comment_single_minimalist_instruction_with_bs = """**JaCoCo Coverage Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 92.0% | 75.0% | +6.9% | ✅ |
| **Changed Files** | 89.71% | 80.0% | +9.0% | ✅ |"""

comment_single_minimalist_instruction_with_bs_summary = """**JaCoCo Coverage Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 92.0% | 75.0% | +6.9% | ✅ |
| **Changed Files** | 89.71% | 80.0% | +9.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `Module Large Report` | 91.33% / 90.0% | 75.0% / 80.0% | -4.17% / -5.0% | ✅/✅ |
| `Module Small Report` | 97.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `notification: API Module Report` | 95.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `notification: Client HTTP Module Report` | 90.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `notification: Plugins Module Report` | 92.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `user-info:  Controller Module Report` | 93.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `user-info: API Module Report` | 95.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 75.0% / 80.0% | +80.0% / +80.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 75.0% / 80.0% | +8.0% / +8.0% | ✅/✅ |"""

comment_more_files_single_summary_instruction_with_modules = """**JaCoCo Coverage Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 92.0% | 75.0% | ✅ |
| **Changed Files** | 89.71% | 80.0% | ✅ |

| Module | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|-----------------|------------------|---------------|
| `context/notification` | 92.33% / 0.0% | 22.0% / 60.0% | ✅/✅ |
| `context/user-info` | 91.5% / 89.0% | 21.0% / 59.0% | ✅/✅ |
| `module_large` | 91.33% / 90.0% | 20.0% / 91.0% | ✅/❌ |
| `module small` | 97.0% / 0.0% | 29.0% / 37.0% | ✅/✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|--------|
| `Module Large Report` | 91.33% / 90.0% | 20.0% / 91.0% | ✅/❌ |
| `Module Small Report` | 97.0% / 0.0% | 29.0% / 37.0% | ✅/✅ |
| `notification: API Module Report` | 95.0% / 0.0% | 22.0% / 60.0% | ✅/✅ |
| `notification: Client HTTP Module Report` | 90.0% / 0.0% | 22.0% / 60.0% | ✅/✅ |
| `notification: Plugins Module Report` | 92.0% / 0.0% | 22.0% / 60.0% | ✅/✅ |
| `user-info:  Controller Module Report` | 93.0% / 0.0% | 21.0% / 59.0% | ✅/✅ |
| `user-info: API Module Report` | 95.0% / 0.0% | 21.0% / 59.0% | ✅/✅ |
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 21.0% / 59.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 21.0% / 59.0% | ✅/✅ |"""

comment_more_files_single_summary_instruction_with_modules_with_bs = """**JaCoCo Coverage Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 92.0% | 75.0% | +6.9% | ✅ |
| **Changed Files** | 89.71% | 80.0% | +9.0% | ✅ |

| Module | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|-----------------|------------------|---------------|---------------|
| `context/notification` | 92.33% / 0.0% | 22.0% / 60.0% | +92.33% / 0.0% | ✅/✅ |
| `context/user-info` | 91.5% / 89.0% | 21.0% / 59.0% | +22.0% / +44.0% | ✅/✅ |
| `module_large` | 91.33% / 90.0% | 20.0% / 91.0% | -4.17% / -5.0% | ✅/❌ |
| `module small` | 97.0% / 0.0% | 29.0% / 37.0% | +97.0% / 0.0% | ✅/✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `Module Large Report` | 91.33% / 90.0% | 20.0% / 91.0% | -4.17% / -5.0% | ✅/❌ |
| `Module Small Report` | 97.0% / 0.0% | 29.0% / 37.0% | 0.0% / 0.0% | ✅/✅ |
| `notification: API Module Report` | 95.0% / 0.0% | 22.0% / 60.0% | 0.0% / 0.0% | ✅/✅ |
| `notification: Client HTTP Module Report` | 90.0% / 0.0% | 22.0% / 60.0% | 0.0% / 0.0% | ✅/✅ |
| `notification: Plugins Module Report` | 92.0% / 0.0% | 22.0% / 60.0% | 0.0% / 0.0% | ✅/✅ |
| `user-info:  Controller Module Report` | 93.0% / 0.0% | 21.0% / 59.0% | 0.0% / 0.0% | ✅/✅ |
| `user-info: API Module Report` | 95.0% / 0.0% | 21.0% / 59.0% | 0.0% / 0.0% | ✅/✅ |
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 21.0% / 59.0% | +80.0% / +80.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 21.0% / 59.0% | +8.0% / +8.0% | ✅/✅ |"""

comment_more_files_single_summary_instruction_with_modules_no_module_thresholds = """**JaCoCo Coverage Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 92.0% | 75.0% | ✅ |
| **Changed Files** | 89.71% | 80.0% | ✅ |

| Module | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|-----------------|------------------|---------------|
| `context/notification` | 92.33% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `context/user-info` | 91.5% / 89.0% | 75.0% / 80.0% | ✅/✅ |
| `module_large` | 91.33% / 90.0% | 75.0% / 80.0% | ✅/✅ |
| `module small` | 97.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|--------|
| `Module Large Report` | 91.33% / 90.0% | 75.0% / 80.0% | ✅/✅ |
| `Module Small Report` | 97.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `notification: API Module Report` | 95.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `notification: Client HTTP Module Report` | 90.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `notification: Plugins Module Report` | 92.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `user-info:  Controller Module Report` | 93.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `user-info: API Module Report` | 95.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 75.0% / 80.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 75.0% / 80.0% | ✅/✅ |"""

comment_more_files_single_summary_instruction_with_modules_no_module_thresholds_with_bs = """**JaCoCo Coverage Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 92.0% | 75.0% | +6.9% | ✅ |
| **Changed Files** | 89.71% | 80.0% | +9.0% | ✅ |

| Module | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|-----------------|------------------|---------------|---------------|
| `context/notification` | 92.33% / 0.0% | 75.0% / 80.0% | +92.33% / 0.0% | ✅/✅ |
| `context/user-info` | 91.5% / 89.0% | 75.0% / 80.0% | +22.0% / +44.0% | ✅/✅ |
| `module_large` | 91.33% / 90.0% | 75.0% / 80.0% | -4.17% / -5.0% | ✅/✅ |
| `module small` | 97.0% / 0.0% | 75.0% / 80.0% | +97.0% / 0.0% | ✅/✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `Module Large Report` | 91.33% / 90.0% | 75.0% / 80.0% | -4.17% / -5.0% | ✅/✅ |
| `Module Small Report` | 97.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `notification: API Module Report` | 95.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `notification: Client HTTP Module Report` | 90.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `notification: Plugins Module Report` | 92.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `user-info:  Controller Module Report` | 93.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `user-info: API Module Report` | 95.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 75.0% / 80.0% | +80.0% / +80.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 75.0% / 80.0% | +8.0% / +8.0% | ✅/✅ |"""

comment_more_files_single_detailed_instruction_no_modules = """**JaCoCo Coverage Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 92.0% | 75.0% | ✅ |
| **Changed Files** | 89.71% | 80.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|--------|
| `Module Large Report` | 91.33% / 90.0% | 75.0% / 80.0% | ✅/✅ |
| `Module Small Report` | 97.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `notification: API Module Report` | 95.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `notification: Client HTTP Module Report` | 90.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `notification: Plugins Module Report` | 92.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `user-info:  Controller Module Report` | 93.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `user-info: API Module Report` | 95.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 75.0% / 80.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 75.0% / 80.0% | ✅/✅ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|
| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 65.0% | ✅ |
| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 65.0% | ✅ |
| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 65.0% | ✅ |"""

comment_more_files_single_detailed_instruction_no_modules_with_bs = """**JaCoCo Coverage Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 92.0% | 75.0% | +6.9% | ✅ |
| **Changed Files** | 89.71% | 80.0% | +9.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `Module Large Report` | 91.33% / 90.0% | 75.0% / 80.0% | -4.17% / -5.0% | ✅/✅ |
| `Module Small Report` | 97.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `notification: API Module Report` | 95.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `notification: Client HTTP Module Report` | 90.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `notification: Plugins Module Report` | 92.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `user-info:  Controller Module Report` | 93.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `user-info: API Module Report` | 95.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 75.0% / 80.0% | +80.0% / +80.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 75.0% / 80.0% | +8.0% / +8.0% | ✅/✅ |

| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 65.0% | -5.0% | ✅ |
| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 65.0% | +80.0% | ✅ |
| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 65.0% | +8.0% | ✅ |"""

comment_more_files_single_detailed_instruction_with_modules = """**JaCoCo Coverage Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 92.0% | 75.0% | ✅ |
| **Changed Files** | 89.71% | 80.0% | ✅ |

| Module | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|-----------------|------------------|---------------|
| `context/notification` | 92.33% / 0.0% | 22.0% / 60.0% | ✅/✅ |
| `context/user-info` | 91.5% / 89.0% | 21.0% / 59.0% | ✅/✅ |
| `module_large` | 91.33% / 90.0% | 20.0% / 91.0% | ✅/❌ |
| `module small` | 97.0% / 0.0% | 29.0% / 37.0% | ✅/✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|--------|
| `Module Large Report` | 91.33% / 90.0% | 20.0% / 91.0% | ✅/❌ |
| `Module Small Report` | 97.0% / 0.0% | 29.0% / 37.0% | ✅/✅ |
| `notification: API Module Report` | 95.0% / 0.0% | 22.0% / 60.0% | ✅/✅ |
| `notification: Client HTTP Module Report` | 90.0% / 0.0% | 22.0% / 60.0% | ✅/✅ |
| `notification: Plugins Module Report` | 92.0% / 0.0% | 22.0% / 60.0% | ✅/✅ |
| `user-info:  Controller Module Report` | 93.0% / 0.0% | 21.0% / 59.0% | ✅/✅ |
| `user-info: API Module Report` | 95.0% / 0.0% | 21.0% / 59.0% | ✅/✅ |
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 21.0% / 59.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 21.0% / 59.0% | ✅/✅ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|
| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 90.5% | ❌ |
| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 55.0% | ✅ |
| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 55.0% | ✅ |"""

comment_more_files_single_detailed_instruction_with_modules_with_bs = """**JaCoCo Coverage Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 92.0% | 75.0% | +6.9% | ✅ |
| **Changed Files** | 89.71% | 80.0% | +9.0% | ✅ |

| Module | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|-----------------|------------------|---------------|---------------|
| `context/notification` | 92.33% / 0.0% | 22.0% / 60.0% | +92.33% / 0.0% | ✅/✅ |
| `context/user-info` | 91.5% / 89.0% | 21.0% / 59.0% | +22.0% / +44.0% | ✅/✅ |
| `module_large` | 91.33% / 90.0% | 20.0% / 91.0% | -4.17% / -5.0% | ✅/❌ |
| `module small` | 97.0% / 0.0% | 29.0% / 37.0% | +97.0% / 0.0% | ✅/✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `Module Large Report` | 91.33% / 90.0% | 20.0% / 91.0% | -4.17% / -5.0% | ✅/❌ |
| `Module Small Report` | 97.0% / 0.0% | 29.0% / 37.0% | 0.0% / 0.0% | ✅/✅ |
| `notification: API Module Report` | 95.0% / 0.0% | 22.0% / 60.0% | 0.0% / 0.0% | ✅/✅ |
| `notification: Client HTTP Module Report` | 90.0% / 0.0% | 22.0% / 60.0% | 0.0% / 0.0% | ✅/✅ |
| `notification: Plugins Module Report` | 92.0% / 0.0% | 22.0% / 60.0% | 0.0% / 0.0% | ✅/✅ |
| `user-info:  Controller Module Report` | 93.0% / 0.0% | 21.0% / 59.0% | 0.0% / 0.0% | ✅/✅ |
| `user-info: API Module Report` | 95.0% / 0.0% | 21.0% / 59.0% | 0.0% / 0.0% | ✅/✅ |
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 21.0% / 59.0% | +80.0% / +80.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 21.0% / 59.0% | +8.0% / +8.0% | ✅/✅ |

| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 90.5% | -5.0% | ❌ |
| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 55.0% | +80.0% | ✅ |
| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 55.0% | +8.0% | ✅ |"""

comment_more_files_single_detailed_instruction_with_modules_with_bs_fail_module = """**JaCoCo Coverage Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 92.0% | 75.0% | +6.9% | ✅ |
| **Changed Files** | 89.71% | 80.0% | +9.0% | ✅ |

| Module | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|-----------------|------------------|---------------|---------------|
| `context/user-info` | 91.5% / 89.0% | 21.0% / 59.0% | +22.0% / +44.0% | ✅/✅ |
| `module_large` | 91.33% / 90.0% | 20.0% / 91.0% | -4.17% / -5.0% | ✅/❌ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `Module Large Report` | 91.33% / 90.0% | 20.0% / 91.0% | -4.17% / -5.0% | ✅/❌ |
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 21.0% / 59.0% | +80.0% / +80.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 21.0% / 59.0% | +8.0% / +8.0% | ✅/✅ |

| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 90.5% | -5.0% | ❌ |
| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 55.0% | +80.0% | ✅ |
| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 55.0% | +8.0% | ✅ |"""

comment_more_files_single_detailed_instruction_with_partial_modules_1 = """**JaCoCo Coverage Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 92.0% | 75.0% | +6.9% | ✅ |
| **Changed Files** | 89.71% | 80.0% | +9.0% | ✅ |

| Module | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|-----------------|------------------|---------------|---------------|
| `context/user-info` | 91.5% / 89.0% | 21.0% / 59.0% | +22.0% / +44.0% | ✅/✅ |
| `Unknown` | 91.33% / 90.0% | 75.0% / 80.0% | -4.17% / -5.0% | ✅/✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `Module Large Report` | 91.33% / 90.0% | 75.0% / 80.0% | -4.17% / -5.0% | ✅/✅ |
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 21.0% / 59.0% | +80.0% / +80.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 21.0% / 59.0% | +8.0% / +8.0% | ✅/✅ |

| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 65.0% | -5.0% | ✅ |
| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 55.0% | +80.0% | ✅ |
| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 55.0% | +8.0% | ✅ |"""

comment_more_files_single_detailed_instruction_with_partial_modules_2 = """**JaCoCo Coverage Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 92.0% | 75.0% | +6.9% | ✅ |
| **Changed Files** | 89.71% | 80.0% | +9.0% | ✅ |

| Module | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|-----------------|------------------|---------------|---------------|
| `module_large` | 91.33% / 90.0% | 20.0% / 91.0% | -4.17% / -5.0% | ✅/❌ |
| `Unknown` | 91.5% / 89.0% | 75.0% / 80.0% | +22.0% / +44.0% | ✅/✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `Module Large Report` | 91.33% / 90.0% | 20.0% / 91.0% | -4.17% / -5.0% | ✅/❌ |
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 75.0% / 80.0% | +80.0% / +80.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 75.0% / 80.0% | +8.0% / +8.0% | ✅/✅ |

| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 90.5% | -5.0% | ❌ |
| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 65.0% | +80.0% | ✅ |
| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 65.0% | +8.0% | ✅ |"""

comment_more_files_single_detailed_instruction_with_partial_modules_3 = """**JaCoCo Coverage Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 92.0% | 75.0% | +6.9% | ✅ |
| **Changed Files** | 89.71% | 80.0% | +9.0% | ✅ |

| Module | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|-----------------|------------------|---------------|---------------|
| `Unknown` | 91.4% / 89.71% | 75.0% / 80.0% | +6.3% / +9.0% | ✅/✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `Module Large Report` | 91.33% / 90.0% | 75.0% / 80.0% | -4.17% / -5.0% | ✅/✅ |
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 75.0% / 80.0% | +80.0% / +80.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 75.0% / 80.0% | +8.0% / +8.0% | ✅/✅ |

| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 65.0% | -5.0% | ✅ |
| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 65.0% | +80.0% | ✅ |
| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 65.0% | +8.0% | ✅ |"""

comment_more_files_single_detailed_instruction_with_modules_no_module_thresholds_not_skip_changed = """**JaCoCo Coverage Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 92.0% | 75.0% | ✅ |
| **Changed Files** | 89.71% | 80.0% | ✅ |

| Module | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|-----------------|------------------|---------------|
| `context/notification` | 92.33% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `context/user-info` | 91.5% / 89.0% | 75.0% / 80.0% | ✅/✅ |
| `module_large` | 91.33% / 90.0% | 75.0% / 80.0% | ✅/✅ |
| `module small` | 97.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|--------|
| `Module Large Report` | 91.33% / 90.0% | 75.0% / 80.0% | ✅/✅ |
| `Module Small Report` | 97.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `notification: API Module Report` | 95.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `notification: Client HTTP Module Report` | 90.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `notification: Plugins Module Report` | 92.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `user-info:  Controller Module Report` | 93.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `user-info: API Module Report` | 95.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 75.0% / 80.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 75.0% / 80.0% | ✅/✅ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|
| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 65.0% | ✅ |
| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 65.0% | ✅ |
| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 65.0% | ✅ |"""

comment_more_files_single_detailed_instruction_with_modules_no_module_thresholds_not_skip_changed_with_bs = """**JaCoCo Coverage Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 92.0% | 75.0% | +6.9% | ✅ |
| **Changed Files** | 89.71% | 80.0% | +9.0% | ✅ |

| Module | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|-----------------|------------------|---------------|---------------|
| `context/notification` | 92.33% / 0.0% | 75.0% / 80.0% | +92.33% / 0.0% | ✅/✅ |
| `context/user-info` | 91.5% / 89.0% | 75.0% / 80.0% | +22.0% / +44.0% | ✅/✅ |
| `module_large` | 91.33% / 90.0% | 75.0% / 80.0% | -4.17% / -5.0% | ✅/✅ |
| `module small` | 97.0% / 0.0% | 75.0% / 80.0% | +97.0% / 0.0% | ✅/✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `Module Large Report` | 91.33% / 90.0% | 75.0% / 80.0% | -4.17% / -5.0% | ✅/✅ |
| `Module Small Report` | 97.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `notification: API Module Report` | 95.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `notification: Client HTTP Module Report` | 90.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `notification: Plugins Module Report` | 92.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `user-info:  Controller Module Report` | 93.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `user-info: API Module Report` | 95.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 75.0% / 80.0% | +80.0% / +80.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 75.0% / 80.0% | +8.0% / +8.0% | ✅/✅ |

| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 65.0% | -5.0% | ✅ |
| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 65.0% | +80.0% | ✅ |
| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 65.0% | +8.0% | ✅ |"""

comment_more_files_single_detailed_instruction_with_modules_no_module_thresholds_skip_changed = """**JaCoCo Coverage Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 92.0% | 75.0% | ✅ |
| **Changed Files** | 89.71% | 80.0% | ✅ |

| Module | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|-----------------|------------------|---------------|
| `context/user-info` | 91.5% / 89.0% | 75.0% / 80.0% | ✅/✅ |
| `module_large` | 91.33% / 90.0% | 75.0% / 80.0% | ✅/✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|--------|
| `Module Large Report` | 91.33% / 90.0% | 75.0% / 80.0% | ✅/✅ |
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 75.0% / 80.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 75.0% / 80.0% | ✅/✅ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|
| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 65.0% | ✅ |
| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 65.0% | ✅ |
| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 65.0% | ✅ |"""

comment_more_files_single_detailed_instruction_with_modules_no_module_thresholds_skip_changed_with_bs = """**JaCoCo Coverage Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 92.0% | 75.0% | +6.9% | ✅ |
| **Changed Files** | 89.71% | 80.0% | +9.0% | ✅ |

| Module | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|-----------------|------------------|---------------|---------------|
| `context/user-info` | 91.5% / 89.0% | 75.0% / 80.0% | +22.0% / +44.0% | ✅/✅ |
| `module_large` | 91.33% / 90.0% | 75.0% / 80.0% | -4.17% / -5.0% | ✅/✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `Module Large Report` | 91.33% / 90.0% | 75.0% / 80.0% | -4.17% / -5.0% | ✅/✅ |
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 75.0% / 80.0% | +80.0% / +80.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 75.0% / 80.0% | +8.0% / +8.0% | ✅/✅ |

| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 65.0% | -5.0% | ✅ |
| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 65.0% | +80.0% | ✅ |
| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 65.0% | +8.0% | ✅ |"""

comment_multi_minimalist_instruction = [
"""**Report: user-info: API Module Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 95.0% | 75.0% | ✅ |
| **Changed Files** | 0.0% | 80.0% | ✅ |""",
"""**Report: Module Large Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 91.33% | 75.0% | ✅ |
| **Changed Files** | 90.0% | 80.0% | ✅ |""",
"""**Report: user-info: Implementation Module Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 88.0% | 75.0% | ✅ |
| **Changed Files** | 88.0% | 80.0% | ✅ |""",
"""**Report: notification: Client HTTP Module Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 90.0% | 75.0% | ✅ |
| **Changed Files** | 0.0% | 80.0% | ✅ |""",
"""**Report: Module Small Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 97.0% | 75.0% | ✅ |
| **Changed Files** | 0.0% | 80.0% | ✅ |""",
"""**Report: notification: Plugins Module Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 92.0% | 75.0% | ✅ |
| **Changed Files** | 0.0% | 80.0% | ✅ |""",
"""**Report: user-info:  Controller Module Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 93.0% | 75.0% | ✅ |
| **Changed Files** | 0.0% | 80.0% | ✅ |""",
"""**Report: user-info: Client HTTP Module Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 90.0% | 75.0% | ✅ |
| **Changed Files** | 90.0% | 80.0% | ✅ |""",
"""**Report: notification: API Module Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 95.0% | 75.0% | ✅ |
| **Changed Files** | 0.0% | 80.0% | ✅ |"""]

comment_multi_minimalist_instruction_with_bs = [
"""**Report: Module Large Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 91.33% | 75.0% | -4.17% | ✅ |
| **Changed Files** | 90.0% | 80.0% | -5.0% | ✅ |""",
"""**Report: notification: Client HTTP Module Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 90.0% | 75.0% | +90.0% | ✅ |
| **Changed Files** | 0.0% | 80.0% | 0.0% | ✅ |""",
"""**Report: user-info: API Module Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 95.0% | 75.0% | 0.0% | ✅ |
| **Changed Files** | 0.0% | 80.0% | 0.0% | ✅ |""",
"""**Report: notification: API Module Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 95.0% | 75.0% | +95.0% | ✅ |
| **Changed Files** | 0.0% | 80.0% | 0.0% | ✅ |""",
"""**Report: user-info: Client HTTP Module Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 90.0% | 75.0% | +80.0% | ✅ |
| **Changed Files** | 90.0% | 80.0% | +80.0% | ✅ |""",
"""**Report: user-info: Implementation Module Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 88.0% | 75.0% | +8.0% | ✅ |
| **Changed Files** | 88.0% | 80.0% | +8.0% | ✅ |""",
"""**Report: notification: Plugins Module Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 92.0% | 75.0% | +92.0% | ✅ |
| **Changed Files** | 0.0% | 80.0% | 0.0% | ✅ |""",
"""**Report: user-info:  Controller Module Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 93.0% | 75.0% | +93.0% | ✅ |
| **Changed Files** | 0.0% | 80.0% | 0.0% | ✅ |""",
"""**Report: Module Small Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 97.0% | 75.0% | +97.0% | ✅ |
| **Changed Files** | 0.0% | 80.0% | 0.0% | ✅ |""",
]

comment_multi_minimalist_instruction_skip = [
"""**Report: Module Large Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 91.33% | 75.0% | ✅ |
| **Changed Files** | 90.0% | 80.0% | ✅ |""",
"""**Report: user-info: Implementation Module Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 88.0% | 75.0% | ✅ |
| **Changed Files** | 88.0% | 80.0% | ✅ |""",
"""**Report: user-info: Client HTTP Module Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 90.0% | 75.0% | ✅ |
| **Changed Files** | 90.0% | 80.0% | ✅ |"""]

comment_multi_minimalist_instruction_with_bs_skip = [
"""**Report: user-info: Client HTTP Module Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 90.0% | 75.0% | +80.0% | ✅ |
| **Changed Files** | 90.0% | 80.0% | +80.0% | ✅ |""",
"""**Report: user-info: Implementation Module Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 88.0% | 75.0% | +8.0% | ✅ |
| **Changed Files** | 88.0% | 80.0% | +8.0% | ✅ |""",
"""**Report: Module Large Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 91.33% | 75.0% | -4.17% | ✅ |
| **Changed Files** | 90.0% | 80.0% | -5.0% | ✅ |""",
]

comment_multi_summary_instruction_with_modules = [
"""**Report: user-info: API Module Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 95.0% | 21.0% | ✅ |
| **Changed Files** | 0.0% | 59.0% | ✅ |""",
"""**Report: user-info:  Controller Module Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 93.0% | 21.0% | ✅ |
| **Changed Files** | 0.0% | 59.0% | ✅ |""",
"""**Report: user-info: Client HTTP Module Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 90.0% | 21.0% | ✅ |
| **Changed Files** | 90.0% | 59.0% | ✅ |""",
"""**Report: Module Small Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 97.0% | 29.0% | ✅ |
| **Changed Files** | 0.0% | 37.0% | ✅ |""",
"""**Report: user-info: Implementation Module Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 88.0% | 21.0% | ✅ |
| **Changed Files** | 88.0% | 59.0% | ✅ |""",
"""**Report: Module Large Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 91.33% | 20.0% | ✅ |
| **Changed Files** | 90.0% | 91.0% | ❌ |""",
"""**Report: notification: API Module Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 95.0% | 22.0% | ✅ |
| **Changed Files** | 0.0% | 60.0% | ✅ |""",
"""**Report: notification: Client HTTP Module Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 90.0% | 22.0% | ✅ |
| **Changed Files** | 0.0% | 60.0% | ✅ |""",
"""**Report: notification: Plugins Module Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 92.0% | 22.0% | ✅ |
| **Changed Files** | 0.0% | 60.0% | ✅ |""",
]

comment_multi_summary_instruction_with_modules_with_bs = [
"""**Report: notification: Plugins Module Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 92.0% | 22.0% | +92.0% | ✅ |
| **Changed Files** | 0.0% | 60.0% | 0.0% | ✅ |""",
"""**Report: notification: Client HTTP Module Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 90.0% | 22.0% | +90.0% | ✅ |
| **Changed Files** | 0.0% | 60.0% | 0.0% | ✅ |""",
"""**Report: notification: API Module Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 95.0% | 22.0% | +95.0% | ✅ |
| **Changed Files** | 0.0% | 60.0% | 0.0% | ✅ |""",
"""**Report: Module Large Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 91.33% | 20.0% | -4.17% | ✅ |
| **Changed Files** | 90.0% | 91.0% | -5.0% | ❌ |""",
"""**Report: user-info: API Module Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 95.0% | 21.0% | 0.0% | ✅ |
| **Changed Files** | 0.0% | 59.0% | 0.0% | ✅ |""",
"""**Report: user-info: Client HTTP Module Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 90.0% | 21.0% | +80.0% | ✅ |
| **Changed Files** | 90.0% | 59.0% | +80.0% | ✅ |""",
"""**Report: Module Small Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 97.0% | 29.0% | +97.0% | ✅ |
| **Changed Files** | 0.0% | 37.0% | 0.0% | ✅ |""",
"""**Report: user-info: Implementation Module Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 88.0% | 21.0% | +8.0% | ✅ |
| **Changed Files** | 88.0% | 59.0% | +8.0% | ✅ |""",
"""**Report: user-info:  Controller Module Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 93.0% | 21.0% | +93.0% | ✅ |
| **Changed Files** | 0.0% | 59.0% | 0.0% | ✅ |""",
]

comment_multi_detailed_instruction_no_modules = [
"""**Report: Module Large Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 91.33% | 75.0% | ✅ |
| **Changed Files** | 90.0% | 80.0% | ✅ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|
| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 65.0% | ✅ |""",
"""**Report: user-info: Implementation Module Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 88.0% | 75.0% | ✅ |
| **Changed Files** | 88.0% | 80.0% | ✅ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|
| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 65.0% | ✅ |""",
"""**Report: Module Small Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 97.0% | 75.0% | ✅ |
| **Changed Files** | 0.0% | 80.0% | ✅ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|

No changed file in reports.""",
"""**Report: user-info: Client HTTP Module Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 90.0% | 75.0% | ✅ |
| **Changed Files** | 90.0% | 80.0% | ✅ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|
| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 65.0% | ✅ |""",
"""**Report: user-info:  Controller Module Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 93.0% | 75.0% | ✅ |
| **Changed Files** | 0.0% | 80.0% | ✅ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|

No changed file in reports.""",
"""**Report: notification: Plugins Module Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 92.0% | 75.0% | ✅ |
| **Changed Files** | 0.0% | 80.0% | ✅ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|

No changed file in reports.""",
"""**Report: user-info: API Module Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 95.0% | 75.0% | ✅ |
| **Changed Files** | 0.0% | 80.0% | ✅ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|

No changed file in reports.""",
"""**Report: notification: Client HTTP Module Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 90.0% | 75.0% | ✅ |
| **Changed Files** | 0.0% | 80.0% | ✅ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|

No changed file in reports.""",
"""**Report: notification: API Module Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 95.0% | 75.0% | ✅ |
| **Changed Files** | 0.0% | 80.0% | ✅ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|

No changed file in reports.""",
]

comment_multi_detailed_instruction_no_modules_with_bs = [
"""**Report: notification: Plugins Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 92.0% | 75.0% | +92.0% | ✅ |\n| **Changed Files** | 0.0% | 80.0% | 0.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n\nNo changed file in reports.""",
"""**Report: user-info:  Controller Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 93.0% | 75.0% | +93.0% | ✅ |\n| **Changed Files** | 0.0% | 80.0% | 0.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n\nNo changed file in reports.""",
"""**Report: Module Small Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 97.0% | 75.0% | +97.0% | ✅ |\n| **Changed Files** | 0.0% | 80.0% | 0.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n\nNo changed file in reports.""",
"""**Report: notification: Client HTTP Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 90.0% | 75.0% | +90.0% | ✅ |\n| **Changed Files** | 0.0% | 80.0% | 0.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n\nNo changed file in reports.""",
"""**Report: Module Large Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 91.33% | 75.0% | -4.17% | ✅ |\n| **Changed Files** | 90.0% | 80.0% | -5.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 65.0% | -5.0% | ✅ |""",
"""**Report: user-info: Implementation Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 88.0% | 75.0% | +8.0% | ✅ |\n| **Changed Files** | 88.0% | 80.0% | +8.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 65.0% | +8.0% | ✅ |""",
"""**Report: user-info: API Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 95.0% | 75.0% | 0.0% | ✅ |\n| **Changed Files** | 0.0% | 80.0% | 0.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n\nNo changed file in reports.""",
"""**Report: user-info: Client HTTP Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 90.0% | 75.0% | +80.0% | ✅ |\n| **Changed Files** | 90.0% | 80.0% | +80.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 65.0% | +80.0% | ✅ |""",
"""**Report: notification: API Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 95.0% | 75.0% | +95.0% | ✅ |\n| **Changed Files** | 0.0% | 80.0% | 0.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n\nNo changed file in reports.""",
]

comment_multi_detailed_instruction_with_modules = [
"""**Report: Module Small Report**\n\n| Metric (instruction) | Coverage | Threshold | Status |\n|----------------------|----------|-----------|--------|\n| **Overall**       | 97.0% | 29.0% | ✅ |\n| **Changed Files** | 0.0% | 37.0% | ✅ |\n\n| File Path | Coverage | Threshold | Status |\n|-----------|----------|-----------|--------|\n\nNo changed file in reports.""",
"""**Report: user-info: Implementation Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Status |\n|----------------------|----------|-----------|--------|\n| **Overall**       | 88.0% | 21.0% | ✅ |\n| **Changed Files** | 88.0% | 59.0% | ✅ |\n\n| File Path | Coverage | Threshold | Status |\n|-----------|----------|-----------|--------|\n| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 55.0% | ✅ |""",
"""**Report: user-info: API Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Status |\n|----------------------|----------|-----------|--------|\n| **Overall**       | 95.0% | 21.0% | ✅ |\n| **Changed Files** | 0.0% | 59.0% | ✅ |\n\n| File Path | Coverage | Threshold | Status |\n|-----------|----------|-----------|--------|\n\nNo changed file in reports.""",
"""**Report: notification: API Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Status |\n|----------------------|----------|-----------|--------|\n| **Overall**       | 95.0% | 22.0% | ✅ |\n| **Changed Files** | 0.0% | 60.0% | ✅ |\n\n| File Path | Coverage | Threshold | Status |\n|-----------|----------|-----------|--------|\n\nNo changed file in reports.""",
"""**Report: notification: Plugins Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Status |\n|----------------------|----------|-----------|--------|\n| **Overall**       | 92.0% | 22.0% | ✅ |\n| **Changed Files** | 0.0% | 60.0% | ✅ |\n\n| File Path | Coverage | Threshold | Status |\n|-----------|----------|-----------|--------|\n\nNo changed file in reports.""",
"""**Report: user-info: Client HTTP Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Status |\n|----------------------|----------|-----------|--------|\n| **Overall**       | 90.0% | 21.0% | ✅ |\n| **Changed Files** | 90.0% | 59.0% | ✅ |\n\n| File Path | Coverage | Threshold | Status |\n|-----------|----------|-----------|--------|\n| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 55.0% | ✅ |""",
"""**Report: Module Large Report**\n\n| Metric (instruction) | Coverage | Threshold | Status |\n|----------------------|----------|-----------|--------|\n| **Overall**       | 91.33% | 20.0% | ✅ |\n| **Changed Files** | 90.0% | 91.0% | ❌ |\n\n| File Path | Coverage | Threshold | Status |\n|-----------|----------|-----------|--------|\n| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 90.5% | ❌ |""",
"""**Report: user-info:  Controller Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Status |\n|----------------------|----------|-----------|--------|\n| **Overall**       | 93.0% | 21.0% | ✅ |\n| **Changed Files** | 0.0% | 59.0% | ✅ |\n\n| File Path | Coverage | Threshold | Status |\n|-----------|----------|-----------|--------|\n\nNo changed file in reports.""",
"""**Report: notification: Client HTTP Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Status |\n|----------------------|----------|-----------|--------|\n| **Overall**       | 90.0% | 22.0% | ✅ |\n| **Changed Files** | 0.0% | 60.0% | ✅ |\n\n| File Path | Coverage | Threshold | Status |\n|-----------|----------|-----------|--------|\n\nNo changed file in reports.""",
]

comment_multi_detailed_instruction_with_modules_with_bs = [
"""**Report: notification: API Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 95.0% | 22.0% | +95.0% | ✅ |\n| **Changed Files** | 0.0% | 60.0% | 0.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n\nNo changed file in reports.""",
"""**Report: user-info: API Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 95.0% | 21.0% | 0.0% | ✅ |\n| **Changed Files** | 0.0% | 59.0% | 0.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n\nNo changed file in reports.""",
"""**Report: user-info: Implementation Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 88.0% | 21.0% | +8.0% | ✅ |\n| **Changed Files** | 88.0% | 59.0% | +8.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 55.0% | +8.0% | ✅ |""",
"""**Report: user-info: Client HTTP Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 90.0% | 21.0% | +80.0% | ✅ |\n| **Changed Files** | 90.0% | 59.0% | +80.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 55.0% | +80.0% | ✅ |""",
"""**Report: notification: Plugins Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 92.0% | 22.0% | +92.0% | ✅ |\n| **Changed Files** | 0.0% | 60.0% | 0.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n\nNo changed file in reports.""",
"""**Report: Module Large Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 91.33% | 20.0% | -4.17% | ✅ |\n| **Changed Files** | 90.0% | 91.0% | -5.0% | ❌ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 90.5% | -5.0% | ❌ |""",
"""**Report: Module Small Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 97.0% | 29.0% | +97.0% | ✅ |\n| **Changed Files** | 0.0% | 37.0% | 0.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n\nNo changed file in reports.""",
"""**Report: user-info:  Controller Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 93.0% | 21.0% | +93.0% | ✅ |\n| **Changed Files** | 0.0% | 59.0% | 0.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n\nNo changed file in reports.""",
"""**Report: notification: Client HTTP Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 90.0% | 22.0% | +90.0% | ✅ |\n| **Changed Files** | 0.0% | 60.0% | 0.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n\nNo changed file in reports.""",
]

comment_multi_detailed_instruction_with_modules_with_bs_fail_module = [
"""**Report: user-info: Implementation Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 88.0% | 21.0% | +8.0% | ✅ |\n| **Changed Files** | 88.0% | 59.0% | +8.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 55.0% | +8.0% | ✅ |""",
"""**Report: Module Large Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 91.33% | 20.0% | -4.17% | ✅ |\n| **Changed Files** | 90.0% | 91.0% | -5.0% | ❌ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 90.5% | -5.0% | ❌ |""",
"""**Report: user-info: Client HTTP Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 90.0% | 21.0% | +80.0% | ✅ |\n| **Changed Files** | 90.0% | 59.0% | +80.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 55.0% | +80.0% | ✅ |""",
]

comment_multi_detailed_instruction_with_modules_with_bs_partial_modules_2 = [
"""**Report: user-info: Implementation Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 88.0% | 75.0% | +8.0% | ✅ |\n| **Changed Files** | 88.0% | 80.0% | +8.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 65.0% | +8.0% | ✅ |""",
"""**Report: Module Large Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 91.33% | 20.0% | -4.17% | ✅ |\n| **Changed Files** | 90.0% | 91.0% | -5.0% | ❌ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 90.5% | -5.0% | ❌ |""",
"""**Report: user-info: Client HTTP Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 90.0% | 75.0% | +80.0% | ✅ |\n| **Changed Files** | 90.0% | 80.0% | +80.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 65.0% | +80.0% | ✅ |""",
]

comment_multi_detailed_instruction_with_modules_with_bs_partial_modules_3 = [
"""**Report: user-info: Implementation Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 88.0% | 75.0% | +8.0% | ✅ |\n| **Changed Files** | 88.0% | 80.0% | +8.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 65.0% | +8.0% | ✅ |""",
"""**Report: Module Large Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 91.33% | 75.0% | -4.17% | ✅ |\n| **Changed Files** | 90.0% | 80.0% | -5.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 65.0% | -5.0% | ✅ |""",
"""**Report: user-info: Client HTTP Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 90.0% | 75.0% | +80.0% | ✅ |\n| **Changed Files** | 90.0% | 80.0% | +80.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 65.0% | +80.0% | ✅ |""",
]

comment_multi_detailed_instruction_with_modules_report_1 = [
"""**Report: user-info: Implementation Module Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 88.0% | 21.0% | +8.0% | ✅ |
| **Changed Files** | 88.0% | 59.0% | +8.0% | ✅ |

| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 55.0% | +8.0% | ✅ |""",
"""**Report: Module Large Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 91.33% | 75.0% | -4.17% | ✅ |
| **Changed Files** | 90.0% | 80.0% | -5.0% | ✅ |

| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 65.0% | -5.0% | ✅ |""",
"""**Report: user-info: Client HTTP Module Report**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 90.0% | 21.0% | +80.0% | ✅ |
| **Changed Files** | 90.0% | 59.0% | +80.0% | ✅ |

| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 55.0% | +80.0% | ✅ |""",
]

comment_multi_detailed_instruction_with_modules_no_module_thresholds_not_skip_changed = [
"""**Report: notification: Plugins Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Status |\n|----------------------|----------|-----------|--------|\n| **Overall**       | 92.0% | 75.0% | ✅ |\n| **Changed Files** | 0.0% | 80.0% | ✅ |\n\n| File Path | Coverage | Threshold | Status |\n|-----------|----------|-----------|--------|\n\nNo changed file in reports.""",
"""**Report: user-info:  Controller Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Status |\n|----------------------|----------|-----------|--------|\n| **Overall**       | 93.0% | 75.0% | ✅ |\n| **Changed Files** | 0.0% | 80.0% | ✅ |\n\n| File Path | Coverage | Threshold | Status |\n|-----------|----------|-----------|--------|\n\nNo changed file in reports.""",
"""**Report: Module Small Report**\n\n| Metric (instruction) | Coverage | Threshold | Status |\n|----------------------|----------|-----------|--------|\n| **Overall**       | 97.0% | 75.0% | ✅ |\n| **Changed Files** | 0.0% | 80.0% | ✅ |\n\n| File Path | Coverage | Threshold | Status |\n|-----------|----------|-----------|--------|\n\nNo changed file in reports.""",
"""**Report: user-info: API Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Status |\n|----------------------|----------|-----------|--------|\n| **Overall**       | 95.0% | 75.0% | ✅ |\n| **Changed Files** | 0.0% | 80.0% | ✅ |\n\n| File Path | Coverage | Threshold | Status |\n|-----------|----------|-----------|--------|\n\nNo changed file in reports.""",
"""**Report: notification: API Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Status |\n|----------------------|----------|-----------|--------|\n| **Overall**       | 95.0% | 75.0% | ✅ |\n| **Changed Files** | 0.0% | 80.0% | ✅ |\n\n| File Path | Coverage | Threshold | Status |\n|-----------|----------|-----------|--------|\n\nNo changed file in reports.""",
"""**Report: user-info: Client HTTP Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Status |\n|----------------------|----------|-----------|--------|\n| **Overall**       | 90.0% | 75.0% | ✅ |\n| **Changed Files** | 90.0% | 80.0% | ✅ |\n\n| File Path | Coverage | Threshold | Status |\n|-----------|----------|-----------|--------|\n| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 65.0% | ✅ |""",
"""**Report: user-info: Implementation Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Status |\n|----------------------|----------|-----------|--------|\n| **Overall**       | 88.0% | 75.0% | ✅ |\n| **Changed Files** | 88.0% | 80.0% | ✅ |\n\n| File Path | Coverage | Threshold | Status |\n|-----------|----------|-----------|--------|\n| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 65.0% | ✅ |""",
"""**Report: notification: Client HTTP Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Status |\n|----------------------|----------|-----------|--------|\n| **Overall**       | 90.0% | 75.0% | ✅ |\n| **Changed Files** | 0.0% | 80.0% | ✅ |\n\n| File Path | Coverage | Threshold | Status |\n|-----------|----------|-----------|--------|\n\nNo changed file in reports.""",
"""**Report: Module Large Report**\n\n| Metric (instruction) | Coverage | Threshold | Status |\n|----------------------|----------|-----------|--------|\n| **Overall**       | 91.33% | 75.0% | ✅ |\n| **Changed Files** | 90.0% | 80.0% | ✅ |\n\n| File Path | Coverage | Threshold | Status |\n|-----------|----------|-----------|--------|\n| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 65.0% | ✅ |""",
]

comment_multi_detailed_instruction_with_modules_no_module_thresholds_not_skip_changed_with_bs = [
"""**Report: notification: Plugins Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 92.0% | 75.0% | +92.0% | ✅ |\n| **Changed Files** | 0.0% | 80.0% | 0.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n\nNo changed file in reports.""",
"""**Report: user-info:  Controller Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 93.0% | 75.0% | +93.0% | ✅ |\n| **Changed Files** | 0.0% | 80.0% | 0.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n\nNo changed file in reports.""",
"""**Report: Module Large Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 91.33% | 75.0% | -4.17% | ✅ |\n| **Changed Files** | 90.0% | 80.0% | -5.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 65.0% | -5.0% | ✅ |""",
"""**Report: user-info: API Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 95.0% | 75.0% | 0.0% | ✅ |\n| **Changed Files** | 0.0% | 80.0% | 0.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n\nNo changed file in reports.""",
"""**Report: user-info: Client HTTP Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 90.0% | 75.0% | +80.0% | ✅ |\n| **Changed Files** | 90.0% | 80.0% | +80.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 65.0% | +80.0% | ✅ |""",
"""**Report: Module Small Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 97.0% | 75.0% | +97.0% | ✅ |\n| **Changed Files** | 0.0% | 80.0% | 0.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n\nNo changed file in reports.""",
"""**Report: notification: API Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 95.0% | 75.0% | +95.0% | ✅ |\n| **Changed Files** | 0.0% | 80.0% | 0.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n\nNo changed file in reports.""",
"""**Report: notification: Client HTTP Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 90.0% | 75.0% | +90.0% | ✅ |\n| **Changed Files** | 0.0% | 80.0% | 0.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n\nNo changed file in reports.""",
"""**Report: user-info: Implementation Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 88.0% | 75.0% | +8.0% | ✅ |\n| **Changed Files** | 88.0% | 80.0% | +8.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 65.0% | +8.0% | ✅ |""",
]

comment_multi_detailed_instruction_with_modules_no_module_thresholds_skip_changed = [
"""**Report: Module Large Report**\n\n| Metric (instruction) | Coverage | Threshold | Status |\n|----------------------|----------|-----------|--------|\n| **Overall**       | 91.33% | 75.0% | ✅ |\n| **Changed Files** | 90.0% | 80.0% | ✅ |\n\n| File Path | Coverage | Threshold | Status |\n|-----------|----------|-----------|--------|\n| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 65.0% | ✅ |""",
"""**Report: user-info: Client HTTP Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Status |\n|----------------------|----------|-----------|--------|\n| **Overall**       | 90.0% | 75.0% | ✅ |\n| **Changed Files** | 90.0% | 80.0% | ✅ |\n\n| File Path | Coverage | Threshold | Status |\n|-----------|----------|-----------|--------|\n| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 65.0% | ✅ |""",
"""**Report: user-info: Implementation Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Status |\n|----------------------|----------|-----------|--------|\n| **Overall**       | 88.0% | 75.0% | ✅ |\n| **Changed Files** | 88.0% | 80.0% | ✅ |\n\n| File Path | Coverage | Threshold | Status |\n|-----------|----------|-----------|--------|\n| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 65.0% | ✅ |""",
]

comment_multi_detailed_instruction_with_modules_no_module_thresholds_skip_changed_with_bs = [
"""**Report: user-info: Client HTTP Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 90.0% | 75.0% | +80.0% | ✅ |\n| **Changed Files** | 90.0% | 80.0% | +80.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 65.0% | +80.0% | ✅ |""",
"""**Report: user-info: Implementation Module Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 88.0% | 75.0% | +8.0% | ✅ |\n| **Changed Files** | 88.0% | 80.0% | +8.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 65.0% | +8.0% | ✅ |""",
"""**Report: Module Large Report**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 91.33% | 75.0% | -4.17% | ✅ |\n| **Changed Files** | 90.0% | 80.0% | -5.0% | ✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 65.0% | -5.0% | ✅ |""",
]

comment_module_detailed_instruction_with_modules_with_bs = [
"""**Module: context/notification**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 92.33% | 22.0% | +92.33% | ✅ |
| **Changed Files** | 0.0% | 60.0% | 0.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `notification: API Module Report` | 95.0% / 0.0% | 22.0% / 60.0% | 0.0% / 0.0% | ✅/✅ |
| `notification: Client HTTP Module Report` | 90.0% / 0.0% | 22.0% / 60.0% | 0.0% / 0.0% | ✅/✅ |
| `notification: Plugins Module Report` | 92.0% / 0.0% | 22.0% / 60.0% | 0.0% / 0.0% | ✅/✅ |

| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|

No changed file in reports.""",
"""**Module: context/user-info**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 91.5% | 21.0% | +22.0% | ✅ |
| **Changed Files** | 89.0% | 59.0% | +44.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `user-info:  Controller Module Report` | 93.0% / 0.0% | 21.0% / 59.0% | 0.0% / 0.0% | ✅/✅ |
| `user-info: API Module Report` | 95.0% / 0.0% | 21.0% / 59.0% | 0.0% / 0.0% | ✅/✅ |
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 21.0% / 59.0% | +80.0% / +80.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 21.0% / 59.0% | +8.0% / +8.0% | ✅/✅ |

| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 55.0% | +80.0% | ✅ |
| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 55.0% | +8.0% | ✅ |""",
"""**Module: module_large**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 91.33% | 20.0% | -4.17% | ✅ |
| **Changed Files** | 90.0% | 91.0% | -5.0% | ❌ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `Module Large Report` | 91.33% / 90.0% | 20.0% / 91.0% | -4.17% / -5.0% | ✅/❌ |

| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 90.5% | -5.0% | ❌ |""",
"""**Module: module small**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 97.0% | 29.0% | +97.0% | ✅ |
| **Changed Files** | 0.0% | 37.0% | 0.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `Module Small Report` | 97.0% / 0.0% | 29.0% / 37.0% | 0.0% / 0.0% | ✅/✅ |

| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|

No changed file in reports.""",
]

comment_module_detailed_instruction_with_modules_with_bs_fail_non_changed_module = [
"""**Module: context/user-info**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 91.5% | 21.0% | +22.0% | ✅ |
| **Changed Files** | 89.0% | 59.0% | +44.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 21.0% / 59.0% | +80.0% / +80.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 21.0% / 59.0% | +8.0% / +8.0% | ✅/✅ |

| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 55.0% | +80.0% | ✅ |
| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 55.0% | +8.0% | ✅ |""",
"""**Module: module_large**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 91.33% | 20.0% | -4.17% | ✅ |
| **Changed Files** | 90.0% | 91.0% | -5.0% | ❌ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `Module Large Report` | 91.33% / 90.0% | 20.0% / 91.0% | -4.17% / -5.0% | ✅/❌ |

| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 90.5% | -5.0% | ❌ |""",
]

comment_module_detailed_instruction_with_modules_with_bs_partial_modules_report_2 = [
"""**Module: Unknown**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 91.5% | 75.0% | +22.0% | ✅ |
| **Changed Files** | 89.0% | 80.0% | +44.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 75.0% / 80.0% | +80.0% / +80.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 75.0% / 80.0% | +8.0% / +8.0% | ✅/✅ |

| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 65.0% | +80.0% | ✅ |
| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 65.0% | +8.0% | ✅ |""",
"""**Module: module_large**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 91.33% | 20.0% | -4.17% | ✅ |
| **Changed Files** | 90.0% | 91.0% | -5.0% | ❌ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `Module Large Report` | 91.33% / 90.0% | 20.0% / 91.0% | -4.17% / -5.0% | ✅/❌ |

| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 90.5% | -5.0% | ❌ |""",
]

comment_module_detailed_instruction_with_modules_with_bs_partial_modules_report_3 = [
"""**Module: Unknown**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 91.4% | 75.0% | +6.3% | ✅ |
| **Changed Files** | 89.71% | 80.0% | +9.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `Module Large Report` | 91.33% / 90.0% | 75.0% / 80.0% | -4.17% / -5.0% | ✅/✅ |
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 75.0% / 80.0% | +80.0% / +80.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 75.0% / 80.0% | +8.0% / +8.0% | ✅/✅ |

| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 65.0% | -5.0% | ✅ |
| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 65.0% | +80.0% | ✅ |
| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 65.0% | +8.0% | ✅ |""",
]

comment_single_detailed_none_changed_files_in_report = """**JaCoCo Coverage Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 92.0% | 75.0% | ✅ |
| **Changed Files** | 0.0% | 80.0% | ✅ |

| Module | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|-----------------|------------------|---------------|

No changed file in reports.

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|--------|

No changed file in reports.

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|

No changed file in reports."""

comment_multi_detailed_none_changed_files_in_report = [
"""TBD""",
"""TBD""",
"""TBD""",
"""TBD""",
]

comment_module_detailed_none_changed_files_in_report = [
"""TBD""",
"""TBD""",
]

comment_single_detailed_two_changed_files_in_report = """**JaCoCo Coverage Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 92.0% | 75.0% | ✅ |
| **Changed Files** | 89.98% | 80.0% | ✅ |

| Module | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|-----------------|------------------|---------------|
| `context/user-info` | 91.5% / 89.0% | 21.0% / 59.0% | ✅/✅ |
| `module_large` | 91.33% / 90.25% | 20.0% / 91.0% | ✅/❌ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|--------|
| `Module Large Report` | 91.33% / 90.41% | 20.0% / 91.0% | ✅/❌ |
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 21.0% / 59.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 21.0% / 59.0% | ✅/✅ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|
| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 90.5% | ❌ |
| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 55.0% | ✅ |
| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 55.0% | ✅ |
| [MidClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-3371f6a8118785a239bd8e06a35f29cab63074eddacfd456caecd1da1c68c2dd) | 90.83% | 90.5% | ✅ |"""

comment_multi_detailed_two_changed_files_in_report = [
"""**Report: user-info: Implementation Module Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 88.0% | 21.0% | ✅ |\n| **Changed Files** | 88.0% | 59.0% | ✅ |

| File Path | Coverage | Threshold | Status |\n|-----------|----------|-----------|--------|
| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 55.0% | ✅ |""",
"""**Report: Module Large Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 91.33% | 20.0% | ✅ |
| **Changed Files** | 90.41% | 91.0% | ❌ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|
| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 90.5% | ❌ |
| [MidClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-3371f6a8118785a239bd8e06a35f29cab63074eddacfd456caecd1da1c68c2dd) | 90.83% | 90.5% | ✅ |""",
"""**Report: user-info: Client HTTP Module Report**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 90.0% | 21.0% | ✅ |
| **Changed Files** | 90.0% | 59.0% | ✅ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|
| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 55.0% | ✅ |""",
]

comment_module_detailed_two_changed_files_in_report = [
"""**Module: context/user-info**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 91.5% | 21.0% | ✅ |
| **Changed Files** | 89.0% | 59.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|--------|
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 21.0% / 59.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 21.0% / 59.0% | ✅/✅ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|
| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 55.0% | ✅ |
| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 55.0% | ✅ |""",
"""**Module: module_large**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 91.33% | 20.0% | ✅ |
| **Changed Files** | 90.25% | 91.0% | ❌ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|--------|
| `Module Large Report` | 91.33% / 90.41% | 20.0% / 91.0% | ✅/❌ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|
| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 90.5% | ❌ |
| [MidClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-3371f6a8118785a239bd8e06a35f29cab63074eddacfd456caecd1da1c68c2dd) | 90.83% | 90.5% | ✅ |""",
]

comment_module_detailed_instruction_with_modules_with_bs_report_1 = [
"""**Module: context/user-info**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 91.5% | 21.0% | +22.0% | ✅ |
| **Changed Files** | 89.0% | 59.0% | +44.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 21.0% / 59.0% | +80.0% / +80.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 21.0% / 59.0% | +8.0% / +8.0% | ✅/✅ |

| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 55.0% | +80.0% | ✅ |
| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 55.0% | +8.0% | ✅ |""",
"""**Module: Unknown**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 91.33% | 75.0% | -4.17% | ✅ |
| **Changed Files** | 90.0% | 80.0% | -5.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `Module Large Report` | 91.33% / 90.0% | 75.0% / 80.0% | -4.17% / -5.0% | ✅/✅ |

| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 65.0% | -5.0% | ✅ |""",
]

comment_module_detailed_instruction_with_modules_with_bs_fail_non_changed_module_fail_report = [
"""**Module: module_large**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 91.33% | 20.0% | -4.17% | ✅ |
| **Changed Files** | 90.0% | 91.0% | -5.0% | ❌ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `Module Large Report` | 91.33% / 90.0% | 20.0% / 91.0% | -4.17% / -5.0% | ✅/❌ |

| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 90.5% | -5.0% | ❌ |""",
]

comment_module_minimalist_instruction = [
"""**Module: context/notification**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 92.33% | 75.0% | ✅ |
| **Changed Files** | 0.0% | 80.0% | ✅ |""",
"""**Module: context/user-info**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 91.5% | 75.0% | ✅ |
| **Changed Files** | 89.0% | 80.0% | ✅ |""",
"""**Module: module_large**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 91.33% | 75.0% | ✅ |
| **Changed Files** | 90.0% | 80.0% | ✅ |""",
"""**Module: module small**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 97.0% | 75.0% | ✅ |
| **Changed Files** | 0.0% | 80.0% | ✅ |""",
]

comment_module_minimalist_instruction_summary = [
"""**Module: context/notification**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 92.33% | 75.0% | ✅ |
| **Changed Files** | 0.0% | 80.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|--------|
| `notification: API Module Report` | 95.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `notification: Client HTTP Module Report` | 90.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `notification: Plugins Module Report` | 92.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |""",
"""**Module: context/user-info**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 91.5% | 75.0% | ✅ |
| **Changed Files** | 89.0% | 80.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|--------|
| `user-info:  Controller Module Report` | 93.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `user-info: API Module Report` | 95.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 75.0% / 80.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 75.0% / 80.0% | ✅/✅ |""",
"""**Module: module_large**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 91.33% | 75.0% | ✅ |
| **Changed Files** | 90.0% | 80.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|--------|
| `Module Large Report` | 91.33% / 90.0% | 75.0% / 80.0% | ✅/✅ |""",
"""**Module: module small**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 97.0% | 75.0% | ✅ |
| **Changed Files** | 0.0% | 80.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|--------|
| `Module Small Report` | 97.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |""",
]

comment_module_minimalist_instruction_with_bs = [
"""**Module: context/notification**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 92.33% | 75.0% | +92.33% | ✅ |
| **Changed Files** | 0.0% | 80.0% | 0.0% | ✅ |""",
"""**Module: context/user-info**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 91.5% | 75.0% | +22.0% | ✅ |
| **Changed Files** | 89.0% | 80.0% | +44.0% | ✅ |""",
"""**Module: module_large**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 91.33% | 75.0% | -4.17% | ✅ |
| **Changed Files** | 90.0% | 80.0% | -5.0% | ✅ |""",
"""**Module: module small**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 97.0% | 75.0% | +97.0% | ✅ |
| **Changed Files** | 0.0% | 80.0% | 0.0% | ✅ |""",
]

comment_module_minimalist_instruction_with_bs_summary = [
"""**Module: context/notification**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 92.33% | 75.0% | +92.33% | ✅ |
| **Changed Files** | 0.0% | 80.0% | 0.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `notification: API Module Report` | 95.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `notification: Client HTTP Module Report` | 90.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `notification: Plugins Module Report` | 92.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |""",
"""**Module: context/user-info**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 91.5% | 75.0% | +22.0% | ✅ |
| **Changed Files** | 89.0% | 80.0% | +44.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `user-info:  Controller Module Report` | 93.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `user-info: API Module Report` | 95.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 75.0% / 80.0% | +80.0% / +80.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 75.0% / 80.0% | +8.0% / +8.0% | ✅/✅ |""",
"""**Module: module_large**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 91.33% | 75.0% | -4.17% | ✅ |
| **Changed Files** | 90.0% | 80.0% | -5.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `Module Large Report` | 91.33% / 90.0% | 75.0% / 80.0% | -4.17% / -5.0% | ✅/✅ |""",
"""**Module: module small**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 97.0% | 75.0% | +97.0% | ✅ |
| **Changed Files** | 0.0% | 80.0% | 0.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `Module Small Report` | 97.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |""",
]

comment_module_summary_instruction_with_modules = [
"""**Module: context/notification**\n\n| Metric (instruction) | Coverage | Threshold | Status |\n|----------------------|----------|-----------|--------|\n| **Overall**       | 92.33% | 22.0% | ✅ |\n| **Changed Files** | 0.0% | 60.0% | ✅ |\n\n| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |\n|--------|----------|-----------|--------|\n| `notification: API Module Report` | 95.0% / 0.0% | 22.0% / 60.0% | ✅/✅ |\n| `notification: Client HTTP Module Report` | 90.0% / 0.0% | 22.0% / 60.0% | ✅/✅ |\n| `notification: Plugins Module Report` | 92.0% / 0.0% | 22.0% / 60.0% | ✅/✅ |""",
"""**Module: context/user-info**\n\n| Metric (instruction) | Coverage | Threshold | Status |\n|----------------------|----------|-----------|--------|\n| **Overall**       | 91.5% | 21.0% | ✅ |\n| **Changed Files** | 89.0% | 59.0% | ✅ |\n\n| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |\n|--------|----------|-----------|--------|\n| `user-info:  Controller Module Report` | 93.0% / 0.0% | 21.0% / 59.0% | ✅/✅ |\n| `user-info: API Module Report` | 95.0% / 0.0% | 21.0% / 59.0% | ✅/✅ |\n| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 21.0% / 59.0% | ✅/✅ |\n| `user-info: Implementation Module Report` | 88.0% / 88.0% | 21.0% / 59.0% | ✅/✅ |""",
"""**Module: module_large**\n\n| Metric (instruction) | Coverage | Threshold | Status |\n|----------------------|----------|-----------|--------|\n| **Overall**       | 91.33% | 20.0% | ✅ |\n| **Changed Files** | 90.0% | 91.0% | ❌ |\n\n| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |\n|--------|----------|-----------|--------|\n| `Module Large Report` | 91.33% / 90.0% | 20.0% / 91.0% | ✅/❌ |""",
"""**Module: module small**\n\n| Metric (instruction) | Coverage | Threshold | Status |\n|----------------------|----------|-----------|--------|\n| **Overall**       | 97.0% | 29.0% | ✅ |\n| **Changed Files** | 0.0% | 37.0% | ✅ |\n\n| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |\n|--------|----------|-----------|--------|\n| `Module Small Report` | 97.0% / 0.0% | 29.0% / 37.0% | ✅/✅ |""",
]

comment_module_summary_instruction_with_modules_with_bs = [
"""**Module: context/notification**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 92.33% | 22.0% | +92.33% | ✅ |\n| **Changed Files** | 0.0% | 60.0% | 0.0% | ✅ |\n\n| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |\n|--------|----------|-----------|------------|--------|\n| `notification: API Module Report` | 95.0% / 0.0% | 22.0% / 60.0% | 0.0% / 0.0% | ✅/✅ |\n| `notification: Client HTTP Module Report` | 90.0% / 0.0% | 22.0% / 60.0% | 0.0% / 0.0% | ✅/✅ |\n| `notification: Plugins Module Report` | 92.0% / 0.0% | 22.0% / 60.0% | 0.0% / 0.0% | ✅/✅ |""",
"""**Module: context/user-info**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 91.5% | 21.0% | +22.0% | ✅ |\n| **Changed Files** | 89.0% | 59.0% | +44.0% | ✅ |\n\n| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |\n|--------|----------|-----------|------------|--------|\n| `user-info:  Controller Module Report` | 93.0% / 0.0% | 21.0% / 59.0% | 0.0% / 0.0% | ✅/✅ |\n| `user-info: API Module Report` | 95.0% / 0.0% | 21.0% / 59.0% | 0.0% / 0.0% | ✅/✅ |\n| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 21.0% / 59.0% | +80.0% / +80.0% | ✅/✅ |\n| `user-info: Implementation Module Report` | 88.0% / 88.0% | 21.0% / 59.0% | +8.0% / +8.0% | ✅/✅ |""",
"""**Module: module_large**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 91.33% | 20.0% | -4.17% | ✅ |\n| **Changed Files** | 90.0% | 91.0% | -5.0% | ❌ |\n\n| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |\n|--------|----------|-----------|------------|--------|\n| `Module Large Report` | 91.33% / 90.0% | 20.0% / 91.0% | -4.17% / -5.0% | ✅/❌ |""",
"""**Module: module small**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 97.0% | 29.0% | +97.0% | ✅ |\n| **Changed Files** | 0.0% | 37.0% | 0.0% | ✅ |\n\n| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |\n|--------|----------|-----------|------------|--------|\n| `Module Small Report` | 97.0% / 0.0% | 29.0% / 37.0% | 0.0% / 0.0% | ✅/✅ |""",
]

comment_module_detail_instruction_with_modules = [
"""**Module: context/notification**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 92.33% | 22.0% | ✅ |
| **Changed Files** | 0.0% | 60.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|--------|
| `notification: API Module Report` | 95.0% / 0.0% | 22.0% / 60.0% | ✅/✅ |
| `notification: Client HTTP Module Report` | 90.0% / 0.0% | 22.0% / 60.0% | ✅/✅ |
| `notification: Plugins Module Report` | 92.0% / 0.0% | 22.0% / 60.0% | ✅/✅ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|

No changed file in reports.""",
"""**Module: context/user-info**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 91.5% | 21.0% | ✅ |
| **Changed Files** | 89.0% | 59.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|--------|
| `user-info:  Controller Module Report` | 93.0% / 0.0% | 21.0% / 59.0% | ✅/✅ |
| `user-info: API Module Report` | 95.0% / 0.0% | 21.0% / 59.0% | ✅/✅ |
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 21.0% / 59.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 21.0% / 59.0% | ✅/✅ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|
| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 55.0% | ✅ |
| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 55.0% | ✅ |""",
"""**Module: module_large**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 91.33% | 20.0% | ✅ |
| **Changed Files** | 90.0% | 91.0% | ❌ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|--------|
| `Module Large Report` | 91.33% / 90.0% | 20.0% / 91.0% | ✅/❌ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|
| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 90.5% | ❌ |""",
"""**Module: module small**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 97.0% | 29.0% | ✅ |
| **Changed Files** | 0.0% | 37.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|--------|
| `Module Small Report` | 97.0% / 0.0% | 29.0% / 37.0% | ✅/✅ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|

No changed file in reports.""",
]

comment_module_detail_instruction_with_modules_with_bs = [
"""**Module: context/notification**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 92.33% | 22.0% | +92.33% | ✅ |\n| **Changed Files** | 0.0% | 60.0% | 0.0% | ✅ |\n\nNo changed file in report.""",
"""**Module: context/user-info**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 91.5% | 21.0% | +22.0% | ✅ |\n| **Changed Files** | 89.0% | 59.0% | +44.0% | ✅ |""",
"""**Module: module_large**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 91.33% | 20.0% | -4.17% | ✅ |\n| **Changed Files** | 90.0% | 91.0% | -5.0% | ❌ |""",
"""**Module: module small**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 97.0% | 29.0% | +97.0% | ✅ |\n| **Changed Files** | 0.0% | 37.0% | 0.0% | ✅ |\n\nNo changed file in report.""",
]

comment_module_detailed_instruction_with_modules_no_module_thresholds_not_skip_changed = [
"""**Module: context/notification**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 92.33% | 75.0% | ✅ |
| **Changed Files** | 0.0% | 80.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|--------|
| `notification: API Module Report` | 95.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `notification: Client HTTP Module Report` | 90.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `notification: Plugins Module Report` | 92.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|

No changed file in reports.""",
"""**Module: context/user-info**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 91.5% | 75.0% | ✅ |
| **Changed Files** | 89.0% | 80.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|--------|
| `user-info:  Controller Module Report` | 93.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `user-info: API Module Report` | 95.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 75.0% / 80.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 75.0% / 80.0% | ✅/✅ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|
| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 65.0% | ✅ |
| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 65.0% | ✅ |""",
"""**Module: module_large**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 91.33% | 75.0% | ✅ |
| **Changed Files** | 90.0% | 80.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|--------|
| `Module Large Report` | 91.33% / 90.0% | 75.0% / 80.0% | ✅/✅ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|
| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 65.0% | ✅ |""",
"""**Module: module small**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 97.0% | 75.0% | ✅ |
| **Changed Files** | 0.0% | 80.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|--------|
| `Module Small Report` | 97.0% / 0.0% | 75.0% / 80.0% | ✅/✅ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|

No changed file in reports.""",
]

comment_module_detailed_instruction_with_modules_no_module_thresholds_not_skip_changed_with_bs = [
"""**Module: context/notification**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 92.33% | 75.0% | +92.33% | ✅ |
| **Changed Files** | 0.0% | 80.0% | 0.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `notification: API Module Report` | 95.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `notification: Client HTTP Module Report` | 90.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `notification: Plugins Module Report` | 92.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |

| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|

No changed file in reports.""",
"""**Module: context/user-info**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 91.5% | 75.0% | +22.0% | ✅ |
| **Changed Files** | 89.0% | 80.0% | +44.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `user-info:  Controller Module Report` | 93.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `user-info: API Module Report` | 95.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 75.0% / 80.0% | +80.0% / +80.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 75.0% / 80.0% | +8.0% / +8.0% | ✅/✅ |

| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 65.0% | +80.0% | ✅ |
| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 65.0% | +8.0% | ✅ |""",
"""**Module: module_large**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 91.33% | 75.0% | -4.17% | ✅ |\n| **Changed Files** | 90.0% | 80.0% | -5.0% | ✅ |\n\n| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |\n|--------|----------|-----------|------------|--------|\n| `Module Large Report` | 91.33% / 90.0% | 75.0% / 80.0% | -4.17% / -5.0% | ✅/✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 65.0% | -5.0% | ✅ |""",
"""**Module: module small**\n\n| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |\n|-------------------|-----|-----|-----|----|\n| **Overall**       | 97.0% | 75.0% | +97.0% | ✅ |\n| **Changed Files** | 0.0% | 80.0% | 0.0% | ✅ |\n\n| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |\n|--------|----------|-----------|------------|--------|\n| `Module Small Report` | 97.0% / 0.0% | 75.0% / 80.0% | 0.0% / 0.0% | ✅/✅ |\n\n| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n\nNo changed file in reports.""",
]

comment_module_detailed_instruction_with_modules_no_module_thresholds_skip_changed = [
"""**Module: context/user-info**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 91.5% | 75.0% | ✅ |
| **Changed Files** | 89.0% | 80.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|--------|
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 75.0% / 80.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 75.0% / 80.0% | ✅/✅ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|
| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 65.0% | ✅ |
| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 65.0% | ✅ |""",
"""**Module: module_large**

| Metric (instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**       | 91.33% | 75.0% | ✅ |
| **Changed Files** | 90.0% | 80.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|--------|
| `Module Large Report` | 91.33% / 90.0% | 75.0% / 80.0% | ✅/✅ |

| File Path | Coverage | Threshold | Status |
|-----------|----------|-----------|--------|
| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 65.0% | ✅ |""",
]

comment_module_detailed_instruction_with_modules_no_module_thresholds_skip_changed_with_bs = [
"""**Module: context/user-info**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 91.5% | 75.0% | +22.0% | ✅ |
| **Changed Files** | 89.0% | 80.0% | +44.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `user-info: Client HTTP Module Report` | 90.0% / 90.0% | 75.0% / 80.0% | +80.0% / +80.0% | ✅/✅ |
| `user-info: Implementation Module Report` | 88.0% / 88.0% | 75.0% / 80.0% | +8.0% / +8.0% | ✅/✅ |

| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [ClientHttpClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-233a8df372c1ee3631d77bd1afb2eb2c5729cdb125b277a3b0eb51a4933b888a) | 90.0% | 65.0% | +80.0% | ✅ |
| [ImplementationClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-7a267b2f062048b58eaf9c03df9857a0b95e8425451a7a68e18508a2ccb0d316) | 88.0% | 65.0% | +8.0% | ✅ |""",
"""**Module: module_large**

| Metric (instruction) | Coverage | Threshold | Δ Coverage | Status |
|-------------------|-----|-----|-----|----|
| **Overall**       | 91.33% | 75.0% | -4.17% | ✅ |
| **Changed Files** | 90.0% | 80.0% | -5.0% | ✅ |

| Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|----------|-----------|------------|--------|
| `Module Large Report` | 91.33% / 90.0% | 75.0% / 80.0% | -4.17% / -5.0% | ✅/✅ |

| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [BigClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-ead3b50565c5dda5dc7e32be690e80a71f6e317d66aaa386b5942b484476832d) | 90.0% | 65.0% | -5.0% | ✅ |""",
]

changed_files = [
    'com/example/user-info/implementation/ImplementationClass.java',
    'com/example/user-info/client-http/ClientHttpClass.java',
    'com/example/module_large/BigClass.java',
]

changed_files_two_in_report = [
    'com/example/user-info/implementation/ImplementationClass.java',
    'com/example/user-info/client-http/ClientHttpClass.java',
    'com/example/module_large/BigClass.java',
    'com/example/module_large/MidClass.java',
]

changed_files_none_in_report = [
    'com/example/module_large/test.config',
]

changed_files_large_only = [
    'com/example/module_large/BigClass.java',
]

modules = {
    "context/notification": 'test_project/context/notification',
    "context/user-info": 'test_project/context/user-info',
    "module_large": 'test_project/module_large',
    "module small": 'test_project/module small',
}

modules_partial_definition_1_report = {
    "context/notification": 'test_project/context/notification',
    "context/user-info": 'test_project/context/user-info',
    "module small": 'test_project/module small',
}

modules_partial_definition_2_reports = {
    "context/notification": 'test_project/context/notification',
    "module_large": 'test_project/module_large',
    "module small": 'test_project/module small',
}

modules_partial_definition_3_reports = {
    "context/notification": 'test_project/context/notification',
    "module small": 'test_project/module small',
}

modules_thresholds = {
    "context/notification": (22.0, 60.0, 55.0),
    "context/user-info": (21.0, 59.0, 55.0),
    "module_large": (20.0, 91.0, 90.5),
    "module small": (29.0, 37.0, 35.0),
}

modules_thresholds_100 = {
    "context/notification": (22.0, 60.0, 55.0),
    "context/user-info": (21.0, 59.0, 55.0),
    "module_large": (20.0, 91.0, 90.5),
    "module small": (100.0, 37.0, 35.0),
}

modules_thresholds_89 = {
    "context/notification": (22.0, 60.0, 55.0),
    "context/user-info": (89.0, 59.0, 55.0),
    "module_large": (20.0, 91.0, 90.5),
    "module small": (100.0, 37.0, 35.0),
}

modules_thresholds_100_partial_definition_1_report = {
    "context/notification": (22.0, 60.0, 55.0),
    "context/user-info": (21.0, 59.0, 55.0),
    "module small": (100.0, 37.0, 35.0),
}

modules_thresholds_100_partial_definition_2_reports = {
    "context/notification": (22.0, 60.0, 55.0),
    "module_large": (20.0, 91.0, 90.5),
    "module small": (100.0, 37.0, 35.0),
}

modules_thresholds_100_partial_definition_3_reports = {
    "context/notification": (22.0, 60.0, 55.0),
    "module small": (100.0, 37.0, 35.0),
}

modules_thresholds_100_all = {
    "context/notification": (100.0, 100.0, 100.0),
    "context/user-info": (100.0, 100.0, 100.0),
    "module_large": (100.0, 100.0, 100.0),
    "module small": (100.0, 100.0, 100.0),
}

@pytest.fixture
def jacoco_report():
    return JaCoCoReport()

def test_run_not_pull_request_event(jacoco_report):
    with patch.object(ActionInputs, 'get_event_name', return_value='push'):
        jacoco_report.run()
        assert "Not a pull request event." in jacoco_report.violations

def test_run_no_pr_number(jacoco_report):
    with patch.object(ActionInputs, 'get_event_name', return_value='pull_request'):
        with patch.object(ActionInputs, 'get_token', return_value='fake_token'):
            with patch('jacoco_report.utils.github.GitHub.get_pr_number', return_value=None):
                jacoco_report.run()
                assert "No pull request number found." in jacoco_report.violations

def test_run_no_jacoco_xml_files(jacoco_report, caplog, mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_event_name", return_value='pull_request')
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_token", return_value='fake_token')
    mocker.patch("jacoco_report.utils.github.GitHub.get_pr_number", return_value=1)
    mocker.patch("jacoco_report.jacoco_report.JaCoCoReport._scan_jacoco_xml_files", return_value=[])
    mock_add_comment = mocker.patch('jacoco_report.utils.github.GitHub.add_comment', return_value=None)

    with caplog.at_level(logging.ERROR):
        jacoco_report.run()
        assert jacoco_report.total_overall_coverage == 0.0
        assert jacoco_report.total_changed_files_coverage == 0.0
        assert "No input JaCoCo xml file found. No comment will be generated." in caplog.text
        assert jacoco_report.violations[0] == "No input JaCoCo xml file found."
        mock_add_comment.assert_not_called()

def test_run_successful_empty_no_baseline(jacoco_report, mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_event_name", return_value='pull_request')
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_token", return_value='fake_token')
    mocker.patch("jacoco_report.utils.github.GitHub.get_pr_number", return_value=35)
    mocker.patch("jacoco_report.jacoco_report.JaCoCoReport._scan_jacoco_xml_files", return_value=[f'{os.getcwd()}/tests/data/module_b/target/jacoco_no_data.xml'])
    mocker.patch("jacoco_report.utils.github.GitHub.get_pr_changed_files", return_value=[])
    mock_add_comment = mocker.patch('jacoco_report.utils.github.GitHub.add_comment', return_value=None)

    jacoco_report.run()

    assert jacoco_report.total_overall_coverage == 0.0
    assert jacoco_report.total_changed_files_coverage == 0.0
    assert jacoco_report.total_overall_coverage_passed is True
    assert jacoco_report.total_changed_files_coverage_passed is True
    assert jacoco_report.violations == []

    mock_add_comment.assert_called_once_with(35, comment_no_data_no_baseline)

def test_run_successful_empty_with_baseline(jacoco_report, mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_event_name", return_value='pull_request')
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_token", return_value='fake_token')
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_baseline_paths", return_value=['fake/path'])
    mocker.patch("jacoco_report.utils.github.GitHub.get_pr_number", return_value=35)
    mocker.patch("jacoco_report.jacoco_report.JaCoCoReport._scan_jacoco_xml_files", return_value=[f'{os.getcwd()}/tests/data/module_b/target/jacoco_no_data.xml'])
    mocker.patch("jacoco_report.utils.github.GitHub.get_pr_changed_files", return_value=[])
    mock_add_comment = mocker.patch('jacoco_report.utils.github.GitHub.add_comment', return_value=None)

    jacoco_report.run()

    assert jacoco_report.total_overall_coverage == 0.0
    assert jacoco_report.total_changed_files_coverage == 0.0
    assert jacoco_report.total_overall_coverage_passed is True
    assert jacoco_report.total_changed_files_coverage_passed is True
    assert jacoco_report.violations == []

    mock_add_comment.assert_called_once_with(35, comment_no_data_with_baseline)


one_source_file_scenarios = [
    (MetricTypeEnum.INSTRUCTION, CommentModeEnum.SINGLE, SensitivityEnum.MINIMAL, comment_one_file_single_minimalist_instruction, 90.0, 80.0, True, True),
    (MetricTypeEnum.LINE, CommentModeEnum.SINGLE, SensitivityEnum.MINIMAL, comment_one_file_single_minimalist_line, 80.0, 60.0, True, True),
    (MetricTypeEnum.BRANCH, CommentModeEnum.SINGLE, SensitivityEnum.MINIMAL, comment_one_file_single_minimalist_branch, 75.0, 0.0, True, True),
    (MetricTypeEnum.COMPLEXITY, CommentModeEnum.SINGLE, SensitivityEnum.MINIMAL, comment_one_file_single_minimalist_complexity, 75.0, 50.0, True, True),
    (MetricTypeEnum.METHOD, CommentModeEnum.SINGLE, SensitivityEnum.MINIMAL, comment_one_file_single_minimalist_method, 100.0, 0.0, True, True),
    (MetricTypeEnum.CLASS, CommentModeEnum.SINGLE, SensitivityEnum.MINIMAL, comment_one_file_single_minimalist_class, 100.0, 0.0, True, True),
]

@pytest.mark.parametrize("metric, mode, template, comment, ov_cov, ch_cov, ov_cov_b, ch_cov_b", one_source_file_scenarios)
def test_successful_one_source_file (jacoco_report, metric, mode, template, comment, ov_cov, ch_cov, ov_cov_b, ch_cov_b, mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_event_name", return_value='pull_request')
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_token", return_value='fake_token')
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_title", return_value='Custom Title')
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value=metric)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_comment_mode", return_value=mode)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_sensitivity", return_value=template)
    mocker.patch("jacoco_report.utils.github.GitHub.get_pr_number", return_value=35)
    mocker.patch("jacoco_report.jacoco_report.JaCoCoReport._scan_jacoco_xml_files", return_value=[f'{os.getcwd()}/tests/data/module_c/target/jacoco_one_source_file.xml'])
    mocker.patch("jacoco_report.utils.github.GitHub.get_pr_changed_files", return_value=['com/example/ExampleClass.java'])

    mock_add_comment = mocker.patch('jacoco_report.utils.github.GitHub.add_comment', return_value=None)

    jacoco_report.run()

    assert jacoco_report.total_overall_coverage == ov_cov
    assert jacoco_report.total_changed_files_coverage == ch_cov
    assert jacoco_report.total_overall_coverage_passed is ov_cov_b
    assert jacoco_report.total_changed_files_coverage_passed is ch_cov_b
    assert jacoco_report.violations == []

    mock_add_comment.assert_called_once_with(35, comment)

# MORE FILES

more_source_files_scenarios = [
    ("1", CommentModeEnum.SINGLE, SensitivityEnum.MINIMAL, {}, {}, changed_files, [comment_single_minimalist_instruction], 9, 0, [], False, False),
    ("2", CommentModeEnum.SINGLE, SensitivityEnum.MINIMAL, {}, {}, changed_files, [comment_single_minimalist_instruction_with_bs], 9, 0, [], False, True),
    ("3", CommentModeEnum.SINGLE, SensitivityEnum.MINIMAL, modules, {}, changed_files, [comment_single_minimalist_instruction], 9, 4, [], False, False),
    ("4", CommentModeEnum.SINGLE, SensitivityEnum.MINIMAL, modules, {}, changed_files, [comment_single_minimalist_instruction_with_bs], 9, 4, [], False, True),
    ("5", CommentModeEnum.SINGLE, SensitivityEnum.SUMMARY, {}, {}, changed_files, [comment_single_minimalist_instruction_summary], 9, 0, [], False, False),
    ("6", CommentModeEnum.SINGLE, SensitivityEnum.SUMMARY, {}, {}, changed_files, [comment_single_minimalist_instruction_with_bs_summary], 9, 0, [], False, True),
    ("7", CommentModeEnum.SINGLE, SensitivityEnum.SUMMARY, modules, modules_thresholds, changed_files, [comment_more_files_single_summary_instruction_with_modules], 9, 4, ["Module 'module_large' changed files coverage 90.0 is below the threshold 91.0.", "Report 'Module Large Report' changed files coverage 90.0 is below the threshold 91.0."], False, False),
    ("8", CommentModeEnum.SINGLE, SensitivityEnum.SUMMARY, modules, modules_thresholds, changed_files, [comment_more_files_single_summary_instruction_with_modules_with_bs], 9, 4, ["Module 'module_large' changed files coverage 90.0 is below the threshold 91.0.", "Report 'Module Large Report' changed files coverage 90.0 is below the threshold 91.0."], False, True),
    ("9", CommentModeEnum.SINGLE, SensitivityEnum.SUMMARY, modules, {}, changed_files, [comment_more_files_single_summary_instruction_with_modules_no_module_thresholds], 9, 4, [], False, False),
    ("10", CommentModeEnum.SINGLE, SensitivityEnum.SUMMARY, modules, {}, changed_files, [comment_more_files_single_summary_instruction_with_modules_no_module_thresholds_with_bs], 9, 4, [], False, True),
    ("11", CommentModeEnum.SINGLE, SensitivityEnum.DETAIL, {}, {}, changed_files, [comment_more_files_single_detailed_instruction_no_modules], 9, 0, [], False, False),
    ("12", CommentModeEnum.SINGLE, SensitivityEnum.DETAIL, {}, {}, changed_files, [comment_more_files_single_detailed_instruction_no_modules_with_bs], 9, 0, [], False, True),
    ("13", CommentModeEnum.SINGLE, SensitivityEnum.DETAIL, modules, modules_thresholds, changed_files, [comment_more_files_single_detailed_instruction_with_modules], 9, 4, ["Module 'module_large' changed files coverage 90.0 is below the threshold 91.0.", "Module Large Report' changed files coverage 90.0 is below the threshold 91.0.", "Module Large Report' changed file 'com/example/module_large/BigClass.java' coverage 90.0 is below the threshold 90.5."], False, False),
    ("14", CommentModeEnum.SINGLE, SensitivityEnum.DETAIL, modules, modules_thresholds, changed_files, [comment_more_files_single_detailed_instruction_with_modules_with_bs], 9, 4, ["Module 'module_large' changed files coverage 90.0 is below the threshold 91.0.", "Module Large Report' changed files coverage 90.0 is below the threshold 91.0.", "Module Large Report' changed file 'com/example/module_large/BigClass.java' coverage 90.0 is below the threshold 90.5."], False, True),
    ("15", CommentModeEnum.SINGLE, SensitivityEnum.DETAIL, modules, {}, changed_files, [comment_more_files_single_detailed_instruction_with_modules_no_module_thresholds_not_skip_changed], 9, 4, [], False, False),
    ("16", CommentModeEnum.SINGLE, SensitivityEnum.DETAIL, modules, {}, changed_files, [comment_more_files_single_detailed_instruction_with_modules_no_module_thresholds_not_skip_changed_with_bs], 9, 4, [], False, True),
    ("17", CommentModeEnum.SINGLE, SensitivityEnum.DETAIL, modules, {}, changed_files, [comment_more_files_single_detailed_instruction_with_modules_no_module_thresholds_skip_changed], 9, 4, [], True, False),
    ("18", CommentModeEnum.SINGLE, SensitivityEnum.DETAIL, modules, {}, changed_files, [comment_more_files_single_detailed_instruction_with_modules_no_module_thresholds_skip_changed_with_bs], 9, 4, [], True, True),
    ("19", CommentModeEnum.MULTI, SensitivityEnum.MINIMAL, {}, {}, changed_files, comment_multi_minimalist_instruction, 9, 0, [], False, False),
    ("20", CommentModeEnum.MULTI, SensitivityEnum.MINIMAL, {}, {}, changed_files, comment_multi_minimalist_instruction_skip, 9, 0, [], True, False),
    ("21", CommentModeEnum.MULTI, SensitivityEnum.MINIMAL, {}, {}, changed_files, comment_multi_minimalist_instruction_with_bs, 9, 0, [], False, True),
    ("22", CommentModeEnum.MULTI, SensitivityEnum.MINIMAL, {}, {}, changed_files, comment_multi_minimalist_instruction_with_bs_skip, 9, 0, [], True, True),
    ("23", CommentModeEnum.MULTI, SensitivityEnum.MINIMAL, modules, {}, changed_files, comment_multi_minimalist_instruction, 9, 0, [], False, False),
    ("24", CommentModeEnum.MULTI, SensitivityEnum.MINIMAL, modules, {}, changed_files, comment_multi_minimalist_instruction_with_bs, 9, 0, [], False, True),
    ("25", CommentModeEnum.MULTI, SensitivityEnum.SUMMARY, {}, {}, changed_files, comment_multi_minimalist_instruction, 9, 0, [], False, False),
    ("26", CommentModeEnum.MULTI, SensitivityEnum.SUMMARY, {}, {}, changed_files, comment_multi_minimalist_instruction_with_bs, 9, 0, [], False, True),
    ("27", CommentModeEnum.MULTI, SensitivityEnum.SUMMARY, modules, modules_thresholds, changed_files, comment_multi_summary_instruction_with_modules, 9, 0, ["Report 'Module Large Report' changed files coverage 90.0 is below the threshold 91.0."], False, False),
    ("28", CommentModeEnum.MULTI, SensitivityEnum.SUMMARY, modules, modules_thresholds, changed_files, comment_multi_summary_instruction_with_modules_with_bs, 9, 0, ["Report 'Module Large Report' changed files coverage 90.0 is below the threshold 91.0."], False, True),
    ("29", CommentModeEnum.MULTI, SensitivityEnum.SUMMARY, modules, {}, changed_files, comment_multi_minimalist_instruction, 9, 0, [], False, False),
    ("30", CommentModeEnum.MULTI, SensitivityEnum.SUMMARY, modules, {}, changed_files, comment_multi_minimalist_instruction_with_bs, 9, 0, [], False, True),
    ("31", CommentModeEnum.MULTI, SensitivityEnum.DETAIL, {}, {}, changed_files, comment_multi_detailed_instruction_no_modules, 9, 0, [], False, False),
    ("32", CommentModeEnum.MULTI, SensitivityEnum.DETAIL, {}, {}, changed_files, comment_multi_detailed_instruction_no_modules_with_bs, 9, 0, [], False, True),
    ("33", CommentModeEnum.MULTI, SensitivityEnum.DETAIL, modules, modules_thresholds, changed_files, comment_multi_detailed_instruction_with_modules, 9, 0, ["Report 'Module Large Report' changed files coverage 90.0 is below the threshold 91.0.", "Report 'Module Large Report' changed file 'com/example/module_large/BigClass.java' coverage 90.0 is below the threshold 90.5."], False, False),
    ("34", CommentModeEnum.MULTI, SensitivityEnum.DETAIL, modules, modules_thresholds, changed_files, comment_multi_detailed_instruction_with_modules_with_bs, 9, 0, ["Report 'Module Large Report' changed files coverage 90.0 is below the threshold 91.0.", "Report 'Module Large Report' changed file 'com/example/module_large/BigClass.java' coverage 90.0 is below the threshold 90.5."], False, True),
    ("35", CommentModeEnum.MULTI, SensitivityEnum.DETAIL, modules, {}, changed_files, comment_multi_detailed_instruction_with_modules_no_module_thresholds_not_skip_changed, 9, 0, [], False, False),
    ("36", CommentModeEnum.MULTI, SensitivityEnum.DETAIL, modules, {}, changed_files, comment_multi_detailed_instruction_with_modules_no_module_thresholds_not_skip_changed_with_bs, 9, 0, [], False, True),
    ("37", CommentModeEnum.MULTI, SensitivityEnum.DETAIL, modules, {}, changed_files, comment_multi_detailed_instruction_with_modules_no_module_thresholds_skip_changed, 9, 0, [], True, False),
    ("38", CommentModeEnum.MULTI, SensitivityEnum.DETAIL, modules, {}, changed_files, comment_multi_detailed_instruction_with_modules_no_module_thresholds_skip_changed_with_bs, 9, 0, [], True, True),
    ("39", CommentModeEnum.MODULE, SensitivityEnum.MINIMAL, modules, {}, changed_files, comment_module_minimalist_instruction, 9, 4, [], False, False),
    ("40", CommentModeEnum.MODULE, SensitivityEnum.MINIMAL, modules, {}, changed_files, comment_module_minimalist_instruction_with_bs, 9, 4, [], False, True),
    ("41", CommentModeEnum.MODULE, SensitivityEnum.SUMMARY, modules, {}, changed_files, comment_module_minimalist_instruction_summary, 9, 4, [], False, False),
    ("42", CommentModeEnum.MODULE, SensitivityEnum.SUMMARY, modules, {}, changed_files, comment_module_minimalist_instruction_with_bs_summary, 9, 4, [], False, True),
    ("43", CommentModeEnum.MODULE, SensitivityEnum.SUMMARY, modules, modules_thresholds, changed_files, comment_module_summary_instruction_with_modules, 9, 4, ["Module 'module_large' changed files coverage 90.0 is below the threshold 91.0.", "Report 'Module Large Report' changed files coverage 90.0 is below the threshold 91.0."], False, False),
    ("44", CommentModeEnum.MODULE, SensitivityEnum.SUMMARY, modules, modules_thresholds, changed_files, comment_module_summary_instruction_with_modules_with_bs, 9, 4, ["Module 'module_large' changed files coverage 90.0 is below the threshold 91.0.", "Report 'Module Large Report' changed files coverage 90.0 is below the threshold 91.0."], False, True),
    ("45", CommentModeEnum.MODULE, SensitivityEnum.DETAIL, modules, modules_thresholds, changed_files, comment_module_detail_instruction_with_modules, 9, 4, ["Module 'module_large' changed files coverage 90.0 is below the threshold 91.0.", "Report 'Module Large Report' changed files coverage 90.0 is below the threshold 91.0.", "Report 'Module Large Report' changed file 'com/example/module_large/BigClass.java' coverage 90.0 is below the threshold 90.5."], False, False),
    ("46", CommentModeEnum.MODULE, SensitivityEnum.DETAIL, modules, modules_thresholds, changed_files, comment_module_detailed_instruction_with_modules_with_bs, 9, 4, ["Module 'module_large' changed files coverage 90.0 is below the threshold 91.0.", "Report 'Module Large Report' changed files coverage 90.0 is below the threshold 91.0.", "Report 'Module Large Report' changed file 'com/example/module_large/BigClass.java' coverage 90.0 is below the threshold 90.5."], False, True),
    ("47", CommentModeEnum.MODULE, SensitivityEnum.DETAIL, modules, {}, changed_files, comment_module_detailed_instruction_with_modules_no_module_thresholds_not_skip_changed, 9, 4, [], False, False),
    ("48", CommentModeEnum.MODULE, SensitivityEnum.DETAIL, modules, {}, changed_files, comment_module_detailed_instruction_with_modules_no_module_thresholds_not_skip_changed_with_bs, 9, 4, [], False, True),
    ("49", CommentModeEnum.MODULE, SensitivityEnum.DETAIL, modules, {}, changed_files, comment_module_detailed_instruction_with_modules_no_module_thresholds_skip_changed, 9, 4, [], True, False),
    ("50", CommentModeEnum.MODULE, SensitivityEnum.DETAIL, modules, {}, changed_files, comment_module_detailed_instruction_with_modules_no_module_thresholds_skip_changed_with_bs, 9, 4, [], True, True),
    # failing module and reports without changed files
    ("51", CommentModeEnum.MODULE, SensitivityEnum.DETAIL, modules, modules_thresholds_100, changed_files, comment_module_detailed_instruction_with_modules_with_bs_fail_non_changed_module, 9, 4, ["Module 'module_large' changed files coverage 90.0 is below the threshold 91.0.", "Report 'Module Large Report' changed files coverage 90.0 is below the threshold 91.0.", "Report 'Module Large Report' changed file 'com/example/module_large/BigClass.java' coverage 90.0 is below the threshold 90.5."], True, True),
    ("52", CommentModeEnum.SINGLE, SensitivityEnum.DETAIL, modules, modules_thresholds_100, changed_files, [comment_more_files_single_detailed_instruction_with_modules_with_bs_fail_module], 9, 4, ["Module 'module_large' changed files coverage 90.0 is below the threshold 91.0.", "Report 'Module Large Report' changed files coverage 90.0 is below the threshold 91.0.", "Report 'Module Large Report' changed file 'com/example/module_large/BigClass.java' coverage 90.0 is below the threshold 90.5."], True, True),
    ("53", CommentModeEnum.MULTI, SensitivityEnum.DETAIL, modules, modules_thresholds_100, changed_files, comment_multi_detailed_instruction_with_modules_with_bs_fail_module, 9, 0, ["Report 'Module Large Report' changed files coverage 90.0 is below the threshold 91.0.", "Report 'Module Large Report' changed file 'com/example/module_large/BigClass.java' coverage 90.0 is below the threshold 90.5."], True, True),
    # failing report in passing module
    ("54", CommentModeEnum.MODULE, SensitivityEnum.DETAIL, modules, modules_thresholds_89, changed_files_large_only, comment_module_detailed_instruction_with_modules_with_bs_fail_non_changed_module_fail_report, 9, 4, ["Module 'module_large' changed files coverage 90.0 is below the threshold 91.0.", "Report 'Module Large Report' changed files coverage 90.0 is below the threshold 91.0.", "Report 'Module Large Report' changed file 'com/example/module_large/BigClass.java' coverage 90.0 is below the threshold 90.5."], True, True),
    # only partial set of modules
    ("55", CommentModeEnum.SINGLE, SensitivityEnum.DETAIL, modules_partial_definition_1_report, modules_thresholds_100_partial_definition_1_report, changed_files, [comment_more_files_single_detailed_instruction_with_partial_modules_1], 9, 4, [], True, True),
    ("56", CommentModeEnum.MULTI, SensitivityEnum.DETAIL, modules_partial_definition_1_report, modules_thresholds_100_partial_definition_1_report, changed_files, comment_multi_detailed_instruction_with_modules_report_1, 9, 0, [], True, True),
    ("57", CommentModeEnum.MODULE, SensitivityEnum.DETAIL, modules_partial_definition_1_report, modules_thresholds_100_partial_definition_1_report, changed_files, comment_module_detailed_instruction_with_modules_with_bs_report_1, 9, 4, [], True, True),
    ("58", CommentModeEnum.SINGLE, SensitivityEnum.DETAIL, modules_partial_definition_2_reports, modules_thresholds_100_partial_definition_2_reports, changed_files, [comment_more_files_single_detailed_instruction_with_partial_modules_2], 9, 4, ["Module 'module_large' changed files coverage 90.0 is below the threshold 91.0.", "Report 'Module Large Report' changed files coverage 90.0 is below the threshold 91.0.", "Report 'Module Large Report' changed file 'com/example/module_large/BigClass.java' coverage 90.0 is below the threshold 90.5."], True, True),
    ("59", CommentModeEnum.MULTI, SensitivityEnum.DETAIL, modules_partial_definition_2_reports, modules_thresholds_100_partial_definition_2_reports, changed_files, comment_multi_detailed_instruction_with_modules_with_bs_partial_modules_2, 9, 0, ["Report 'Module Large Report' changed files coverage 90.0 is below the threshold 91.0.", "Report 'Module Large Report' changed file 'com/example/module_large/BigClass.java' coverage 90.0 is below the threshold 90.5."], True, True),
    ("60", CommentModeEnum.MODULE, SensitivityEnum.DETAIL, modules_partial_definition_2_reports, modules_thresholds_100_partial_definition_2_reports, changed_files, comment_module_detailed_instruction_with_modules_with_bs_partial_modules_report_2, 9, 4, ["Module 'module_large' changed files coverage 90.0 is below the threshold 91.0.", "Report 'Module Large Report' changed files coverage 90.0 is below the threshold 91.0.", "Report 'Module Large Report' changed file 'com/example/module_large/BigClass.java' coverage 90.0 is below the threshold 90.5."], True, True),
    ("61", CommentModeEnum.SINGLE, SensitivityEnum.DETAIL, modules_partial_definition_3_reports, modules_thresholds_100_partial_definition_3_reports, changed_files, [comment_more_files_single_detailed_instruction_with_partial_modules_3], 9, 3, [], True, True),
    ("62", CommentModeEnum.MULTI, SensitivityEnum.DETAIL, modules_partial_definition_3_reports, modules_thresholds_100_partial_definition_3_reports, changed_files, comment_multi_detailed_instruction_with_modules_with_bs_partial_modules_3, 9, 0, [], True, True),
    ("63", CommentModeEnum.MODULE, SensitivityEnum.DETAIL, modules_partial_definition_3_reports, modules_thresholds_100_partial_definition_3_reports, changed_files, comment_module_detailed_instruction_with_modules_with_bs_partial_modules_report_3, 9, 3, [], True, True),
    # multiple changed files per report file
    ("64", CommentModeEnum.SINGLE, SensitivityEnum.DETAIL, modules, modules_thresholds, changed_files_two_in_report, [comment_single_detailed_two_changed_files_in_report], 9, 4, ["Module 'module_large' changed files coverage 90.25 is below the threshold 91.0.", "Report 'Module Large Report' changed files coverage 90.41 is below the threshold 91.0.", "Report 'Module Large Report' changed file 'com/example/module_large/BigClass.java' coverage 90.0 is below the threshold 90.5."], True, False),
    ("65", CommentModeEnum.MULTI, SensitivityEnum.DETAIL, modules, modules_thresholds, changed_files_two_in_report, comment_multi_detailed_two_changed_files_in_report, 9, 0, ["Report 'Module Large Report' changed files coverage 90.41 is below the threshold 91.0.", "Report 'Module Large Report' changed file 'com/example/module_large/BigClass.java' coverage 90.0 is below the threshold 90.5."], True, False),
    ("66", CommentModeEnum.MODULE, SensitivityEnum.DETAIL, modules, modules_thresholds, changed_files_two_in_report, comment_module_detailed_two_changed_files_in_report, 9, 4, ["Module 'module_large' changed files coverage 90.25 is below the threshold 91.0.", "Report 'Module Large Report' changed files coverage 90.41 is below the threshold 91.0.", "Report 'Module Large Report' changed file 'com/example/module_large/BigClass.java' coverage 90.0 is below the threshold 90.5."], True, False),
    # no changed files in report files = evaluation passed without any violation
    ("67", CommentModeEnum.SINGLE, SensitivityEnum.MINIMAL, modules, modules_thresholds_100_all, changed_files_none_in_report, [], 9, 4, [], True, False),
    ("68", CommentModeEnum.SINGLE, SensitivityEnum.SUMMARY, modules, modules_thresholds_100_all, changed_files_none_in_report, [], 9, 4, [], True, False),
    ("69", CommentModeEnum.SINGLE, SensitivityEnum.DETAIL, modules, modules_thresholds_100_all, changed_files_none_in_report, [], 9, 4, [], True, False),
    ("70", CommentModeEnum.MULTI, SensitivityEnum.MINIMAL, modules, modules_thresholds_100_all, changed_files_none_in_report, [], 9, 0, [], True, False),
    ("71", CommentModeEnum.MULTI, SensitivityEnum.SUMMARY, modules, modules_thresholds_100_all, changed_files_none_in_report, [], 9, 0, [], True, False),
    ("72", CommentModeEnum.MULTI, SensitivityEnum.DETAIL, modules, modules_thresholds_100_all, changed_files_none_in_report, [], 9, 0, [], True, False),
    ("73", CommentModeEnum.MODULE, SensitivityEnum.MINIMAL, modules, modules_thresholds_100_all, changed_files_none_in_report, [], 9, 4, [], True, False),
    ("74", CommentModeEnum.MODULE, SensitivityEnum.SUMMARY, modules, modules_thresholds_100_all, changed_files_none_in_report, [], 9, 4, [], True, False),
    ("75", CommentModeEnum.MODULE, SensitivityEnum.DETAIL, modules, modules_thresholds_100_all, changed_files_none_in_report, [], 9, 4, [], True, False),
]

@pytest.mark.parametrize("id, mode, template, modules, modules_thresholds, changed_files, expected_comments, evaluated_cov_reports, evaluated_cov_modules, violations, skip_unchanged, use_baseline", more_source_files_scenarios)
def test_successful_more_source_files(jacoco_report, id, mode, template, modules, modules_thresholds, changed_files, expected_comments, evaluated_cov_reports, evaluated_cov_modules, violations, skip_unchanged, use_baseline, mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_event_name", return_value='pull_request')
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_token", return_value='fake_token')
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_comment_mode", return_value=mode)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_sensitivity", return_value=template)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_paths", return_value=["tests/data/test_project/**/jacoco.xml"])
    # mocker.patch("jacoco_report.action_inputs.ActionInputs.get_paths", return_value=["data/test_project/**/jacoco.xml"])
    if use_baseline:
        # mocker.patch("jacoco_report.action_inputs.ActionInputs.get_baseline_paths", return_value=["data_baseline/**/*.xml"])
        mocker.patch("jacoco_report.action_inputs.ActionInputs.get_baseline_paths", return_value=["tests/data_baseline/**/*.xml"])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_min_coverage_overall", return_value=75.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_min_coverage_changed_files", return_value=80.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_min_coverage_per_changed_file", return_value=65.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_modules", return_value=modules)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_modules_thresholds", return_value=modules_thresholds)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_repository", return_value="MoranaApps/jacoco-report")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_skip_unchanged", return_value=skip_unchanged)
    mocker.patch("jacoco_report.utils.github.GitHub.get_pr_number", return_value=35)
    mocker.patch("jacoco_report.utils.github.GitHub.get_pr_changed_files", return_value=changed_files)

    mock_add_comment = mocker.patch('jacoco_report.utils.github.GitHub.add_comment', return_value=None)

    jacoco_report.run()

    # for item in mock_add_comment.call_args_list:
    #     print(item)

    if mode == CommentModeEnum.SINGLE:
        assert mock_add_comment.call_count == len(expected_comments)

        if len(expected_comments):
            mock_add_comment.assert_called_once_with(35, expected_comments[0])
    else:
        # Check the count of calls
        assert mock_add_comment.call_count == len(expected_comments)

        if len(expected_comments):
            for expected_comment in expected_comments:
                mock_add_comment.assert_any_call(35, expected_comment)

    # Parse the JSON strings
    dict_evaluated_coverage_reports: dict = json.loads(jacoco_report.evaluated_coverage_reports)
    dict_evaluated_coverage_modules: dict = json.loads(jacoco_report.evaluated_coverage_modules)

    assert evaluated_cov_reports == len(dict_evaluated_coverage_reports)
    assert evaluated_cov_modules == len(dict_evaluated_coverage_modules)

    actual_merger_violations = " ".join(jacoco_report.violations)
    assert len(jacoco_report.violations) == len(violations)
    for violation in violations:
        assert violation in actual_merger_violations


single_minimal_violations = [
    'Global overall coverage 92.0 is below the threshold 100.0.',
    'Global changed files coverage 89.71 is below the threshold 100.0.'
]

single_summary_violations = [
    'Global overall coverage 92.0 is below the threshold 100.0.',
    'Global changed files coverage 89.71 is below the threshold 100.0.',
    "Report 'Module Large Report' overall coverage 91.33 is below the threshold 100.0.",
    "Report 'Module Large Report' changed files coverage 90.0 is below the threshold 100.0.",
    "Report 'user-info:  Controller Module Report' overall coverage 93.0 is below the threshold 100.0.",
    "Report 'user-info: Implementation Module Report' overall coverage 88.0 is below the threshold 100.0.",
    "Report 'user-info: Implementation Module Report' changed files coverage 88.0 is below the threshold 100.0.",
    "Report 'notification: API Module Report' overall coverage 95.0 is below the threshold 100.0.",
    "Report 'Module Small Report' overall coverage 97.0 is below the threshold 100.0.",
    "Report 'notification: Client HTTP Module Report' overall coverage 90.0 is below the threshold 100.0.",
    "Report 'user-info: API Module Report' overall coverage 95.0 is below the threshold 100.0.",
    "Report 'user-info: Client HTTP Module Report' overall coverage 90.0 is below the threshold 100.0.",
    "Report 'user-info: Client HTTP Module Report' changed files coverage 90.0 is below the threshold 100.0.",
    "Report 'notification: Plugins Module Report' overall coverage 92.0 is below the threshold 100.0."
]

single_summary_violations_with_modules = [
    'Global overall coverage 92.0 is below the threshold 100.0.',
    'Global changed files coverage 89.71 is below the threshold 100.0.',
    "Module 'context/notification' overall coverage 92.33 is below the threshold 100.0.",
    "Module 'context/user-info' overall coverage 91.5 is below the threshold 100.0.",
    "Module 'context/user-info' changed files coverage 89.0 is below the threshold 100.0.",
    "Module 'module_large' overall coverage 91.33 is below the threshold 100.0.",
    "Module 'module_large' changed files coverage 90.0 is below the threshold 100.0.",
    "Module 'module small' overall coverage 97.0 is below the threshold 100.0.",
    "Report 'Module Large Report' overall coverage 91.33 is below the threshold 100.0.",
    "Report 'Module Large Report' changed files coverage 90.0 is below the threshold 100.0.",
    "Report 'user-info:  Controller Module Report' overall coverage 93.0 is below the threshold 100.0.",
    "Report 'user-info: Implementation Module Report' overall coverage 88.0 is below the threshold 100.0.",
    "Report 'user-info: Implementation Module Report' changed files coverage 88.0 is below the threshold 100.0.",
    "Report 'notification: API Module Report' overall coverage 95.0 is below the threshold 100.0.",
    "Report 'Module Small Report' overall coverage 97.0 is below the threshold 100.0.",
    "Report 'notification: Client HTTP Module Report' overall coverage 90.0 is below the threshold 100.0.",
    "Report 'user-info: API Module Report' overall coverage 95.0 is below the threshold 100.0.",
    "Report 'user-info: Client HTTP Module Report' overall coverage 90.0 is below the threshold 100.0.",
    "Report 'user-info: Client HTTP Module Report' changed files coverage 90.0 is below the threshold 100.0.",
    "Report 'notification: Plugins Module Report' overall coverage 92.0 is below the threshold 100.0."
]

single_detail_violations = [
    'Global overall coverage 92.0 is below the threshold 100.0.',
    'Global changed files coverage 89.71 is below the threshold 100.0.',
    "Report 'Module Large Report' overall coverage 91.33 is below the threshold 100.0.",
    "Report 'Module Large Report' changed files coverage 90.0 is below the threshold 100.0.",
    "Report 'Module Large Report' changed file 'com/example/module_large/BigClass.java' coverage 90.0 is below the threshold 100.0.",
    "Report 'user-info:  Controller Module Report' overall coverage 93.0 is below the threshold 100.0.",
    "Report 'user-info: Implementation Module Report' overall coverage 88.0 is below the threshold 100.0.",
    "Report 'user-info: Implementation Module Report' changed files coverage 88.0 is below the threshold 100.0.",
    "Report 'user-info: Implementation Module Report' changed file 'com/example/user-info/implementation/ImplementationClass.java' coverage 88.0 is below the threshold 100.0.",
    "Report 'notification: API Module Report' overall coverage 95.0 is below the threshold 100.0.",
    "Report 'Module Small Report' overall coverage 97.0 is below the threshold 100.0.",
    "Report 'notification: Client HTTP Module Report' overall coverage 90.0 is below the threshold 100.0.",
    "Report 'user-info: API Module Report' overall coverage 95.0 is below the threshold 100.0.",
    "Report 'user-info: Client HTTP Module Report' overall coverage 90.0 is below the threshold 100.0.",
    "Report 'user-info: Client HTTP Module Report' changed files coverage 90.0 is below the threshold 100.0.",
    "Report 'user-info: Client HTTP Module Report' changed file 'com/example/user-info/client-http/ClientHttpClass.java' coverage 90.0 is below the threshold 100.0.",
    "Report 'notification: Plugins Module Report' overall coverage 92.0 is below the threshold 100.0."
]

single_detail_violations_with_modules = [
    'Global overall coverage 92.0 is below the threshold 100.0.',
    'Global changed files coverage 89.71 is below the threshold 100.0.',
    "Module 'context/notification' overall coverage 92.33 is below the threshold 100.0.",
    "Module 'context/user-info' overall coverage 91.5 is below the threshold 100.0.",
    "Module 'context/user-info' changed files coverage 89.0 is below the threshold 100.0.",
    "Module 'module_large' overall coverage 91.33 is below the threshold 100.0.",
    "Module 'module_large' changed files coverage 90.0 is below the threshold 100.0.",
    "Module 'module small' overall coverage 97.0 is below the threshold 100.0.",
    "Report 'Module Large Report' overall coverage 91.33 is below the threshold 100.0.",
    "Report 'Module Large Report' changed files coverage 90.0 is below the threshold 100.0.",
    "Report 'Module Large Report' changed file 'com/example/module_large/BigClass.java' coverage 90.0 is below the threshold 100.0.",
    "Report 'user-info:  Controller Module Report' overall coverage 93.0 is below the threshold 100.0.",
    "Report 'user-info: Implementation Module Report' overall coverage 88.0 is below the threshold 100.0.",
    "Report 'user-info: Implementation Module Report' changed files coverage 88.0 is below the threshold 100.0.",
    "Report 'user-info: Implementation Module Report' changed file 'com/example/user-info/implementation/ImplementationClass.java' coverage 88.0 is below the threshold 100.0.",
    "Report 'notification: API Module Report' overall coverage 95.0 is below the threshold 100.0.",
    "Report 'Module Small Report' overall coverage 97.0 is below the threshold 100.0.",
    "Report 'notification: Client HTTP Module Report' overall coverage 90.0 is below the threshold 100.0.",
    "Report 'user-info: API Module Report' overall coverage 95.0 is below the threshold 100.0.",
    "Report 'user-info: Client HTTP Module Report' overall coverage 90.0 is below the threshold 100.0.",
    "Report 'user-info: Client HTTP Module Report' changed files coverage 90.0 is below the threshold 100.0.",
    "Report 'user-info: Client HTTP Module Report' changed file 'com/example/user-info/client-http/ClientHttpClass.java' coverage 90.0 is below the threshold 100.0.",
    "Report 'notification: Plugins Module Report' overall coverage 92.0 is below the threshold 100.0."
]

multi_detail_violations = [
    "Report 'Module Large Report' overall coverage 91.33 is below the threshold 100.0.",
    "Report 'Module Large Report' changed files coverage 90.0 is below the threshold 100.0.",
    "Report 'Module Large Report' changed file 'com/example/module_large/BigClass.java' coverage 90.0 is below the threshold 100.0.",
    "Report 'user-info:  Controller Module Report' overall coverage 93.0 is below the threshold 100.0.",
    "Report 'user-info: Implementation Module Report' overall coverage 88.0 is below the threshold 100.0.",
    "Report 'user-info: Implementation Module Report' changed files coverage 88.0 is below the threshold 100.0.",
    "Report 'user-info: Implementation Module Report' changed file 'com/example/user-info/implementation/ImplementationClass.java' coverage 88.0 is below the threshold 100.0.",
    "Report 'notification: API Module Report' overall coverage 95.0 is below the threshold 100.0.",
    "Report 'Module Small Report' overall coverage 97.0 is below the threshold 100.0.",
    "Report 'notification: Client HTTP Module Report' overall coverage 90.0 is below the threshold 100.0.",
    "Report 'user-info: API Module Report' overall coverage 95.0 is below the threshold 100.0.",
    "Report 'user-info: Client HTTP Module Report' overall coverage 90.0 is below the threshold 100.0.",
    "Report 'user-info: Client HTTP Module Report' changed files coverage 90.0 is below the threshold 100.0.",
    "Report 'user-info: Client HTTP Module Report' changed file 'com/example/user-info/client-http/ClientHttpClass.java' coverage 90.0 is below the threshold 100.0.",
    "Report 'notification: Plugins Module Report' overall coverage 92.0 is below the threshold 100.0."
]

multi_minimal_violations = [
    "Report 'Module Large Report' overall coverage 91.33 is below the threshold 100.0.",
    "Report 'Module Large Report' changed files coverage 90.0 is below the threshold 100.0.",
    "Report 'user-info:  Controller Module Report' overall coverage 93.0 is below the threshold 100.0.",
    "Report 'user-info: Implementation Module Report' overall coverage 88.0 is below the threshold 100.0.",
    "Report 'user-info: Implementation Module Report' changed files coverage 88.0 is below the threshold 100.0.",
    "Report 'notification: API Module Report' overall coverage 95.0 is below the threshold 100.0.",
    "Report 'Module Small Report' overall coverage 97.0 is below the threshold 100.0.",
    "Report 'notification: Client HTTP Module Report' overall coverage 90.0 is below the threshold 100.0.",
    "Report 'user-info: API Module Report' overall coverage 95.0 is below the threshold 100.0.",
    "Report 'user-info: Client HTTP Module Report' overall coverage 90.0 is below the threshold 100.0.",
    "Report 'user-info: Client HTTP Module Report' changed files coverage 90.0 is below the threshold 100.0.",
    "Report 'notification: Plugins Module Report' overall coverage 92.0 is below the threshold 100.0."
]

module_minimal_violations = [
    "Module 'context/notification' overall coverage 92.33 is below the threshold 100.0.",
    "Module 'context/user-info' overall coverage 91.5 is below the threshold 100.0.",
    "Module 'context/user-info' changed files coverage 89.0 is below the threshold 100.0.",
    "Module 'module_large' overall coverage 91.33 is below the threshold 100.0.",
    "Module 'module_large' changed files coverage 90.0 is below the threshold 100.0.",
    "Module 'module small' overall coverage 97.0 is below the threshold 100.0.",
]

module_summary_violations = [
    "Module 'context/notification' overall coverage 92.33 is below the threshold 100.0.",
    "Module 'context/user-info' overall coverage 91.5 is below the threshold 100.0.",
    "Module 'context/user-info' changed files coverage 89.0 is below the threshold 100.0.",
    "Module 'module_large' overall coverage 91.33 is below the threshold 100.0.",
    "Module 'module_large' changed files coverage 90.0 is below the threshold 100.0.",
    "Module 'module small' overall coverage 97.0 is below the threshold 100.0.",
    "Report 'Module Large Report' overall coverage 91.33 is below the threshold 100.0.",
    "Report 'Module Large Report' changed files coverage 90.0 is below the threshold 100.0.",
    "Report 'user-info:  Controller Module Report' overall coverage 93.0 is below the threshold 100.0.",
    "Report 'user-info: Implementation Module Report' overall coverage 88.0 is below the threshold 100.0.",
    "Report 'user-info: Implementation Module Report' changed files coverage 88.0 is below the threshold 100.0.",
    "Report 'notification: API Module Report' overall coverage 95.0 is below the threshold 100.0.",
    "Report 'Module Small Report' overall coverage 97.0 is below the threshold 100.0.",
    "Report 'notification: Client HTTP Module Report' overall coverage 90.0 is below the threshold 100.0.",
    "Report 'user-info: API Module Report' overall coverage 95.0 is below the threshold 100.0.",
    "Report 'user-info: Client HTTP Module Report' overall coverage 90.0 is below the threshold 100.0.",
    "Report 'user-info: Client HTTP Module Report' changed files coverage 90.0 is below the threshold 100.0.",
    "Report 'notification: Plugins Module Report' overall coverage 92.0 is below the threshold 100.0."
]

module_detail_violations = [
    "Module 'context/notification' overall coverage 92.33 is below the threshold 100.0.",
    "Module 'context/user-info' overall coverage 91.5 is below the threshold 100.0.",
    "Module 'context/user-info' changed files coverage 89.0 is below the threshold 100.0.",
    "Module 'module_large' overall coverage 91.33 is below the threshold 100.0.",
    "Module 'module_large' changed files coverage 90.0 is below the threshold 100.0.",
    "Module 'module small' overall coverage 97.0 is below the threshold 100.0.",
    "Report 'Module Large Report' overall coverage 91.33 is below the threshold 100.0.",
    "Report 'Module Large Report' changed files coverage 90.0 is below the threshold 100.0.",
    "Report 'user-info:  Controller Module Report' overall coverage 93.0 is below the threshold 100.0.",
    "Report 'user-info: Implementation Module Report' overall coverage 88.0 is below the threshold 100.0.",
    "Report 'user-info: Implementation Module Report' changed files coverage 88.0 is below the threshold 100.0.",
    "Report 'notification: API Module Report' overall coverage 95.0 is below the threshold 100.0.",
    "Report 'Module Small Report' overall coverage 97.0 is below the threshold 100.0.",
    "Report 'notification: Client HTTP Module Report' overall coverage 90.0 is below the threshold 100.0.",
    "Report 'user-info: API Module Report' overall coverage 95.0 is below the threshold 100.0.",
    "Report 'user-info: Client HTTP Module Report' overall coverage 90.0 is below the threshold 100.0.",
    "Report 'user-info: Client HTTP Module Report' changed files coverage 90.0 is below the threshold 100.0.",
    "Report 'notification: Plugins Module Report' overall coverage 92.0 is below the threshold 100.0.",
    "Report 'Module Large Report' changed file 'com/example/module_large/BigClass.java' coverage 90.0 is below the threshold 100.0.",
    "Report 'user-info: Implementation Module Report' changed file 'com/example/user-info/implementation/ImplementationClass.java' coverage 88.0 is below the threshold 100.0.",
    "Report 'user-info: Client HTTP Module Report' changed file 'com/example/user-info/client-http/ClientHttpClass.java' coverage 90.0 is below the threshold 100.0.",
]

# Note: used min 100% coverage for overall and changed files to test the violations
more_source_files_scenarios = [
    ("1", CommentModeEnum.SINGLE, SensitivityEnum.MINIMAL, {}, {}, changed_files, single_minimal_violations),
    ("2", CommentModeEnum.SINGLE, SensitivityEnum.SUMMARY, {}, {}, changed_files, single_summary_violations),
    ("3", CommentModeEnum.SINGLE, SensitivityEnum.DETAIL, {}, {}, changed_files, single_detail_violations),
    ("4", CommentModeEnum.MULTI, SensitivityEnum.MINIMAL, {}, {}, changed_files, multi_minimal_violations),
    ("5", CommentModeEnum.MULTI, SensitivityEnum.SUMMARY, {}, {}, changed_files, multi_minimal_violations),
    ("6", CommentModeEnum.MULTI, SensitivityEnum.DETAIL, {}, {}, changed_files, multi_detail_violations),
    # with modules expecting 100% coverage
    ("101", CommentModeEnum.SINGLE, SensitivityEnum.MINIMAL, modules, modules_thresholds_100_all, changed_files, single_minimal_violations),
    ("102", CommentModeEnum.SINGLE, SensitivityEnum.SUMMARY, modules, modules_thresholds_100_all, changed_files, single_summary_violations_with_modules),
    ("103", CommentModeEnum.SINGLE, SensitivityEnum.DETAIL, modules, modules_thresholds_100_all, changed_files, single_detail_violations_with_modules),
    ("104", CommentModeEnum.MULTI, SensitivityEnum.MINIMAL, modules, modules_thresholds_100_all, changed_files, multi_minimal_violations),
    ("105", CommentModeEnum.MULTI, SensitivityEnum.SUMMARY, modules, modules_thresholds_100_all, changed_files, multi_minimal_violations),
    ("106", CommentModeEnum.MULTI, SensitivityEnum.DETAIL, modules, modules_thresholds_100_all, changed_files, multi_detail_violations),
    ("107", CommentModeEnum.MODULE, SensitivityEnum.MINIMAL, modules, modules_thresholds_100_all, changed_files, module_minimal_violations),
    ("108", CommentModeEnum.MODULE, SensitivityEnum.SUMMARY, modules, modules_thresholds_100_all, changed_files, module_summary_violations),
    ("109", CommentModeEnum.MODULE, SensitivityEnum.DETAIL, modules, modules_thresholds_100_all, changed_files, module_detail_violations),
]
@pytest.mark.parametrize("id, mode, template, modules, modules_thresholds, changed_files, violations", more_source_files_scenarios)
def test_violations(jacoco_report, id, mode, template, modules, modules_thresholds, changed_files, violations, mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_event_name", return_value='pull_request')
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_token", return_value='fake_token')
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_comment_mode", return_value=mode)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_sensitivity", return_value=template)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_paths", return_value=["tests/data/test_project/**/jacoco.xml"])
    # mocker.patch("jacoco_report.action_inputs.ActionInputs.get_paths", return_value=["data/test_project/**/jacoco.xml"])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_min_coverage_overall", return_value=100.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_min_coverage_changed_files", return_value=100.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_min_coverage_per_changed_file", return_value=100.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_modules", return_value=modules)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_modules_thresholds", return_value=modules_thresholds)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_repository", return_value="MoranaApps/jacoco-report")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_skip_unchanged", return_value=False)
    mocker.patch("jacoco_report.utils.github.GitHub.get_pr_number", return_value=35)
    mocker.patch("jacoco_report.utils.github.GitHub.get_pr_changed_files", return_value=changed_files)

    mock_add_comment = mocker.patch('jacoco_report.utils.github.GitHub.add_comment', return_value=None)

    jacoco_report.run()

    # for comment in mock_add_comment.call_args_list:
    #     print(f"\ncomment: \n{comment[0][1]}")

    # print(f"Violations: \n")
    # for violation in jacoco_report.violations:
    #     print(f"{violation}")

    actual_merger_violations = " ".join(jacoco_report.violations)
    assert len(jacoco_report.violations) == len(violations)
    for violation in violations:
        assert violation in actual_merger_violations

def test_filtered_out_all_from_changed_file(jacoco_report, mocker):
    changed_files = [
        'com/example/ExampleClass.java'
    ]

    expected_comments = ["""**Report: Example Report**\n\n| Metric (instruction) | Coverage | Threshold | Status |\n|----------------------|----------|-----------|--------|\n| **Overall**       | 90.0% | 100.0% | ❌ |\n| **Changed Files** | 0.0% | 100.0% | ✅ |\n\n| File Path | Coverage | Threshold | Status |\n|-----------|----------|-----------|--------|\n| [ExampleClass.java](https://github.com/MoranaApps/jacoco-report/pull/35/files#diff-30ac4c908eac65fd143f488145837364d4ee1b2f321154225885e23c8ef80aa7) | 0.0% | 100.0% | ✅ |"""]

    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_event_name", return_value='pull_request')
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_token", return_value='fake_token')
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_comment_mode", return_value=CommentModeEnum.MULTI)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_sensitivity", return_value=SensitivityEnum.DETAIL)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_paths", return_value=["tests/data/module_d/**/jacoco*.xml"])
    # mocker.patch("jacoco_report.action_inputs.ActionInputs.get_paths", return_value=["data/module_d/**/jacoco*.xml"])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_min_coverage_overall", return_value=100.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_min_coverage_changed_files", return_value=100.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_min_coverage_per_changed_file", return_value=100.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_modules", return_value=modules)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_modules_thresholds", return_value=modules_thresholds)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_repository", return_value="MoranaApps/jacoco-report")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_skip_unchanged", return_value=False)
    mocker.patch("jacoco_report.utils.github.GitHub.get_pr_number", return_value=35)
    mocker.patch("jacoco_report.utils.github.GitHub.get_pr_changed_files", return_value=changed_files)

    mock_add_comment = mocker.patch('jacoco_report.utils.github.GitHub.add_comment', return_value=None)

    jacoco_report.run()

    assert mock_add_comment.call_count == len(expected_comments)

    if len(expected_comments):
        mock_add_comment.assert_called_once_with(35, expected_comments[0])
