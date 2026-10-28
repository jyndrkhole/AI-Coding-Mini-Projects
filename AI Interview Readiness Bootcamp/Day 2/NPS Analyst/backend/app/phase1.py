"""Print Phase 1 counts and NPS for the configured survey file."""

from app.analytics.nps import calculate_nps, nps_by_month
from app.core.config import survey_path
from app.data.loader import load_survey_csv
from app.data.normalizer import normalize
from app.data.validator import validate_frame


def main() -> None:
    path = survey_path()
    frame = load_survey_csv(path)
    validation = validate_frame(frame)
    responses = normalize(frame, validation)
    overall = calculate_nps(responses)
    print(f"file: {path}")
    print(f"rows: {validation.original_rows}")
    print(f"valid: {len(validation.valid_index)}")
    print(f"invalid: {validation.invalid_rows}")
    print(f"issues: {len(validation.issues)}")
    print(
        "overall NPS: {nps}  promoters {promoters}  passives {passives}  detractors {detractors}  n {total_responses}".format(
            **overall
        )
    )
    for month in nps_by_month(responses):
        print(
            "{month}: NPS {nps:.4f}  n {total_responses}  promoters {promoters}  passives {passives}  detractors {detractors}".format(
                **month
            )
        )


if __name__ == "__main__":
    main()
