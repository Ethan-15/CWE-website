RELATIVE_COLUMNS = (90, 91, 92, 93)
EXERCISE_DAYS_COLUMN = 105
DAILY_STEPS_COLUMN = 108
CALORIE_INTAKE_COLUMN = 114
SUGAR_INTAKE_COLUMN = 118
PROCESSED_FOOD_COLUMN = 125
DIABETES_STATUS_COLUMN = 208

NO_FAMILY_HISTORY_MESSAGE = "No valid family-history data was found."


def diabetes(filename="diabetes_large_dataset.csv") -> str:
    """
    Calculate the probability of diabetes given family history,
    and compare how lifestyle affects that probability.

    >>>diabetes()
    'If a person has at least one diabetic relative, they have a 50.0% chance of being diabetic.Among people with diabetic relatives and a healthy lifestyle, 0.0% were diabetic. Among people with diabetic relatives and an unhealthy lifestyle, 100.0% were diabetic. This suggests that lifestyle choices significantly affect the likelihood of diabetes even when family history is present.'
    """
    rows = read_rows(filename)
    counts = count_rows(rows)
    return format_report(counts)


def read_rows(filename):
    """Read the survey and return each data row as a list. The header is skipped."""
    rows = []
    with open(filename, "r") as csv_file:
        csv_file.readline()
        for line in csv_file:
            rows.append(line.strip().split(","))
    return rows


def required_data(row):
    """Return the fields this analysis uses from one row."""
    values = []
    for index in RELATIVE_COLUMNS:
        values.append(row[index])
    values.append(row[EXERCISE_DAYS_COLUMN])
    values.append(row[DAILY_STEPS_COLUMN])
    values.append(row[CALORIE_INTAKE_COLUMN])
    values.append(row[SUGAR_INTAKE_COLUMN])
    values.append(row[PROCESSED_FOOD_COLUMN])
    values.append(row[DIABETES_STATUS_COLUMN])
    return values


def row_is_complete(row):
    """Return False when a required field is blank or '<null>'."""
    data = required_data(row)
    if "<null>" in data or "" in data:
        return False
    return True


def has_family_history(relatives):
    """Return True when at least one relative is marked Yes."""
    if "Yes" in relatives:
        return True
    return False


def is_diabetic(status):
    """Return True unless the status is exactly 'No Diabetes'."""
    if status != "No Diabetes":
        return True
    return False


def lifestyle_score(exercise_days, daily_steps, calorie_intake, sugar_intake, processed_food_frequency):
    """Count unhealthy factors. A score of 3 or more is an unhealthy lifestyle."""
    score = 0

    if exercise_days < 2:
        score += 1

    if daily_steps < 5000:
        score += 1

    if calorie_intake > 2750:
        score += 1

    if sugar_intake > 50:
        score += 1

    if processed_food_frequency == "Never" or processed_food_frequency == "Often":
        score += 1

    return score


def is_unhealthy(exercise_days, daily_steps, calorie_intake, sugar_intake, processed_food_frequency):
    if lifestyle_score(exercise_days, daily_steps, calorie_intake, sugar_intake, processed_food_frequency) >= 3:
        return True
    return False


def empty_counts():
    """The six counters, stored by name."""
    return {
        "family_history_count": 0,
        "diabetic_with_family_history": 0,
        "family_healthy": 0,
        "family_healthy_diabetic": 0,
        "family_unhealthy": 0,
        "family_unhealthy_diabetic": 0,
    }


def count_rows(rows):
    """Count family-history cases, split by lifestyle.

    Returns a dictionary of the six counters.
    """
    counts = empty_counts()

    for row in rows:
        if not row_is_complete(row):
            continue

        relatives = (
            row[RELATIVE_COLUMNS[0]],
            row[RELATIVE_COLUMNS[1]],
            row[RELATIVE_COLUMNS[2]],
            row[RELATIVE_COLUMNS[3]],
        )
        status = row[DIABETES_STATUS_COLUMN]
        exercise_days = int(row[EXERCISE_DAYS_COLUMN])
        daily_steps = int(row[DAILY_STEPS_COLUMN])
        calorie_intake = float(row[CALORIE_INTAKE_COLUMN])
        sugar_intake = float(row[SUGAR_INTAKE_COLUMN])
        processed_food_frequency = row[PROCESSED_FOOD_COLUMN]

        if not has_family_history(relatives):
            continue

        counts["family_history_count"] += 1
        diabetic = is_diabetic(status)

        if diabetic:
            counts["diabetic_with_family_history"] += 1

        if is_unhealthy(exercise_days, daily_steps, calorie_intake, sugar_intake, processed_food_frequency):
            counts["family_unhealthy"] += 1
            if diabetic:
                counts["family_unhealthy_diabetic"] += 1
        else:
            counts["family_healthy"] += 1
            if diabetic:
                counts["family_healthy_diabetic"] += 1

    return counts


def percentage(part_and_whole):
    """part_and_whole is a tuple: (part, whole)."""
    part, whole = part_and_whole
    if whole == 0:
        return 0.0
    return (part / whole) * 100


def format_report(counts):
    """Build the sentence report. Matches the original wording, including spacing."""
    if counts["family_history_count"] == 0:
        return NO_FAMILY_HISTORY_MESSAGE

    family_history_percentage = percentage((
        counts["diabetic_with_family_history"],
        counts["family_history_count"],
    ))
    healthy_rate = percentage((
        counts["family_healthy_diabetic"],
        counts["family_healthy"],
    ))
    unhealthy_rate = percentage((
        counts["family_unhealthy_diabetic"],
        counts["family_unhealthy"],
    ))

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
