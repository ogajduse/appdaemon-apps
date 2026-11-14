"""Tests for the Bird Buddy processor module (ha-birdbuddy >= 0.1.0 payload)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from apps import bb_processor
from apps.bb_processor import NewPostcardEvent, ReportFormatter

DATA = Path(__file__).parent.parent / 'data' / 'new_postcard_event.yml'


def event(**overrides: Any) -> dict[str, Any]:  # noqa: ANN401
    """Return a payload shaped like the integration's ``birdbuddy_new_postcard``."""
    data: dict[str, Any] = {
        'postcard_id': 'FeedItemNewPostcard:1234',
        'feeder_id': 'feeder-1',
        'species': [
            {'__typename': 'Species', 'id': 's-1', 'name': 'Great Tit'},
        ],
        'media': {
            '__typename': 'MediaImage',
            'id': 'm-1',
            'createdAt': '2026-11-14T08:00:00.000Z',
            'thumbnailUrl': 'https://example.com/thumb.jpg',
            'contentUrl': 'https://example.com/full.jpg',
        },
    }
    data.update(overrides)
    return data


@pytest.fixture(autouse=True)
def no_wikipedia() -> MagicMock:
    """Never hit the network; pretend Wikipedia knows every bird."""
    page = MagicMock(url='https://en.wikipedia.org/wiki/Bird', title='Bird')
    with (
        patch.object(bb_processor.wikipedia, 'search', return_value=['Bird']),
        patch.object(bb_processor.wikipedia, 'page', return_value=page) as m,
    ):
        yield m


def block_types(blocks: list[dict]) -> list[str]:
    """Return the block types in order."""
    return [b['type'] for b in blocks]


def test_single_species_report_and_blocks() -> None:
    """One species: header, divider, name, wiki link, image."""
    fmt = ReportFormatter(NewPostcardEvent.model_validate(event()))
    assert fmt.report.species == ['Great Tit']
    assert fmt.report.image_url == 'https://example.com/full.jpg'
    assert fmt.title == 'New bird sighting: Great Tit!'
    blocks = fmt.format_slack_message()
    assert block_types(blocks) == ['header', 'divider', 'context', 'section', 'image']
    assert blocks[-1]['image_url'] == 'https://example.com/full.jpg'


def test_multiple_species_title() -> None:
    """Two species are both named in the title and get their own blocks."""
    species = [
        {'id': 's-1', 'name': 'Great Tit'},
        {'id': 's-2', 'name': 'Eurasian Blue Tit'},
    ]
    fmt = ReportFormatter(NewPostcardEvent.model_validate(event(species=species)))
    assert fmt.title == 'New bird sighting! 2 birds: Great Tit, Eurasian Blue Tit'
    assert block_types(fmt.format_slack_message()).count('context') == len(species)


def test_no_species_still_posts_image() -> None:
    """Unrecognized visitor: generic title, image kept."""
    fmt = ReportFormatter(NewPostcardEvent.model_validate(event(species=[])))
    assert fmt.title == 'New visitor at the feeder!'
    assert block_types(fmt.format_slack_message()) == ['header', 'divider', 'image']


def test_thumbnail_used_without_content_url() -> None:
    """Media without contentUrl falls back to the thumbnail."""
    media = event()['media']
    del media['contentUrl']
    fmt = ReportFormatter(NewPostcardEvent.model_validate(event(media=media)))
    assert fmt.report.image_url == 'https://example.com/thumb.jpg'


def test_no_media_no_image_block() -> None:
    """media=null and feeder_id=null are accepted."""
    fmt = ReportFormatter(
        NewPostcardEvent.model_validate(event(media=None, feeder_id=None))
    )
    assert fmt.report.image_url is None
    assert 'image' not in block_types(fmt.format_slack_message())


def test_wikipedia_failure_does_not_break(no_wikipedia: MagicMock) -> None:
    """A Wikipedia error drops the link block only."""
    no_wikipedia.side_effect = RuntimeError('disambiguation')
    fmt = ReportFormatter(NewPostcardEvent.model_validate(event()))
    assert block_types(fmt.format_slack_message()) == [
        'header',
        'divider',
        'context',
        'image',
    ]


def test_sample_data_file_parses() -> None:
    """The documented sample payload parses."""
    fmt = ReportFormatter.from_yaml(str(DATA))
    assert fmt.report.species
    assert fmt.format_slack_message()


def test_processor_fires_report_event() -> None:
    """The app re-emits the Slack report under the unchanged event name."""
    app = bb_processor.BirdBuddyEventProcessor.__new__(
        bb_processor.BirdBuddyEventProcessor
    )
    app.log = MagicMock()
    app.fire_event = MagicMock()
    app.process_event('birdbuddy_new_postcard', event(), {})
    name, kwargs = app.fire_event.call_args.args[0], app.fire_event.call_args.kwargs
    assert name == 'birdbuddy_new_postcard_sighting_report'
    assert kwargs['report']['species'] == ['Great Tit']
    assert kwargs['title'] == 'New bird sighting: Great Tit!'
    assert kwargs['slack_message'][0]['type'] == 'header'
