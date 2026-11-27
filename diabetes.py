"""Family-history diabetes rates, split by lifestyle."""

from dataclasses import dataclass

RELATIVE_COLUMNS = (90, 91, 92, 93)
EXERCISE_DAYS_COLUMN = 105
DAILY_STEPS_COLUMN = 108
CALORIE_INTAKE_COLUMN = 114
SUGAR_INTAKE_COLUMN = 118
PROCESSED_FOOD_COLUMN = 125
DIABETES_STATUS_COLUMN = 208

REQUIRED_COLUMNS = (
    *RELATIVE_COLUMNS,
    EXERCISE_DAYS_COLUMN,
    DAILY_STEPS_COLUMN,
    CALORIE_INTAKE_COLUMN,
    SUGAR_INTAKE_COLUMN,
    PROCESSED_FOOD_COLUMN,
    DIABETES_STATUS_COLUMN,
)

MISSING_VALUES = ("<null>", "")
NO_DIABETES = "No Diabetes"
# Both values add a point. The original check was written as
# `== "Never" or "Often"`, which is always true in Python.
UNHEALTHY_PROCESSED_FOOD = ("Never", "Often")
UNHEALTHY_SCORE_AT_LEAST = 3

NO_FAMILY_HISTORY_MESSAGE = "No valid family-history data was found."


@dataclass(frozen=True)
class PersonRecord:
    relatives_diabetic: tuple[str, str, str, str]
    individually_diabetic: str
    exercise_days: int
    daily_steps: int
    calorie_intake: float
    sugar_intake: float
    processed_food_frequency: str


@dataclass
class FamilyHistoryStats:
    family_history_count: int = 0
    diabetic_with_family_history: int = 0
    family_healthy: int = 0
    family_healthy_diabetic: int = 0
    family_unhealthy: int = 0
    family_unhealthy_diabetic: int = 0


def read_survey_rows(filename: str):
    """Yield each data row, skipping the header line."""
    with open(filename, "r") as csv_file:
        csv_file.readline()
        for line in csv_file:
            yield line.strip().split(",")


def required_values(row: list[str]) -> list[str]:
    return [row[index] for index in REQUIRED_COLUMNS]


def row_has_required_values(row: list[str]) -> bool:
    """Return False when a required field is blank or '<null>'."""
    values = required_values(row)
    return not any(value in MISSING_VALUES for value in values)


def parse_person(row: list[str]) -> PersonRecord:
    """Turn one complete survey row into a person record."""
    return PersonRecord(
        relatives_diabetic=tuple(row[index] for index in RELATIVE_COLUMNS),
        individually_diabetic=row[DIABETES_STATUS_COLUMN],
        exercise_days=int(row[EXERCISE_DAYS_COLUMN]),
        daily_steps=int(row[DAILY_STEPS_COLUMN]),
        calorie_intake=float(row[CALORIE_INTAKE_COLUMN]),
        sugar_intake=float(row[SUGAR_INTAKE_COLUMN]),
        processed_food_frequency=row[PROCESSED_FOOD_COLUMN],
    )


def iter_people(filename: str):
    """Yield people whose required fields are present."""
    for row in read_survey_rows(filename):
        if row_has_required_values(row):
            yield parse_person(row)


def load_people(filename: str) -> list[PersonRecord]:
    """Read the survey and keep rows that have every required field."""
    return list(iter_people(filename))


def has_diabetic_relative(relatives: tuple[str, ...]) -> bool:
    return "Yes" in relatives


def person_is_diabetic(status: str) -> bool:
    return status != NO_DIABETES


def lifestyle_score(person: PersonRecord) -> int:
    """Count unhealthy factors. A score of 3 or more is an unhealthy lifestyle."""
    factors = (
        person.exercise_days < 2,
        person.daily_steps < 5000,
        person.calorie_intake > 2750,
        person.sugar_intake > 50,
        person.processed_food_frequency in UNHEALTHY_PROCESSED_FOOD,
    )
    return sum(1 for factor in factors if factor)


def has_unhealthy_lifestyle(person: PersonRecord) -> bool:
    return lifestyle_score(person) >= UNHEALTHY_SCORE_AT_LEAST


def record_person(stats: FamilyHistoryStats, person: PersonRecord) -> None:
    """Add one person to the family-history tallies. Others are ignored."""
    if not has_diabetic_relative(person.relatives_diabetic):
        return

    stats.family_history_count += 1
    diabetic = person_is_diabetic(person.individually_diabetic)
    if diabetic:
        stats.diabetic_with_family_history += 1

    if has_unhealthy_lifestyle(person):
        stats.family_unhealthy += 1
        if diabetic:
            stats.family_unhealthy_diabetic += 1
    else:
        stats.family_healthy += 1
        if diabetic:
            stats.family_healthy_diabetic += 1


def count_family_history(people: list[PersonRecord]) -> FamilyHistoryStats:
    stats = FamilyHistoryStats()
    for person in people:
        record_person(stats, person)
    return stats


def percentage(part: int, whole: int) -> float:
    if whole == 0:
        return 0.0
    return (part / whole) * 100


def format_report(stats: FamilyHistoryStats) -> str:
    """Build the sentence report. Matches the original wording, including spacing."""
    if stats.family_history_count == 0:
        return NO_FAMILY_HISTORY_MESSAGE

    family_history_percentage = percentage(
        stats.diabetic_with_family_history,
        stats.family_history_count,
    )
    healthy_rate = percentage(stats.family_healthy_diabetic, stats.family_healthy)
    unhealthy_rate = percentage(
        stats.family_unhealthy_diabetic,
        stats.family_unhealthy,
    )
    return (
        f"If a person has at least one diabetic relative, "
        f"they have a {round(family_history_percentage, 2)}% chance of being diabetic."
        f"Among people with diabetic relatives and a healthy lifestyle, "
        f"{round(healthy_rate, 2)}% were diabetic. "
        f"Among people with diabetic relatives and an unhealthy lifestyle, "
        f"{round(unhealthy_rate, 2)}% were diabetic. "
        f"This suggests that lifestyle choices significantly affect the "
        f"likelihood of diabetes even when family history is present."
    )


def diabetes(filename: str = "diabetes_large_dataset.csv") -> str:
    """
    Calculate the probability of diabetes given family history,
    and compare how lifestyle affects that probability.

    >>>diabetes()
    'If a person has at least one diabetic relative, they have a 50.0% chance of being diabetic.Among people with diabetic relatives and a healthy lifestyle, 0.0% were diabetic. Among people with diabetic relatives and an unhealthy lifestyle, 100.0% were diabetic. This suggests that lifestyle choices significantly affect the likelihood of diabetes even when family history is present.'
    """
    stats = FamilyHistoryStats()
    for person in iter_people(filename):
        record_person(stats, person)
    return format_report(stats)
