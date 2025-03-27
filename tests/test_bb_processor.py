"""Tests for the Bird Buddy processor module."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import jwt
import pytest

from apps.bb_processor import (
    AutomationReport,
    BBEventModel,
    Feeder,
    IdentifiableModel,
    ReportFormatter,
    SightedBird,
    SightingReport,
    Species,
    VideoMedia,
)

# Constants for magic numbers
NUM_BIRDS_SINGLE = 1
NUM_BIRDS_MULTIPLE = 2
NUM_BIRDS_RECOGNIZED_UNRECOGNIZED = 2
MIN_BLOCKS_EXPECTED = 3


# Create a sample event dictionary with minimal required fields.
@pytest.fixture
def sample_event() -> dict[str, Any]:
    """Create a sample Bird Buddy event with a single bird sighting.

    Returns
    -------
        Dictionary containing a properly structured Bird Buddy event

    """
    # Generate valid UUID4 values for testing
    postcard_id = str(uuid4())
    feeder_id = str(uuid4())
    media1_id = str(uuid4())
    media2_id = str(uuid4())
    sighting_id = str(uuid4())
    species_id = str(uuid4())
    video_id = str(uuid4())

    # Create a JWT token with a dummy payload.
    token = jwt.encode(
        {'reportToken': '{"dummy": "value"}'}, key='secret', algorithm='HS256'
    )
    return {
        'postcard': {'id': postcard_id, 'createdAt': '2024-04-06T08:08:38.055Z'},
        'sighting': {
            'feeder': {'id': feeder_id, 'name': 'Test Feeder', 'state': 'READY'},
            'medias': [
                {
                    'id': media1_id,
                    'createdAt': '2024-04-06T08:08:36.208Z',
                    'thumbnailUrl': 'http://example.com/thumb1.jpg',
                    'contentUrl': 'http://example.com/content1.jpg',
                },
                {
                    'id': media2_id,
                    'createdAt': '2024-04-06T08:08:36.208Z',
                    'thumbnailUrl': 'http://example.com/thumb2.jpg',
                    'contentUrl': 'http://example.com/content2.jpg',
                },
            ],
            'sightingReport': {
                'reportToken': token,
                'sightings': [
                    {
                        'id': sighting_id,
                        'matchTokens': [media1_id],
                        'color': 'YELLOW',
                        'text': 'Test sighting',
                        'count': 1,
                        'icon': 'HEART',
                        'shareableMatchTokens': [media1_id],
                        'species': {
                            'id': species_id,
                            'iconUrl': 'http://example.com/species_icon.jpg',
                            'name': 'Test Bird',
                            'isUnofficialName': False,
                            'mapUrl': 'http://example.com/map.jpg',
                        },
                    }
                ],
            },
            'videoMedia': {
                'id': video_id,
                'createdAt': '2024-04-06T08:08:36.208Z',
                'thumbnailUrl': 'http://example.com/vthumb.jpg',
                'contentUrl': 'http://example.com/vcontent.mp4',
            },
        },
    }


@pytest.fixture
def sample_multi_bird_event(sample_event: dict[str, Any]) -> dict[str, Any]:
    """Create a sample event with multiple birds.

    Args:
    ----
        sample_event: The base single-bird event to build upon

    Returns:
    -------
        Dictionary containing an event with multiple bird sightings

    """
    multi_event = sample_event.copy()
    # Deep copy of sighting
    multi_event['sighting'] = sample_event['sighting'].copy()
    # Deep copy of sightingReport
    multi_event['sighting']['sightingReport'] = sample_event['sighting'][
        'sightingReport'
    ].copy()
    # Deep copy of sightings list
    multi_event['sighting']['sightingReport']['sightings'] = sample_event['sighting'][
        'sightingReport'
    ]['sightings'].copy()

    # Generate valid UUID4 values for the second bird
    second_bird_id = str(uuid4())
    second_species_id = str(uuid4())
    media2_id = sample_event['sighting']['medias'][1]['id']

    # Add a second bird sighting
    multi_event['sighting']['sightingReport']['sightings'].append(
        {
            'id': second_bird_id,
            'matchTokens': [media2_id],
            'color': 'BLUE',
            'text': 'Another test sighting',
            'count': 2,
            'icon': 'STAR',
            'shareableMatchTokens': [media2_id],
            'species': {
                'id': second_species_id,
                'iconUrl': 'http://example.com/species2_icon.jpg',
                'name': 'Another Test Bird',
                'isUnofficialName': False,
                'mapUrl': 'http://example.com/map2.jpg',
            },
        }
    )

    return multi_event


@pytest.fixture
def sample_event_with_cant_decide_birds(sample_event: dict[str, Any]) -> dict[str, Any]:
    """Create a sample event that includes birds that can't be confidently identified.

    Args:
    ----
        sample_event: The base single-bird event to build upon

    Returns:
    -------
        Dictionary containing an event with both recognized and unrecognized
        bird sightings

    """
    event = sample_event.copy()
    # Deep copy of sighting
    event['sighting'] = sample_event['sighting'].copy()
    # Deep copy of sightingReport
    event['sighting']['sightingReport'] = sample_event['sighting'][
        'sightingReport'
    ].copy()
    # Deep copy of sightings list
    event['sighting']['sightingReport']['sightings'] = sample_event['sighting'][
        'sightingReport'
    ]['sightings'].copy()

    # Generate valid UUID4 values for the unrecognized bird
    cant_decide_id = str(uuid4())
    species1_id = str(uuid4())
    species2_id = str(uuid4())
    media_id = sample_event['sighting']['medias'][0]['id']

    # Add an unrecognized bird sighting (SightingCantDecideWhichBird)
    event['sighting']['sightingReport']['sightings'].append(
        {
            'id': cant_decide_id,
            'matchTokens': [media_id],
            '__typename': 'SightingCantDecideWhichBird',
            'suggestions': [
                {
                    'isCollected': True,
                    'species': {
                        'id': species1_id,
                        'iconUrl': 'http://example.com/species1_icon.jpg',
                        'name': 'Possible Bird 1',
                        'isUnofficialName': False,
                        'mapUrl': 'http://example.com/map1.jpg',
                    },
                    'media': None,
                },
                {
                    'isCollected': False,
                    'species': {
                        'id': species2_id,
                        'iconUrl': 'http://example.com/species2_icon.jpg',
                        'name': 'Possible Bird 2',
                        'isUnofficialName': False,
                        'mapUrl': 'http://example.com/map2.jpg',
                    },
                    'media': None,
                },
            ],
        }
    )

    return event


def test_identifiable_model_serialization() -> None:
    """Test that UUIDs are properly serialized."""
    valid_uuid = str(uuid4())
    model = IdentifiableModel(id=valid_uuid)
    serialized = model.model_dump()
    assert serialized['id'] == valid_uuid


def test_sighting_report_token_validation() -> None:
    """Test that the JWT token is properly decoded."""
    # Create a valid JWT token
    valid_token = jwt.encode(
        {'reportToken': '{"feeder_id": "test"}'}, key='secret', algorithm='HS256'
    )
    report = SightingReport(reportToken=valid_token, sightings=[])

    # The report_token should be the decoded JSON payload
    assert isinstance(report.report_token, dict)
    assert report.report_token.get('feeder_id') == 'test'

    # Test with invalid JWT token
    with pytest.raises(ValueError, match='Invalid JWT token'):
        SightingReport(reportToken='invalid_token', sightings=[])


def test_report_formatter_creates_single_bird(sample_event: dict[str, Any]) -> None:
    """Test that the ReportFormatter correctly identifies a single bird.

    From event data.
    """
    formatter = ReportFormatter(BBEventModel(**sample_event))
    report = formatter.report
    # Expect one bird sighting from our sample event.
    assert len(report.birds_sighted) == NUM_BIRDS_SINGLE
    bird = report.birds_sighted[0]
    # Check that the image_urls list contains our URL
    url_found = any(
        str(url) == 'http://example.com/content1.jpg' for url in bird.image_urls
    )
    assert url_found


def test_report_formatter_creates_multiple_birds(
    sample_multi_bird_event: dict[str, Any],
) -> None:
    """Test that the ReportFormatter correctly processes multiple birds."""
    formatter = ReportFormatter(BBEventModel(**sample_multi_bird_event))
    report = formatter.report

    # Should have two birds
    assert len(report.birds_sighted) == NUM_BIRDS_MULTIPLE

    # Check first bird
    assert report.birds_sighted[0].species.name == 'Test Bird'
    first_url_found = any(
        str(url) == 'http://example.com/content1.jpg'
        for url in report.birds_sighted[0].image_urls
    )
    assert first_url_found

    # Check second bird
    assert report.birds_sighted[1].species.name == 'Another Test Bird'
    second_url_found = any(
        str(url) == 'http://example.com/content2.jpg'
        for url in report.birds_sighted[1].image_urls
    )
    assert second_url_found


def test_process_unrecognized_birds(
    sample_event_with_cant_decide_birds: dict[str, Any],
) -> None:
    """Test that the ReportFormatter correctly processes unrecognized birds."""
    formatter = ReportFormatter(BBEventModel(**sample_event_with_cant_decide_birds))
    report = formatter.report

    # Should have two birds (one recognized, one unrecognized)
    assert len(report.birds_sighted) == NUM_BIRDS_RECOGNIZED_UNRECOGNIZED

    # Check first bird (recognized)
    assert report.birds_sighted[0].species.name == 'Test Bird'

    # Check second bird (unrecognized but using the first suggestion)
    assert report.birds_sighted[1].species.name == 'Possible Bird 1'

    # Ensure the image URL for the unrecognized bird is correctly assigned
    media_id = sample_event_with_cant_decide_birds['sighting']['medias'][0]['id']
    second_bird_tokens = sample_event_with_cant_decide_birds['sighting'][
        'sightingReport'
    ]['sightings'][1]['matchTokens']
    assert media_id in second_bird_tokens  # Verify the test fixture is correct

    # The unrecognized bird should have the correct image URL assigned
    second_url_found = any(
        str(url) == 'http://example.com/content1.jpg'
        for url in report.birds_sighted[1].image_urls
    )
    assert second_url_found


def test_format_slack_message_contains_header(sample_event: dict[str, Any]) -> None:
    """Test that the formatted slack message contains a proper header."""
    formatter = ReportFormatter(BBEventModel(**sample_event))
    blocks = formatter.format_slack_message()
    # Check that one of the blocks is a header with the expected text.
    header_found = any(
        block.get('type') == 'header'
        and '1 bird' in block.get('text', {}).get('text', '')
        for block in blocks
    )
    assert header_found


@patch('wikipedia.search')
@patch('wikipedia.page')
def test_format_slack_message_multiple_birds(
    mock_wiki_page: MagicMock,
    mock_wiki_search: MagicMock,
    sample_multi_bird_event: dict[str, Any],
    sample_event: dict[str, Any],
) -> None:
    """Test that the slack message correctly shows multiple birds."""
    # Mock Wikipedia to avoid real calls
    mock_wiki_search.return_value = ['Test Bird']
    mock_page = MagicMock()
    mock_page.url = 'http://example.com/wiki/Test_Bird'
    mock_page.title = 'Test Bird'
    mock_wiki_page.return_value = mock_page

    formatter = ReportFormatter(BBEventModel(**sample_multi_bird_event))
    blocks = formatter.format_slack_message()

    # Check for the plural "birds" in the header
    header_found = any(
        block.get('type') == 'header'
        and '2 birds' in block.get('text', {}).get('text', '')
        for block in blocks
    )
    assert header_found

    # Should have more blocks for 2 birds than for 1 bird
    with (
        patch('wikipedia.search') as single_mock_search,
        patch('wikipedia.page') as single_mock_page,
    ):
        # Set up the same mocks for the single bird test
        single_mock_search.return_value = ['Test Bird']
        mock_page = MagicMock()
        mock_page.url = 'http://example.com/wiki/Test_Bird'
        mock_page.title = 'Test Bird'
        single_mock_page.return_value = mock_page

        single_bird_formatter = ReportFormatter(BBEventModel(**sample_event))
        single_bird_blocks = single_bird_formatter.format_slack_message()
        assert len(blocks) > len(single_bird_blocks)


def test_slack_message_structure(sample_event: dict[str, Any]) -> None:
    """Test that the slack message has the expected structure with header and blocks."""
    formatter = ReportFormatter(BBEventModel(**sample_event))
    slack_message = formatter.format_slack_message()
    # The message should contain at least MIN_BLOCKS_EXPECTED blocks:
    # header, divider, and at least one bird block
    assert len(slack_message) >= MIN_BLOCKS_EXPECTED
    # The first block should be a header block.
    assert slack_message[0].get('type') == 'header'


@patch('wikipedia.search')
@patch('wikipedia.page')
def test_sighted_bird_create_slack_blocks_with_wiki(
    mock_wiki_page: MagicMock, mock_wiki_search: MagicMock
) -> None:
    """Test that SightedBird correctly creates Slack blocks with wiki information."""
    # Mock the Wikipedia API calls
    mock_wiki_search.return_value = ['Great Bird']
    mock_page = MagicMock()
    mock_page.url = 'http://example.com/wiki/Great_Bird'
    mock_page.title = 'Great Bird'
    mock_wiki_page.return_value = mock_page

    # Create a SightedBird instance with valid UUID4 values
    species_id = str(uuid4())
    video_id = str(uuid4())

    species = Species(
        id=species_id,
        iconUrl='http://example.com/species_icon.jpg',
        name='Great Bird',
        isUnofficialName=False,
        mapUrl='http://example.com/map.jpg',
    )

    video_media = VideoMedia(
        id=video_id,
        createdAt=datetime.now(tz=UTC),
        thumbnailUrl='http://example.com/vthumb.jpg',
        contentUrl='http://example.com/vcontent.mp4',
    )

    bird = SightedBird(
        species=species,
        image_urls=['http://example.com/content1.jpg'],
        video_media=video_media,
    )

    # Generate Slack blocks
    blocks = bird.create_slack_blocks(feeder_name='Test Feeder')

    # Should contain context block with species name
    context_blocks = [b for b in blocks if b.get('type') == 'context']
    assert len(context_blocks) > 0

    # Should contain section block with wiki info
    section_blocks = [b for b in blocks if b.get('type') == 'section']
    assert len(section_blocks) > 0

    # Should contain image blocks
    image_blocks = [b for b in blocks if b.get('type') == 'image']
    assert len(image_blocks) > 0
    assert image_blocks[0].get('title', {}).get('text') == 'Great Bird was sighted!'


@patch('wikipedia.search')
def test_sighted_bird_create_slack_blocks_without_wiki(
    mock_wiki_search: MagicMock,
) -> None:
    """Test that SightedBird correctly creates Slack blocks without wiki info."""
    # Mock the Wikipedia API to return no results
    mock_wiki_search.return_value = []

    # Create a SightedBird instance with valid UUID4 values
    species_id = str(uuid4())
    video_id = str(uuid4())

    species = Species(
        id=species_id,
        iconUrl='http://example.com/species_icon.jpg',
        name='Rare Bird',
        isUnofficialName=False,
        mapUrl='http://example.com/map.jpg',
    )

    video_media = VideoMedia(
        id=video_id,
        createdAt=datetime.now(tz=UTC),
        thumbnailUrl='http://example.com/vthumb.jpg',
        contentUrl='http://example.com/vcontent.mp4',
    )

    bird = SightedBird(
        species=species,
        image_urls=['http://example.com/content1.jpg'],
        video_media=video_media,
    )

    # Generate Slack blocks
    blocks = bird.create_slack_blocks(feeder_name='Test Feeder')

    # Should still create section block with fallback text
    section_blocks = [b for b in blocks if b.get('type') == 'section']
    assert len(section_blocks) > 0
    text = section_blocks[0].get('text', {}).get('text', '')
    assert 'Rare Bird was sighted!' in text


def test_automation_report() -> None:
    """Test the AutomationReport model."""
    # Generate valid UUID4 values
    feeder_id = str(uuid4())
    species_id = str(uuid4())
    video_id = str(uuid4())

    feeder = Feeder(id=feeder_id, name='Test Feeder', state='READY')

    # Empty report
    report = AutomationReport(feeder=feeder)
    assert report.feeder.name == 'Test Feeder'
    assert len(report.birds_sighted) == 0

    # Report with birds
    species = Species(
        id=species_id,
        iconUrl='http://example.com/species_icon.jpg',
        name='Test Bird',
        isUnofficialName=False,
        mapUrl='http://example.com/map.jpg',
    )

    video_media = VideoMedia(
        id=video_id,
        createdAt=datetime.now(tz=UTC),
        thumbnailUrl='http://example.com/vthumb.jpg',
        contentUrl='http://example.com/vcontent.mp4',
    )

    bird = SightedBird(
        species=species,
        image_urls=['http://example.com/content1.jpg'],
        video_media=video_media,
    )

    report = AutomationReport(feeder=feeder, birds_sighted=[bird])
    assert len(report.birds_sighted) == 1
    assert report.birds_sighted[0].species.name == 'Test Bird'


if __name__ == '__main__':
    # Run the tests if executed directly.
    import sys

    sys.exit(pytest.main([str(Path(__file__).resolve())]))
