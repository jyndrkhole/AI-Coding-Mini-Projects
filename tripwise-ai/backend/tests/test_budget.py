from app.services.budget import calculate_stay_share, calculate_trip_cost


def test_goa_lesson_total():
    stay = calculate_stay_share(3000, 3, 4)
    assert stay["rooms_needed"] == 2
    assert stay["stay_share"] == 4500
    cost = calculate_trip_cost(2800, stay["stay_share"], 1500, 3)
    assert cost["cost_per_person"] == 11800


def test_manali_three_friends_still_need_two_rooms():
    stay = calculate_stay_share(2500, 4, 3)
    assert stay["rooms_needed"] == 2
    assert stay["stay_share"] == 6666.67
    cost = calculate_trip_cost(9000, stay["stay_share"], 1300, 4)
    assert cost["cost_per_person"] == 20866.67


def test_similarity_filter_drops_weak_matches():
    from app.ai.retriever import filter_hits

    kept = filter_hits(
        ["a", "b"],
        ["close", "far"],
        [{}, {}],
        [0.1, 0.9],
        0.28,
    )
    assert [item["id"] for item in kept] == ["a"]
    assert kept[0]["similarity"] == 0.9
