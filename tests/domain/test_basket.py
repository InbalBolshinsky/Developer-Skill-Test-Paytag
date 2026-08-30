from datetime import datetime

from paytag_client.api.models import Item
from paytag_client.domain.basket import Basket


def test_from_items_keeps_distinct_items():
    items = [
        Item(barcode="7290000000001", rfid="RFID0001", is_hard_tag=False),
        Item(barcode="7290000000002", rfid="RFID0002", is_hard_tag=True),
    ]

    basket = Basket.from_items(items, datetime(2026, 1, 1, 10, 0, 0))

    assert basket.items == items


def test_from_items_dedupes_exact_duplicate_within_one_response():
    # Confirmed live against the simulator: a single GetItems response can contain
    # the exact same item (same barcode AND rfid) listed twice.
    duplicated = Item(barcode="7290000000001", rfid="RFID0001", is_hard_tag=False)
    items = [duplicated, duplicated]

    basket = Basket.from_items(items, datetime(2026, 1, 1, 10, 0, 0))

    assert basket.items == [duplicated]


def test_from_items_keeps_two_items_sharing_a_barcode_with_different_rfids():
    # Two physical units of the same product each carry their own RFID - confirmed
    # live too. Barcode is not a safe identity key; RFID is.
    item_a = Item(barcode="7290000000002", rfid="RFID0002", is_hard_tag=False)
    item_b = Item(barcode="7290000000002", rfid="RFID0012", is_hard_tag=False)

    basket = Basket.from_items([item_a, item_b], datetime(2026, 1, 1, 10, 0, 0))

    assert basket.items == [item_a, item_b]


def test_from_items_marks_a_fresh_basket_not_stale():
    confirmed_at = datetime(2026, 1, 1, 10, 0, 0)

    basket = Basket.from_items([], confirmed_at)

    assert basket.is_stale is False
    assert basket.last_confirmed_at == confirmed_at


def test_mark_stale_flips_the_flag_without_touching_items():
    basket = Basket.from_items([Item("1", "R1", False)], datetime(2026, 1, 1, 10, 0, 0))

    basket.mark_stale()

    assert basket.is_stale is True
    assert len(basket.items) == 1


def test_neutralizable_and_hard_tag_items_split_correctly():
    regular = Item(barcode="1", rfid="R1", is_hard_tag=False)
    hard_tag = Item(barcode="2", rfid="R2", is_hard_tag=True)
    basket = Basket.from_items([regular, hard_tag], datetime(2026, 1, 1, 10, 0, 0))

    assert basket.neutralizable_items() == [regular]
    assert basket.hard_tag_items() == [hard_tag]
