# Home Assistant AppDaemon Applications

A collection of AppDaemon applications for Home Assistant that enhance its functionality with various automations and integrations.

## Apps in This Repository

### Bird Buddy Automation

Turns Bird Buddy postcard events into a ready-made Slack message.

Requires the [ha-birdbuddy](https://github.com/jhansche/ha-birdbuddy) integration
**v0.1.0 or newer**.

#### Features

- **Event Processing**: Listens for `birdbuddy_new_postcard` events from Home Assistant
  (payload: `postcard_id`, `feeder_id`, `species` as `{id, name}`, first `media`)
- **Rich Notifications**: Builds Slack blocks with the species names, a Wikipedia link
  per species (best effort), and the postcard image
- **Report Event**: Fires `birdbuddy_new_postcard_sighting_report` with `report`,
  `title` and `slack_message`, for a Home Assistant automation to post via `notify`

> **Important:** the integration only fires `birdbuddy_new_postcard` when Home Assistant
> itself has a listener for it (an automation with an event or device trigger on it).
> AppDaemon's subscription does not count, so keep such an automation enabled.

Since v0.1.0 the event no longer carries species icons, range maps, the video, or
more than one image, so those parts of the message are gone.

### Additional Apps

_More apps will be added to this repository as they are developed._

## Installation

### Prerequisites

- Home Assistant
- AppDaemon 4.x
- Python 3.11+

### Global Dependencies

```bash
pip install pydantic pydantic-yaml slackblocks wikipedia
```

### App-Specific Setup

#### Bird Buddy Automation

Add the following to your AppDaemon `apps.yaml`:

```yaml
bb_event_processor:
  module: bb_processor
  class: BirdBuddyEventProcessor
```

## Usage

### Bird Buddy Automation

When a bird visits your Bird Buddy feeder, the automation will:

1. Receive the `birdbuddy_new_postcard` event from Home Assistant
2. Summarize the recognized species and the postcard image
3. Format a Slack message with names, Wikipedia links and the image
4. Fire `birdbuddy_new_postcard_sighting_report` with the report and the message

## Repository Structure

```
apps/                  # AppDaemon apps
  __init__.py
  apps.yaml            # AppDaemon configuration
  bb_processor.py      # Bird Buddy automation
data/                  # Sample data for testing
  new_postcard_event.yml
tests/                 # Test suite
  test_bb_processor.py
```

## Development

### Testing

Tests are written using pytest and can be run with:

```bash
pytest tests/
```

### Linting

This project uses `ruff` for linting and formatting:

```bash
ruff check .
ruff format .
```

Pre-commit hooks are configured to automatically run linting:

```bash
pre-commit install
```

### Adding a New App

1. Create a new Python file in the `apps` directory
2. Add the app configuration to `apps.yaml`
3. Add tests to the `tests` directory
4. Update this README with app details

## Configuration

The AppDaemon configuration is managed in the `apps.yaml` file. Each app has its own section with specific configuration options.

See the [AppDaemon documentation](https://appdaemon.readthedocs.io/en/latest/) for more details on app configuration.

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Credits

Created by [Ondrej Gajdusek](mailto:ondrej@gajdusek.dev)
