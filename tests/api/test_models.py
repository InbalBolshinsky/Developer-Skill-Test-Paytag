from paytag_client.api.models import Item


def test_from_dict_builds_item_from_known_fields():
    item = Item.from_dict({
        "Barcode": "7290000000001",
        "RFID": "E200001B0000000000000001",
        "IsHardTag": False,
    })

    assert item == Item(
        barcode="7290000000001",
        rfid="E200001B0000000000000001",
        is_hard_tag=False,
    )


def test_from_dict_ignores_unexpected_extra_fields():
    item = Item.from_dict({
        "Barcode": "7290000000001",
        "RFID": "E200001B0000000000000001",
        "IsHardTag": True,
        "SomeFutureField": "a field a firmware update might add later",
        "AnotherOne": 42,
    })

    assert item == Item(
        barcode="7290000000001",
        rfid="E200001B0000000000000001",
        is_hard_tag=True,
    )
