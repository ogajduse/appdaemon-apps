"""Tester module for Slack blocks."""

import json

import wikipedia
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

# VideoBlock,  # TODO: add support for video block to upstream
from apps.bb_processor import (
    ReportFormatter,
    SightedBird,
)


def create_image_blocks(bird: SightedBird) -> list[ImageBlock]:
    """Create image blocks for the bird sighting (single bird)."""
    image_blocks = []
    for count, media_url in enumerate(bird.image_urls):
        image_blocks.append(
            ImageBlock(
                title=f'{bird.species.name} was sighted!',
                image_url=str(media_url),
                alt_text=f'{bird.species.name}-{count + 1}',
            )
        )
    return image_blocks


def create_blocks_for_one_bird(bird_sighting: SightedBird) -> list[dict]:
    """Create blocks for a single bird sighting."""
    species = bird_sighting.species
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
        bird_summary = f'*<{wiki_page.url}|{wiki_page.title}*\n'
        bird_summary += wiki_page.summary
    else:
        bird_summary = f'{species.name} was sighted!'

    section_block = SectionBlock(
        text=bird_summary,
        accessory=Image(
            image_url=str(species.map_url),
            alt_text=f'You can spot {species.name} in the highlighted area.',
        ),
    )
    ### Image Block ###
    image_blocks = create_image_blocks(bird_sighting)

    ### Video Block ###
    video_block = {
        'type': 'video',
        'title': {
            'type': 'plain_text',
            'text': f'Watch the video of {species.name}',
            'emoji': True,
        },
        'title_url': str(bird_sighting.video_media.content_url),
        'description': {
            'type': 'plain_text',
            'text': f'Here is a video of {species.name} captured during the sighting.',
            'emoji': True,
        },
        'video_url': str(bird_sighting.video_media.content_url),
        'alt_text': f'Video of {species.name} sighted at {report.feeder.name}.',
        'thumbnail_url': str(bird_sighting.video_media.thumbnail_url),
        'author_name': f'{report.feeder.name} bird feeder',
        'provider_icon_url': 'https://mybirdbuddy.com/wp-content/uploads/2023/06/cropped-Birdbuddy_favicon_64x64-32x32.png',
    }

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
    dict_message['blocks'].append(video_block)
    return dict_message['blocks']


if __name__ == '__main__':
    rf: ReportFormatter = ReportFormatter.from_yaml('data/birds_event_two_birds.yml')
    report = rf.report()

    ### Header Block ###
    birds_count = len(report.birds_sighted)
    bird_text = 'bird' if birds_count == 1 else 'birds'
    header_block = HeaderBlock(f'New Bird Sighting! {birds_count} {bird_text} sighted!')
    divider = DividerBlock()
    message = Message(
        channel='#general',
        blocks=[header_block, divider],
    )
    dict_message = message.to_dict()

    # generate blocks for each bird
    for bird_sighting in report.birds_sighted:
        dict_message['blocks'] += create_blocks_for_one_bird(bird_sighting)

    result = json.dumps(dict_message['blocks'])
    print(result)
