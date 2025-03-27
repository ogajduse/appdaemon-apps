# Home Assistant AppDaemon Applications

A collection of AppDaemon applications for Home Assistant that enhance its functionality with various automations and integrations.

## Apps in This Repository

### Bird Buddy Automation

An automation that processes Bird Buddy smart bird feeder events, identifies bird species in images, and creates rich notifications.

#### Features

- **Event Processing**: Listens for `birdbuddy_new_postcard_sighting` events from Home Assistant
- **Bird Identification**: Processes Bird Buddy sighting data for recognized birds and uncertain identifications
- **Media Handling**: Associates images with specific bird sightings
- **Rich Notifications**: Creates formatted messages for Slack with:
  - Bird species information
  - Multiple images of the sighting
  - Wikipedia lookup for additional species information
  - Range maps for bird species
  - Support for video content (in progress)
- **Full Pydantic Models**: Complete type-validated models for Bird Buddy API data

### Additional Apps

_More apps will be added to this repository as they are developed._

## Installation

### Prerequisites

- Home Assistant
- AppDaemon 4.x
- Python 3.11+

### Global Dependencies

```bash
pip install pydantic pyjwt pydantic-yaml slackblocks wikipedia
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

1. Receive the event data from Home Assistant
2. Process the bird sighting information
3. Match images to the detected birds
4. Create a report with all birds and their details
5. Format a message for Slack with images and context
6. Emit a new event with the processed information

## Repository Structure

```
apps/                  # AppDaemon apps
  __init__.py
  apps.yaml            # AppDaemon configuration
  bb_processor.py      # Bird Buddy automation
data/                  # Sample data for testing
  birds_event.yml
  birds_event.json
  birds_event_two_birds.yml
scripts/               # Utility scripts
  blocks.py            # Slack blocks helper
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
