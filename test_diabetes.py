"""Unit tests for the family-history diabetes report."""

import tempfile
import unittest
from pathlib import Path

import diabetes
from diabetes import (
    DIABETES_STATUS_COLUMN,
    EXERCISE_DAYS_COLUMN,
    count_rows,
    format_report,
    has_family_history,
    is_diabetic,
    is_unhealthy,
    lifestyle_score,
    percentage,
    row_is_complete,
)


COLUMN_COUNT = DIABETES_STATUS_COLUMN + 1


def survey_row(updates=None):
    """One CSV row wide enough for column 208, with a healthy baseline."""
    row = ["0"] * COLUMN_COUNT
    row[90] = "No"
    row[91] = "No"
    row[92] = "No"
    row[93] = "No"
    row[EXERCISE_DAYS_COLUMN] = "5"
    row[108] = "8000"
    row[114] = "2000"
    row[118] = "20"
    row[125] = "Sometimes"
    row[DIABETES_STATUS_COLUMN] = "No Diabetes"
    if updates is not None:
        for index in updates:
            row[index] = updates[index]
    return row


def write_survey(rows):
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".csv",
        delete=False,
        encoding="utf-8",
    )
    header = ",".join("col" + str(index) for index in range(COLUMN_COUNT))
    lines = [header]
    for row in rows:
        lines.append(",".join(row))
    handle.write("\n".join(lines) + "\n")
    handle.close()
    return handle.name


class LifestyleScoreTests(unittest.TestCase):
    def test_healthy_baseline_scores_zero(self):
        self.assertEqual(lifestyle_score(5, 8000, 2000, 20, "Sometimes"), 0)
        self.assertFalse(is_unhealthy(5, 8000, 2000, 20, "Sometimes"))

    def test_each_factor_adds_one_point(self):
        cases = [
            (1, 8000, 2000, 20, "Sometimes"),
            (5, 4999, 2000, 20, "Sometimes"),
            (5, 8000, 2750.1, 20, "Sometimes"),
            (5, 8000, 2000, 50.1, "Sometimes"),
            (5, 8000, 2000, 20, "Often"),
            (5, 8000, 2000, 20, "Never"),
        ]
        for exercise, steps, calories, sugar, food in cases:
            with self.subTest(food=food, exercise=exercise, steps=steps):
                self.assertEqual(
                    lifestyle_score(exercise, steps, calories, sugar, food),
                    1,
                )

    def test_boundaries_that_stay_healthy(self):
        cases = [
            (2, 8000, 2000, 20, "Sometimes"),
            (5, 5000, 2000, 20, "Sometimes"),
            (5, 8000, 2750, 20, "Sometimes"),
            (5, 8000, 2000, 50, "Sometimes"),
            (5, 8000, 2000, 20, "Rarely"),
            (5, 8000, 2000, 20, "Sometimes"),
        ]
        for exercise, steps, calories, sugar, food in cases:
            with self.subTest(food=food, exercise=exercise, steps=steps):
                self.assertEqual(
                    lifestyle_score(exercise, steps, calories, sugar, food),
                    0,
                )

    def test_three_points_is_unhealthy_and_two_is_not(self):
        self.assertEqual(lifestyle_score(0, 1000, 2000, 20, "Sometimes"), 2)
        self.assertFalse(is_unhealthy(0, 1000, 2000, 20, "Sometimes"))
        self.assertEqual(lifestyle_score(0, 1000, 3000, 20, "Sometimes"), 3)
        self.assertTrue(is_unhealthy(0, 1000, 3000, 20, "Sometimes"))


class FamilyHistoryTests(unittest.TestCase):
    def test_any_yes_relative_counts(self):
        self.assertTrue(has_family_history(["No", "No", "Yes", "No"]))
        self.assertFalse(has_family_history(["No", "No", "No", "No"]))
        self.assertFalse(has_family_history(["yes", "No", "No", "No"]))

    def test_only_no_diabetes_is_non_diabetic(self):
        self.assertFalse(is_diabetic("No Diabetes"))
        self.assertTrue(is_diabetic("Type 2 Diabetes"))
        self.assertTrue(is_diabetic("Prediabetes"))

    def test_people_without_family_history_are_ignored(self):
        rows = [
            survey_row({208: "Type 2 Diabetes"}),
            survey_row({90: "Yes"}),
        ]
        counts = count_rows(rows)
        self.assertEqual(counts[0], 1)
        self.assertEqual(counts[1], 0)
        self.assertEqual(counts[2], 1)
        self.assertEqual(counts[4], 0)

    def test_splits_diabetic_relatives_by_lifestyle(self):
        healthy_diabetic = survey_row({90: "Yes", 208: "Type 2 Diabetes"})
        unhealthy = survey_row({
            91: "Yes",
            105: "0",
            108: "1000",
            118: "80",
            208: "Type 2 Diabetes",
        })
        healthy_clear = survey_row({93: "Yes"})
        counts = count_rows([healthy_diabetic, unhealthy, healthy_clear])
        self.assertEqual(counts[0], 3)
        self.assertEqual(counts[1], 2)
        self.assertEqual(counts[2], 2)
        self.assertEqual(counts[3], 1)
        self.assertEqual(counts[4], 1)
        self.assertEqual(counts[5], 1)


class ReportTests(unittest.TestCase):
    def test_percentage_is_zero_when_the_group_is_empty(self):
        self.assertEqual(percentage(0, 0), 0.0)
        self.assertEqual(percentage(1, 2), 50.0)

    def test_empty_family_history(self):
        self.assertEqual(format_report([0, 0, 0, 0, 0, 0]), diabetes.NO_FAMILY_HISTORY_MESSAGE)

    def test_report_matches_the_documented_example(self):
        expected = (
            "If a person has at least one diabetic relative, "
            "they have a 50.0% chance of being diabetic."
            "Among people with diabetic relatives and a healthy lifestyle, "
            "0.0% were diabetic. "
            "Among people with diabetic relatives and an unhealthy lifestyle, "
            "100.0% were diabetic. "
            "This suggests that lifestyle choices significantly affect the "
            "likelihood of diabetes even when family history is present."
        )
        self.assertEqual(format_report([2, 1, 1, 0, 1, 1]), expected)

    def test_rates_round_to_two_decimals(self):
        report = format_report([3, 1, 3, 1, 0, 0])
        self.assertIn("33.33% chance of being diabetic.", report)
        self.assertIn("33.33% were diabetic. Among people", report)
        self.assertIn("an unhealthy lifestyle, 0.0% were diabetic.", report)


class SurveyFileTests(unittest.TestCase):
    def test_skips_header_and_incomplete_rows(self):
        missing = survey_row()
        missing[90] = "<null>"
        blank = survey_row()
        blank[208] = ""
        kept = survey_row({90: "Yes", 208: "Type 2 Diabetes"})
        path = write_survey([kept, missing, blank])
        self.addCleanup(Path(path).unlink)

        rows = diabetes.read_rows(path)
        self.assertEqual(len(rows), 3)
        self.assertFalse(row_is_complete(missing))
        self.assertFalse(row_is_complete(blank))
        counts = count_rows(rows)
        self.assertEqual(counts[0], 1)
        self.assertEqual(counts[1], 1)

    def test_diabetes_report_for_a_small_file(self):
        healthy = survey_row({90: "Yes", 208: "No Diabetes"})
        unhealthy = survey_row({
            93: "Yes",
            105: "0",
            108: "1000",
            114: "3000",
            118: "80",
            125: "Often",
            208: "Type 2 Diabetes",
        })
        ignored = survey_row({208: "Type 2 Diabetes"})
        path = write_survey([healthy, unhealthy, ignored])
        self.addCleanup(Path(path).unlink)
        report = diabetes.diabetes(path)
        self.assertIn("50.0% chance of being diabetic.", report)
        self.assertIn("healthy lifestyle, 0.0% were diabetic.", report)
        self.assertIn("unhealthy lifestyle, 100.0% were diabetic.", report)

    def test_no_family_history_in_the_file(self):
        path = write_survey([survey_row()])
        self.addCleanup(Path(path).unlink)
        self.assertEqual(diabetes.diabetes(path), diabetes.NO_FAMILY_HISTORY_MESSAGE)


if __name__ == "__main__":
    unittest.main()
