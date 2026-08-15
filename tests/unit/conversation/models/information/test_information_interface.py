"""Tests for information-extractor interfaces and deterministic doubles."""

from conversation.entities.message import Message
from conversation.models.information.interface import (
    DummyInformationExtractor,
    InformationExtractorInterface,
)


def test_information_extractor_interface_is_abstract() -> None:
    try:
        InformationExtractorInterface()
    except TypeError:
        pass
    else:
        raise AssertionError("InformationExtractorInterface must remain abstract")




def test_dummy_extractor_ignores_plain_confirmation() -> None:
    assert DummyInformationExtractor().extract(Message("yes", original_content="yes")) == []
