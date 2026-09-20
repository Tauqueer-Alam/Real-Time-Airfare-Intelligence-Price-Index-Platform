"""Tests for the non-genuine airline filtering logic."""
from app.collectors.flightapi_airfare_collector import itineraries_to_price_events
from app.filters import NON_GENUINE_AIRLINES, filter_genuine_airlines, is_genuine_airline


class TestIsGenuineAirline:
    def test_genuine_airline_returns_true(self):
        assert is_genuine_airline("IndiGo") is True
        assert is_genuine_airline("Air India") is True
        assert is_genuine_airline("Akasa Air") is True
        assert is_genuine_airline("Vistara") is True

    def test_duffel_airways_returns_false(self):
        assert is_genuine_airline("Duffel Airways") is False
        assert is_genuine_airline("duffel airways") is False
        assert is_genuine_airline("DUFFEL AIRWAYS") is False

    def test_duffel_airways_with_code_returns_false(self):
        # The collector formats airline as "Name (CODE)"
        assert is_genuine_airline("Duffel Airways (DUFFEL)") is False

    def test_none_and_empty_return_false(self):
        assert is_genuine_airline(None) is False
        assert is_genuine_airline("") is False

    def test_non_genuine_list_contains_duffel_airways(self):
        assert "duffel airways" in NON_GENUINE_AIRLINES


class TestFilterGenuineAirlines:
    def test_filters_out_duffel_airways(self):
        airlines = ["IndiGo", "Duffel Airways", "Air India", "duffel airways"]
        result = filter_genuine_airlines(airlines)
        assert result == ["IndiGo", "Air India"]

    def test_keeps_all_genuine(self):
        airlines = ["IndiGo", "Air India", "Akasa Air"]
        result = filter_genuine_airlines(airlines)
        assert result == airlines

    def test_empty_list(self):
        assert filter_genuine_airlines([]) == []


# Shared test fixtures in FlightAPI.io response format
_TEST_CARRIERS = [
    {
        "id": -31896,
        "name": "Duffel Airways",
        "alt_id": "DUFFEL",
        "display_code": "DUFFEL",
        "display_code_type": "IATA",
    },
    {
        "id": -32213,
        "name": "IndiGo",
        "alt_id": "6E",
        "display_code": "6E",
        "display_code_type": "IATA",
    },
]

_TEST_SEGMENTS = [
    {
        "id": "10957-12703-2609201125-2605201425--31896",
        "origin_place_id": 10957,
        "destination_place_id": 12703,
        "arrival": "2026-09-20T14:25:00",
        "departure": "2026-09-20T11:25:00",
        "duration": 330,
        "marketing_flight_number": "757",
        "marketing_carrier_id": -31896,
        "operating_carrier_id": -31896,
        "transport_mode": "TRANSPORT_MODE_FLIGHT",
    },
    {
        "id": "10957-12703-2609202005-2605202305--32213",
        "origin_place_id": 10957,
        "destination_place_id": 12703,
        "arrival": "2026-09-20T16:00:00",
        "departure": "2026-09-20T14:00:00",
        "duration": 120,
        "marketing_flight_number": "234",
        "marketing_carrier_id": -32213,
        "operating_carrier_id": -32213,
        "transport_mode": "TRANSPORT_MODE_FLIGHT",
    },
]

_TEST_PLACES = [
    {"id": 10957, "alt_id": "DEL", "display_code": "DEL", "name": "New Delhi", "type": "Airport"},
    {"id": 10002, "alt_id": "BLR", "display_code": "BLR", "name": "Bengaluru", "type": "Airport"},
]


class TestCollectorFiltersDuffelAirways:
    def test_itineraries_to_price_events_skips_duffel_airways(self):
        """Itineraries whose carrier is 'Duffel Airways' must be skipped."""
        itineraries = [
            {
                "id": "10957-2609201125--31896-2-10002-2609210735",
                "itinerary_token": "token1",
                "leg_ids": ["10957-2609201125--31896-2-10002-2609210735"],
                "pricing_options": [
                    {
                        "id": "opt1",
                        "agent_ids": ["saud"],
                        "price": {"amount": 88161, "update_status": "current"},
                        "items": [
                            {
                                "agent_id": "saud",
                                "url": "/transport_deeplink/...",
                                "segment_ids": [
                                    "10957-12703-2609201125-2605201425--31896"
                                ],
                                "price": {"amount": 88161},
                                "fares": [],
                                "marketing_carrier_ids": [-31896],
                            }
                        ],
                        "transfer_type": "MANAGED",
                        "score": 0.15431,
                    }
                ],
                "cheapest_price": {"amount": 88161},
                "pricing_options_count": 1,
                "has_linked_pricing_options": False,
            },
            {
                "id": "10957-2609202005--32213-1-10002-2609211000",
                "itinerary_token": "token2",
                "leg_ids": ["10957-2609202005--32213-1-10002-2609211000"],
                "pricing_options": [
                    {
                        "id": "opt2",
                        "agent_ids": ["saud"],
                        "price": {"amount": 52451, "update_status": "current"},
                        "items": [
                            {
                                "agent_id": "saud",
                                "url": "/transport_deeplink/...",
                                "segment_ids": [
                                    "10957-12703-2609202005-2605202305--32213"
                                ],
                                "price": {"amount": 52451},
                                "fares": [],
                                "marketing_carrier_ids": [-32213],
                            }
                        ],
                        "transfer_type": "MANAGED",
                        "score": 0.3759,
                    }
                ],
                "cheapest_price": {"amount": 52451},
                "pricing_options_count": 1,
                "has_linked_pricing_options": False,
            },
        ]

        events = itineraries_to_price_events(
            itineraries, "DEL", "BLR",
            carriers=_TEST_CARRIERS,
            segments=_TEST_SEGMENTS,
            places=_TEST_PLACES,
        )

        # Only the genuine IndiGo offer should survive
        assert len(events) == 1
        assert events[0].airline == "IndiGo (6E)"
        assert events[0].flight_number == "6E 234"
        assert events[0].price == 52451
        assert events[0].currency == "INR"
        assert events[0].data_source == "flightapi"

    def test_itineraries_to_price_events_all_duffel_returns_empty(self):
        itineraries = [
            {
                "id": "10957-2609201125--31896-2-10002-2609210735",
                "itinerary_token": "token1",
                "leg_ids": ["10957-2609201125--31896-2-10002-2609210735"],
                "pricing_options": [
                    {
                        "id": "opt1",
                        "agent_ids": ["saud"],
                        "price": {"amount": 88161, "update_status": "current"},
                        "items": [
                            {
                                "agent_id": "saud",
                                "url": "/transport_deeplink/...",
                                "segment_ids": [
                                    "10957-12703-2609201125-2605201425--31896"
                                ],
                                "price": {"amount": 88161},
                                "fares": [],
                                "marketing_carrier_ids": [-31896],
                            }
                        ],
                        "transfer_type": "MANAGED",
                        "score": 0.15431,
                    }
                ],
                "cheapest_price": {"amount": 88161},
                "pricing_options_count": 1,
                "has_linked_pricing_options": False,
            },
        ]

        events = itineraries_to_price_events(
            itineraries, "DEL", "BLR",
            carriers=_TEST_CARRIERS,
            segments=_TEST_SEGMENTS,
            places=_TEST_PLACES,
        )
        assert events == []
