"""Canonical travel notebook, plus a few TripWise notes the lesson list does not cover.

Prices are intentionally absent. The MCP database is the source of those numbers.
"""

NOTEBOOK = [
    ("trip-cost", "Trip cost per person = travel + stay share + daily spend x nights.", {"topic": "money", "destination": "", "travel_type": "", "season": ""}),
    ("rooms", "One room fits 2 people, so rooms needed = people / 2, rounded up. Stay share = rooms x room price x nights / people.", {"topic": "money", "destination": "", "travel_type": "", "season": ""}),
    ("buffer", "Keep a 10% buffer on top of the total for surprises like a cab surge or a missed bus.", {"topic": "money", "destination": "", "travel_type": "", "season": ""}),
    ("splitting", "Split shared costs (stay, cabs, fuel) equally. Personal shopping is never split.", {"topic": "money", "destination": "", "travel_type": "", "season": ""}),
    ("beach", "Beach trips (Goa, Gokarna, Pondicherry): best November-February. In the monsoon (June-September) many beach shacks and water sports close.", {"topic": "trip_type", "destination": "", "travel_type": "Beach", "season": ""}),
    ("hills", "Hill trips (Coorg, Ooty, Manali): best March-June and October. Avoid July-August: heavy rain and landslides block hill roads. Carry a jacket even in summer.", {"topic": "trip_type", "destination": "Manali", "travel_type": "Hills", "season": "July"}),
    ("heritage", "Heritage trips (Hampi, Jaipur): best October-March. April-May afternoons cross 40°C, so explore early in the morning.", {"topic": "trip_type", "destination": "", "travel_type": "Heritage", "season": ""}),
    ("adventure", "Adventure trips (Rishikesh, Dandeli): river rafting runs October-June and closes in the monsoon. Use licensed operators and always wear a life jacket.", {"topic": "trip_type", "destination": "", "travel_type": "Adventure", "season": ""}),
    ("book-early", "Book trains and flights 30-60 days early; prices often double in the last week.", {"topic": "travel_tip", "destination": "", "travel_type": "", "season": ""}),
    ("weekdays", "Weekday stays are often 20-30% cheaper than weekends.", {"topic": "travel_tip", "destination": "", "travel_type": "", "season": ""}),
    ("long-weekend", "Long weekends and New Year push Goa prices up sharply; book early or pick Gokarna instead.", {"topic": "travel_tip", "destination": "Goa", "travel_type": "Beach", "season": "December"}),
    ("overnight", "Overnight buses and trains save the cost of one night's stay.", {"topic": "travel_tip", "destination": "", "travel_type": "", "season": ""}),
    ("big-group", "Groups bigger than 6: a villa or homestay is usually cheaper than many hotel rooms.", {"topic": "travel_tip", "destination": "", "travel_type": "", "season": ""}),
    (
        "manali-july",
        "Manali in July: avoid treating the drive as a normal summer trip. Heavy rain and landslides can block hill roads. Skip exposed river crossings, keep a rain jacket and warm layer, and do not assume rafting or paragliding is running. This is stored travel guidance, not a live weather report.",
        {"topic": "safety", "destination": "Manali", "travel_type": "Hills", "season": "July"},
    ),
    (
        "kerala-family",
        "A 5-day Kerala family trip is usually paced as Kochi on arrival, one day for Fort Kochi, a slower day in the hills around Munnar, a backwater day at Alleppey, and departure. December is drier than the June to September monsoon. Ask the database for demonstration prices before saying a budget fits.",
        {"topic": "guide", "destination": "Kerala", "travel_type": "Nature", "season": "December"},
    ),
    (
        "pune-weekends",
        "From Pune, the stored short trips are Lonavala (about 2 hours), Alibaug (about 3 hours), and Mahabaleshwar (about 4 to 5 hours). Goa is an overnight journey, not a 3-day weekend hop. Use the destination records for hours and demonstration fares.",
        {"topic": "guide", "destination": "", "travel_type": "Hills", "season": ""},
    ),
    (
        "quiet-december-hills",
        "December hill notes stored for this project: Ooty weekends are busy around the lake and botanical garden. Coorg is calmer midweek than on a holiday weekend. Mahabaleshwar weekends draw more visitors than midweek. There is no numeric crowd index beyond these notes.",
        {"topic": "crowdedness", "destination": "", "travel_type": "Hills", "season": "December"},
    ),
    (
        "west-coast-couple",
        "For a couple, Goa has the widest beach-and-food choice and is crowded in December. Gokarna is quieter, with cliff paths and fewer stay options. Alibaug is a short beach break from Pune or Mumbai, not a week-long beach holiday. Compare prices only from the database.",
        {"topic": "guide", "destination": "", "travel_type": "Beach", "season": ""},
    ),
]
