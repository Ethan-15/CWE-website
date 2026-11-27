"""Unit tests for the family-history diabetes report."""

import tempfile
import unittest
from pathlib import Path

import diabetes
from diabetes import (
    DIABETES_STATUS_COLUMN,
    EXERCISE_DAYS_COLUMN,
    FamilyHistoryStats,
    PersonRecord,
    count_family_history,
    format_report,
    has_diabetic_relative,
    has_unhealthy_lifestyle,
    lifestyle_score,
    load_people,
    parse_person,
    percentage,
    person_is_diabetic,
    row_has_required_values,
)


COLUMN_COUNT = DIABETES_STATUS_COLUMN + 1


def healthy_person(**overrides) -> PersonRecord:
    values = dict(
        relatives_diabetic=("No", "No", "No", "No"),
        individually_diabetic="No Diabetes",
        exercise_days=5,
        daily_steps=8000,
        calorie_intake=2000.0,
        sugar_intake=20.0,
        processed_food_frequency="Sometimes",
    )
    values.update(overrides)
    return PersonRecord(**values)


def survey_row(updates: dict[int, str] | None = None) -> list[str]:
    """One CSV row wide enough for column 208, with a healthy baseline."""
    row = ["0"] * COLUMN_COUNT
    row[90] = row[91] = row[92] = row[93] = "No"
    row[EXERCISE_DAYS_COLUMN] = "5"
    row[108] = "8000"
    row[114] = "2000"
    row[118] = "20"
    row[125] = "Sometimes"
    row[DIABETES_STATUS_COLUMN] = "No Diabetes"
    for index, value in (updates or {}).items():
        row[index] = value
    return row


def write_survey(rows: list[list[str]]) -> str:
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".csv",
        delete=False,
        encoding="utf-8",
    )
    header = ",".join(f"col{index}" for index in range(COLUMN_COUNT))
    lines = [header]
    lines.extend(",".join(row) for row in rows)
    handle.write("\n".join(lines) + "\n")
    handle.close()
    return handle.name


class LifestyleScoreTests(unittest.TestCase):
    def test_healthy_baseline_scores_zero(self):
        self.assertEqual(lifestyle_score(healthy_person()), 0)
        self.assertFalse(has_unhealthy_lifestyle(healthy_person()))

    def test_each_factor_adds_one_point(self):
        cases = [
            dict(exercise_days=1),
            dict(daily_steps=4999),
            dict(calorie_intake=2750.1),
            dict(sugar_intake=50.1),
            dict(processed_food_frequency="Often"),
            dict(processed_food_frequency="Never"),
        ]
        for overrides in cases:
            with self.subTest(overrides=overrides):
                self.assertEqual(lifestyle_score(healthy_person(**overrides)), 1)

    def test_boundaries_that_stay_healthy(self):
        cases = [
            dict(exercise_days=2),
            dict(daily_steps=5000),
            dict(calorie_intake=2750.0),
            dict(sugar_intake=50.0),
            dict(processed_food_frequency="Rarely"),
            dict(processed_food_frequency="Sometimes"),
        ]
        for overrides in cases:
            with self.subTest(overrides=overrides):
                self.assertEqual(lifestyle_score(healthy_person(**overrides)), 0)

    def test_three_points_is_unhealthy_and_two_is_not(self):
        two_points = healthy_person(exercise_days=0, daily_steps=1000)
        three_points = healthy_person(
            exercise_days=0,
            daily_steps=1000,
            calorie_intake=3000,
        )
        self.assertEqual(lifestyle_score(two_points), 2)
        self.assertFalse(has_unhealthy_lifestyle(two_points))
        self.assertEqual(lifestyle_score(three_points), 3)
        self.assertTrue(has_unhealthy_lifestyle(three_points))


class FamilyHistoryTests(unittest.TestCase):
    def test_any_yes_relative_counts(self):
        self.assertTrue(has_diabetic_relative(("No", "No", "Yes", "No")))
        self.assertFalse(has_diabetic_relative(("No", "No", "No", "No")))
        self.assertFalse(has_diabetic_relative(("yes", "No", "No", "No")))

    def test_only_no_diabetes_is_non_diabetic(self):
        self.assertFalse(person_is_diabetic("No Diabetes"))
        self.assertTrue(person_is_diabetic("Type 2 Diabetes"))
        self.assertTrue(person_is_diabetic("Prediabetes"))

    def test_people_without_family_history_are_ignored(self):
        people = [
            healthy_person(individually_diabetic="Type 2 Diabetes"),
            healthy_person(relatives_diabetic=("Yes", "No", "No", "No")),
        ]
        stats = count_family_history(people)
        self.assertEqual(stats.family_history_count, 1)
        self.assertEqual(stats.diabetic_with_family_history, 0)
        self.assertEqual(stats.family_healthy, 1)
        self.assertEqual(stats.family_unhealthy, 0)

    def test_splits_diabetic_relatives_by_lifestyle(self):
        healthy_diabetic = healthy_person(
            relatives_diabetic=("Yes", "No", "No", "No"),
            individually_diabetic="Type 2 Diabetes",
        )
        unhealthy = healthy_person(
            relatives_diabetic=("No", "Yes", "No", "No"),
            individually_diabetic="Type 2 Diabetes",
            exercise_days=0,
            daily_steps=1000,
            sugar_intake=80,
        )
        healthy_clear = healthy_person(
            relatives_diabetic=("No", "No", "No", "Yes"),
        )
        stats = count_family_history([healthy_diabetic, unhealthy, healthy_clear])
        self.assertEqual(stats.family_history_count, 3)
        self.assertEqual(stats.diabetic_with_family_history, 2)
        self.assertEqual(stats.family_healthy, 2)
        self.assertEqual(stats.family_healthy_diabetic, 1)
        self.assertEqual(stats.family_unhealthy, 1)
        self.assertEqual(stats.family_unhealthy_diabetic, 1)


class ReportTests(unittest.TestCase):
    def test_percentage_is_zero_when_the_group_is_empty(self):
        self.assertEqual(percentage(0, 0), 0.0)
        self.assertEqual(percentage(1, 2), 50.0)

    def test_empty_family_history(self):
        self.assertEqual(
            format_report(FamilyHistoryStats()),
            diabetes.NO_FAMILY_HISTORY_MESSAGE,
        )

    def test_report_matches_the_documented_example(self):
        stats = FamilyHistoryStats(
            family_history_count=2,
            diabetic_with_family_history=1,
            family_healthy=1,
            family_healthy_diabetic=0,
            family_unhealthy=1,
            family_unhealthy_diabetic=1,
        )
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
        self.assertEqual(format_report(stats), expected)

    def test_rates_round_to_two_decimals(self):
        stats = FamilyHistoryStats(
            family_history_count=3,
            diabetic_with_family_history=1,
            family_healthy=3,
            family_healthy_diabetic=1,
            family_unhealthy=0,
            family_unhealthy_diabetic=0,
        )
        report = format_report(stats)
        self.assertIn("33.33% chance of being diabetic.", report)
        self.assertIn("33.33% were diabetic. Among people", report)
        self.assertIn("an unhealthy lifestyle, 0.0% were diabetic.", report)


class SurveyFileTests(unittest.TestCase):
    def test_skips_header_and_incomplete_rows(self):
        missing = survey_row()
        missing[90] = "<null>"
        blank = survey_row()
        blank[208] = ""
        path = write_survey(
            [
                survey_row({90: "Yes", 208: "Type 2 Diabetes"}),
                missing,
                blank,
            ]
        )
        self.addCleanup(Path(path).unlink)
        people = load_people(path)
        self.assertEqual(len(people), 1)
        self.assertEqual(people[0].relatives_diabetic[0], "Yes")
        self.assertEqual(people[0].individually_diabetic, "Type 2 Diabetes")
        self.assertFalse(row_has_required_values(missing))
        self.assertFalse(row_has_required_values(blank))

    def test_parse_person_reads_the_survey_columns(self):
        row = survey_row(
            {
                90: "Yes",
                91: "No",
                92: "No",
                93: "Yes",
                105: "1",
                108: "4000",
                114: "3000.5",
                118: "60",
                125: "Often",
                208: "Type 1 Diabetes",
            }
        )
        person = parse_person(row)
        self.assertEqual(person.relatives_diabetic, ("Yes", "No", "No", "Yes"))
        self.assertEqual(person.exercise_days, 1)
        self.assertEqual(person.daily_steps, 4000)
        self.assertEqual(person.calorie_intake, 3000.5)
        self.assertEqual(person.sugar_intake, 60.0)
        self.assertEqual(person.processed_food_frequency, "Often")
        self.assertEqual(person.individually_diabetic, "Type 1 Diabetes")

    def test_diabetes_report_for_a_small_file(self):
        healthy = survey_row({90: "Yes", 208: "No Diabetes"})
        unhealthy = survey_row(
            {
                93: "Yes",
                105: "0",
                108: "1000",
                114: "3000",
                118: "80",
                125: "Often",
                208: "Type 2 Diabetes",
            }
        )
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
        self.assertEqual(
            diabetes.diabetes(path),
            diabetes.NO_FAMILY_HISTORY_MESSAGE,
        )


if __name__ == "__main__":
    unittest.main()
