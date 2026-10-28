# Assumptions

Churn probabilities, used only for expected revenue at risk:

- Promoter 3% a year
- Passive 10% a year
- Detractor 25% a year

These are planning assumptions, not measured attrition. They can be changed with `NPS_CHURN_PROMOTER`, `NPS_CHURN_PASSIVE`, and `NPS_CHURN_DETRACTOR`.

Revenue exposed is the sum of annual revenue on responses that have a revenue value. Expected revenue at risk multiplies each of those amounts by the probability for that response’s NPS group. Rows with missing revenue are counted and left out of both sums.

A fix simulation changes a copy of the scores:

- A: selected detractors in the theme become passives (score 7)
- B: those detractors become promoters (score 10)
- C: a chosen proportion of those detractors moves up by a chosen number of points, capped at 10

The simulation is not a forecast. Fixing an issue does not guarantee a new score.

Callback urgency is TODAY when a detractor comment describes moving the relationship, THIS_WEEK for other shortlisted detractors and contradictory scores, and MONITOR otherwise. The shortlist is not every detractor. Priority points are shown separately for sentiment, revenue exposure, expected revenue at risk, and data-quality flags.

Alert thresholds: critical NPS 0, severe decline 20 points, mild decline 5 points. Bootstrap samples default to 1000 and the seed defaults to 42. The minimum sample is 30.

The bank and the survey are fictional. The application does not contact customers or change bank records.
