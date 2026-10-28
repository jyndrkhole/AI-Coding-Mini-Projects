# How the numbers are calculated

NPS uses every valid response. Promoters are 9–10, passives are 7–8, and detractors are 0–6.

NPS = promoter percentage − detractor percentage, on a 0–100 scale. The result is a score from −100 to +100. Empty valid input returns no NPS. Rounding is only for display.

Invalid scores, unparseable dates, and duplicate response ids are excluded and listed. The first copy of a duplicate id is kept. A month that disagrees with the date is flagged; the original month text is kept, and trends use the month on the date. Blank comments stay in the NPS denominator. Missing revenue is not treated as zero.

Monthly series include only months that have responses. The change is this month’s NPS minus the previous month’s NPS.

Uncertainty is a 95% bootstrap percentile interval. Each response is coded +1, 0, or −1, resampled with a configured seed, and the 2.5 and 97.5 percentiles are the bounds. A segment under 30 responses is labelled “LOW SAMPLE — INTERPRET WITH CAUTION” and is not ranked as the best or worst.

Themes use a fixed phrase list. A label outside that list is stored as UNCLEAR. Sentiment is a separate phrase list. “Not happy” is negative even though it contains the letters of “happy”. A positive comment with a score of 0–6, or a negative comment with a score of 9–10, is flagged and the score is left unchanged.

Customer-impact score = detractor count × theme severity / implementation complexity. Expected revenue at risk is not part of that score. Themes under the minimum sample are listed apart from the definitive ranking.

The alert is RED when the latest NPS is below 0 or the drop from the first month to the last is at least 20 points. A smaller drop of at least 5 points is AMBER. Otherwise the alert is GREEN.

The assignment’s July +32 and September −6.5 figures are compared with the calculation and are not written back over it.
