"""Home Assistant automation script to parse an incoming event."""

from __future__ import annotations

import json
from datetime import datetime
from functools import cached_property
from pathlib import Path
from typing import Annotated

import appdaemon.plugins.hass.hassapi as hass
import jwt
import wikipedia
from pydantic import (
    UUID4,
    BaseModel,
    Field,
    HttpUrl,
    PlainSerializer,
    field_serializer,
    field_validator,
)
from pydantic_yaml import parse_yaml_raw_as
from slackblocks import (
    ContextBlock,
    DividerBlock,
    HeaderBlock,
    Image,
    ImageBlock,
    Message,
    SectionBlock,
    Text,
)

BBHttpUrl = Annotated[
    HttpUrl, PlainSerializer(lambda u: str(u) if u else u, return_type=str)
]


class IdentifiableModel(BaseModel):
    """Base model for identifiable models."""

    id: UUID4

    @field_serializer('id')
    def serialize_uuid(uuid: UUID4) -> str:
        """Serialize the UUID to string."""
        return str(uuid)


class Postcard(IdentifiableModel):
    """Postcard model."""

    created_at: datetime = Field(..., alias='createdAt')


class Feeder(IdentifiableModel):
    """Feeder model."""

    name: str
    state: str


class Media(IdentifiableModel):
    """Media model."""

    created_at: datetime = Field(..., alias='createdAt')
    thumbnail_url: BBHttpUrl = Field(..., alias='thumbnailUrl')
    content_url: BBHttpUrl = Field(..., alias='contentUrl')


class ImageMedia(Media):
    """Image media model."""

    pass


class VideoMedia(Media):
    """Video media model."""

    pass


class Species(IdentifiableModel):
    """Species model."""

    icon_url: BBHttpUrl = Field(..., alias='iconUrl')
    name: str
    is_unofficial_name: bool = Field(..., alias='isUnofficialName')
    map_url: BBHttpUrl = Field(..., alias='mapUrl')


class SightingRecognizedBird(IdentifiableModel):
    """Sighting recognized bird model.

    This model is used to represent a bird that was sighted.
    """

    match_tokens: list[UUID4] = Field(..., alias='matchTokens')
    color: str
    text: str
    count: int
    icon: str
    shareable_match_tokens: list[UUID4] = Field(..., alias='shareableMatchTokens')
    species: Species


class Suggestion(BaseModel):
    """Model for a bird suggestion."""

    is_collected: bool = Field(..., alias='isCollected')
    species: Species
    media: ImageMedia | None = None


class SightingCantDecideWhichBird(IdentifiableModel):
    """Model for sightings where the bird type can't be confidently determined."""

    match_tokens: list[UUID4] = Field(..., alias='matchTokens')
    suggestions: list[Suggestion]
    typename: str = Field(default='SightingCantDecideWhichBird', alias='__typename')


class SightingReport(BaseModel):
    """Sighting report model."""

    report_token: str = Field(..., alias='reportToken')
    sightings: list[SightingRecognizedBird | SightingCantDecideWhichBird]

    @field_validator('report_token')
    def validate_report_token(cls: SightingReport, value: str) -> str:
        """Validate the report token."""
        if value:
            try:
                decoded = jwt.decode(value, options={'verify_signature': False})
            except jwt.exceptions.PyJWTError as e:
                msg = 'Invalid JWT token'
                raise ValueError(msg) from e
        return json.loads(decoded['reportToken'])


class BaseSighting(BaseModel):
    """Sighting model."""

    feeder: Feeder
    medias: list[ImageMedia]
    sighting_report: SightingReport = Field(..., alias='sightingReport')
    video_media: VideoMedia = Field(..., alias='videoMedia')


class BBEventModel(BaseModel):
    """Model for the incoming event."""

    postcard: Postcard
    sighting: BaseSighting


class SightedBird(BaseModel):
    """Model for sighted bird with media assigned.

    This model is used to model the data in the automation report.
    """

    species: Species
    image_urls: list[BBHttpUrl] | list[None] = []
    video_media: VideoMedia

    def create_slack_blocks(
        self: SightedBird,
        feeder_name: str = 'Unknown',  # noqa: ARG002
    ) -> list[dict]:
        """Create Slack blocks for a single bird sighting."""
        species = self.species
        ### Context Block ###
        context_block = ContextBlock(
            elements=[
                Image(
                    image_url=str(species.icon_url),
                    alt_text=species.name,
                ),
                Text(f'*{species.name}*'),
            ],
        )

        ### Section Block ###
        wiki_search = wikipedia.search(species.name)
        # Best effort to get the summary of the species
        if wiki_search:
            wiki_page = wikipedia.page(wiki_search[0])
            bird_summary = f'*<{wiki_page.url}|{wiki_page.title}>*\n'
        else:
            bird_summary = f'{species.name} was sighted!'

        section_block = SectionBlock(
            text=bird_summary,
            accessory=Image(
                image_url=str(species.map_url),
                alt_text=f'You can spot {species.name} in the highlighted area.',
            ),
        )
        ### Image Block(s) ###
        image_blocks = []
        for count, media_url in enumerate(self.image_urls):
            image_blocks.append(
                ImageBlock(
                    title=f'{self.species.name} was sighted!',
                    image_url=str(media_url),
                    alt_text=f'{self.species.name}-{count + 1}',
                )
            )

        ### Video Block ###
        # TODO: Uncomment when ready to use the video block
        # video_block = {
        #     'type': 'video',
        #     'title': {
        #         'type': 'plain_text',
        #         'text': f'Watch the video of {species.name}',
        #         'emoji': True,
        #     },
        #     'title_url': str(self.video_media.content_url),
        #     'description': {
        #         'type': 'plain_text',
        #         'text': f'Here is a video of {species.name} '
        #         'captured during the sighting.',
        #         'emoji': True,
        #     },
        #     'video_url': str(self.video_media.content_url),
        #     'alt_text': f'Video of {species.name} sighted at {feeder_name}.',
        #     'thumbnail_url': str(self.video_media.thumbnail_url),
        #     'author_name': f'{feeder_name} bird feeder',
        #     'provider_icon_url': 'https://mybirdbuddy.com/wp-content/uploads/2023/06/cropped-Birdbuddy_favicon_64x64-32x32.png',
        # }

        message = Message(
            channel='#general',
            blocks=[
                context_block,
                section_block,
                *image_blocks,
            ],
        )
        dict_message = message.to_dict()
        # Hack to add video block to the message
        # TODO: fix the video block
        # dict_message['blocks'].append(video_block)
        return dict_message['blocks']


class AutomationReport(BaseModel):
    """Automation report model."""

    feeder: Feeder
    birds_sighted: list[SightedBird] | list[None] = []


class ReportFormatter:
    """Report formatter.

    Format the report data for the Home Assistant automation.
    Output of this formatter is a list that contains list of medias.
    For each media, it contains the name of the bird/birds
    that were sighted and the URL of the media.
    """

    def __init__(self: ReportFormatter, model: BBEventModel) -> None:
        """Initialize the formatter."""
        self.model = model

    @classmethod
    def from_yaml(cls: ReportFormatter, file_path: str) -> ReportFormatter:
        """Create a formatter from a file."""
        return cls(parse_yaml_raw_as(BBEventModel, Path(file_path).read_text()))

    @cached_property
    def report(self: ReportFormatter) -> AutomationReport:
        """Create a formatted list of sightings.

        Create list of sightings with the name of the bird/birds and
        assign the URL of the media on which the bird was sighted.
        """
        report = AutomationReport(feeder=self.model.sighting.feeder)
        for sighting in self.model.sighting.sighting_report.sightings:
            media_urls = []
            for media in self.model.sighting.medias:
                if media.id in sighting.match_tokens:
                    media_urls.append(media.content_url)

            # Handle different types of sightings
            if isinstance(sighting, SightingRecognizedBird):
                # This is a recognized bird
                report.birds_sighted.append(
                    SightedBird(
                        species=sighting.species,
                        image_urls=media_urls,
                        video_media=self.model.sighting.video_media,
                    )
                )
            if (
                hasattr(sighting, 'suggestions')
                and sighting.suggestions
                and len(sighting.suggestions) > 0
            ):
                # This is a SightingCantDecideWhichBird
                # Use the first suggestion's species as our best guess
                report.birds_sighted.append(
                    SightedBird(
                        species=sighting.suggestions[0].species,
                        image_urls=media_urls,
                        video_media=self.model.sighting.video_media,
                    )
                )
        return report

    def format_slack_message(self: ReportFormatter) -> list[dict]:
        """Create a formatted Slack message."""
        message_blocks = []
        birds_count = len(self.report.birds_sighted)
        bird_text = 'bird' if birds_count == 1 else 'birds'
        header_block = HeaderBlock(
            f'New Bird Sighting! {birds_count} {bird_text} sighted!'
        )
        divider = DividerBlock()
        message = Message(
            channel='#general',
            blocks=[header_block, divider],
        )
        dict_message = message.to_dict()
        message_blocks.extend(dict_message['blocks'])
        for bird in self.report.birds_sighted:
            message_blocks.extend(
                bird.create_slack_blocks(feeder_name=self.report.feeder.name)
            )
        return message_blocks


class BirdBuddyEventProcessor(hass.Hass):
    """Bird Buddy event processor."""

    emit_event_name = 'birdbuddy_new_postcard_sighting_report'
    listen_event_name = 'birdbuddy_new_postcard_sighting'
    listen_event_handle_list: list = []  # noqa: RUF012

    def initialize(self: BirdBuddyEventProcessor) -> None:
        """Initialize the event processor."""
        self.log(f'watching event "{self.listen_event_name}" for state changes')
        self.listen_event_handle_list.append(
            self.listen_event(self.process_event, self.listen_event_name)
        )

    def process_event(
        self: BirdBuddyEventProcessor,
        event_name: str,
        data: dict,
        kwargs: dict,  # noqa: ARG002
    ) -> None:
        """Process the incoming event."""
        self.log('Processing the incoming event %s', event_name)
        formatter = ReportFormatter(BBEventModel(**data))
        self.log('Report to send: %s', formatter.report)
        report = formatter.report.model_dump()
        self.log('Report dumped successfully')
        slack_message = formatter.format_slack_message()
        self.log('Slack message created successfully')
        json.dumps(slack_message)  # Is this necessary?
        self.log('About to fire an %s event', self.emit_event_name)
        self.fire_event(
            self.emit_event_name,
            report=report,
            slack_message=slack_message,
        )

    def terminate(self: BirdBuddyEventProcessor) -> None:
        """Cancel all active listen event handles."""
        for listen_event_handle in self.listen_event_handle_list:
            self.cancel_listen_event(listen_event_handle)


if __name__ == '__main__':
    formatter: ReportFormatter = ReportFormatter.from_yaml('birds_event.yml')
    report: AutomationReport = formatter.report
    slack_message = formatter.format_slack_message()
    pass
