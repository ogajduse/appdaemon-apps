"""Turn Bird Buddy postcard events into a Slack report event.

Listens for ``birdbuddy_new_postcard`` (ha-birdbuddy >= 0.1.0) and fires
``birdbuddy_new_postcard_sighting_report`` with a ready-made Slack message,
which a Home Assistant automation posts with ``notify.*``.

The 0.1.0 payload is slim: ``postcard_id``, ``feeder_id``, a list of
recognized ``species`` (``{"id", "name"}`` only) and the first ``media`` item
(or ``null``). Species icons, range maps, extra images and the video are no
longer part of the event.

Note: the integration only fires the event when Home Assistant itself has a
listener for ``birdbuddy_new_postcard`` (an automation trigger). AppDaemon's
catch-all subscription does not count, so keep an HA automation on it.
"""

from __future__ import annotations

from functools import cached_property
from pathlib import Path

import appdaemon.plugins.hass.hassapi as hass
import wikipedia
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from pydantic_yaml import parse_yaml_raw_as
from slackblocks import (
    ContextBlock,
    DividerBlock,
    HeaderBlock,
    ImageBlock,
    Message,
    SectionBlock,
    Text,
)

SLACK_CHANNEL = '#general'  # Only needed to build a Message; notify sets it.
HEADER_MAX = 150  # Slack header text limit
IMAGE_TITLE_MAX = 2000  # Slack image block title limit


class Species(BaseModel):
    """A recognized species as carried by the event."""

    model_config = ConfigDict(extra='ignore')

    id: str
    name: str


class Media(BaseModel):
    """The first postcard media item, in Bird Buddy's own key spelling."""

    model_config = ConfigDict(extra='ignore', populate_by_name=True)

    id: str
    thumbnail_url: HttpUrl = Field(..., alias='thumbnailUrl')
    content_url: HttpUrl | None = Field(default=None, alias='contentUrl')

    @property
    def best_url(self: Media) -> str:
        """Full-size URL when present, otherwise the thumbnail."""
        return str(self.content_url or self.thumbnail_url)


class NewPostcardEvent(BaseModel):
    """Payload of the ``birdbuddy_new_postcard`` event."""

    model_config = ConfigDict(extra='ignore')

    postcard_id: str
    feeder_id: str | None = None
    species: list[Species] = []
    media: Media | None = None


class AutomationReport(BaseModel):
    """Compact report fired alongside the Slack message."""

    postcard_id: str
    feeder_id: str | None
    species: list[str]
    image_url: str | None


def wikipedia_link(name: str) -> str | None:
    """Return a Slack mrkdwn link to the species' Wikipedia page, best effort."""
    try:
        results = wikipedia.search(name)
        if not results:
            return None
        page = wikipedia.page(results[0], auto_suggest=False)
    except Exception:  # noqa: BLE001 - lookup failures must not drop the post
        return None
    return f'*<{page.url}|{page.title}>*'


class ReportFormatter:
    """Build the report and the Slack blocks from one postcard event."""

    def __init__(self: ReportFormatter, event: NewPostcardEvent) -> None:
        """Initialize the formatter."""
        self.event = event

    @classmethod
    def from_yaml(cls: type[ReportFormatter], file_path: str) -> ReportFormatter:
        """Create a formatter from a YAML file holding the event data."""
        return cls(parse_yaml_raw_as(NewPostcardEvent, Path(file_path).read_text()))

    @cached_property
    def report(self: ReportFormatter) -> AutomationReport:
        """Summarize the postcard."""
        return AutomationReport(
            postcard_id=self.event.postcard_id,
            feeder_id=self.event.feeder_id,
            species=[s.name for s in self.event.species],
            image_url=self.event.media.best_url if self.event.media else None,
        )

    @property
    def title(self: ReportFormatter) -> str:
        """One-line title, also usable as the notification fallback text."""
        names = self.report.species
        if not names:
            return 'New visitor at the feeder!'
        if len(names) == 1:
            return f'New bird sighting: {names[0]}!'
        return f'New bird sighting! {len(names)} birds: {", ".join(names)}'

    def format_slack_message(self: ReportFormatter) -> list[dict]:
        """Create the Slack blocks."""
        blocks = [HeaderBlock(self.title[:HEADER_MAX]), DividerBlock()]
        for species in self.event.species:
            blocks.append(ContextBlock(elements=[Text(f'*{species.name}*')]))
            link = wikipedia_link(species.name)
            if link:
                blocks.append(SectionBlock(text=link))
        if self.report.image_url:
            blocks.append(
                ImageBlock(
                    image_url=self.report.image_url,
                    alt_text=', '.join(self.report.species) or 'Bird Buddy postcard',
                    title=self.title[:IMAGE_TITLE_MAX],
                )
            )
        return Message(channel=SLACK_CHANNEL, blocks=blocks).to_dict()['blocks']


class BirdBuddyEventProcessor(hass.Hass):
    """Bird Buddy event processor."""

    emit_event_name = 'birdbuddy_new_postcard_sighting_report'
    listen_event_name = 'birdbuddy_new_postcard'

    def initialize(self: BirdBuddyEventProcessor) -> None:
        """Subscribe to the postcard event (AppDaemon cancels it on reload)."""
        self.log('Watching event "%s"', self.listen_event_name)
        self.listen_event(self.process_event, self.listen_event_name)

    def process_event(
        self: BirdBuddyEventProcessor,
        event_name: str,
        data: dict,
        kwargs: dict,  # noqa: ARG002
    ) -> None:
        """Process one postcard event and fire the report event."""
        self.log('Processing event %s', event_name)
        formatter = ReportFormatter(NewPostcardEvent.model_validate(data))
        report = formatter.report.model_dump()
        self.log('Report: %s', report)
        self.fire_event(
            self.emit_event_name,
            report=report,
            title=formatter.title,
            slack_message=formatter.format_slack_message(),
        )


if __name__ == '__main__':
    fmt = ReportFormatter.from_yaml('data/new_postcard_event.yml')
    print(fmt.report)
    print(fmt.format_slack_message())
