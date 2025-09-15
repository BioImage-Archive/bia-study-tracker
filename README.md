# BIA Study Tracker
BIA Study Tracker is a Python tool that analyzes studies from the BioImage Archive (BIA), generates summary and detailed reports, and posts them automatically to Slack on a schedule (via Github actions).

----
## Features
- Fetch studies from the BioImage Archive (BIA) search API
- Generate reports with:
  - ✅ Summary statistics (studies with/without datasets, images)
  - ✅ Detailed CSV/Excel reports for missing datasets/images and conversion report
- Post reports and files directly to Slack
- CI/CD integration for automated weekly/biweekly runs

---
## Installation

This project uses Poetry for dependency management.

```
# Clone the repo
git clone https://github.com/BioImage-Archive/bia-study-tracker.git
cd bia-study-tracker

# Install dependencies
poetry install
```

## Configuration
Set the following environment variables:

| Variable            | Description                                    | Value                                    |
| ------------------- | ---------------------------------------------- |------------------------------------------|
| `PUBLIC_SEARCH_API` | Endpoint for BIA search API                    | https://alpha.bioimagearchive.org/search |
| `SLACK_BOT_TOKEN`   | Slack Bot User OAuth Token                     | xoxb- ....                               |
| `SLACK_CHANNEL`     | Slack channel ID  | CXXXXXX                                  |

---
## Usage

Run the tracker manually: `poetry run track-ingested-studies`


## Example Slack Output
```
BIA tracker - Summary stats report

+---------------------------+-------+
| Statistic                 | Value |
+---------------------------+-------+
| Total Studies checked     | 120   |
| Studies With images       | 75    |
| Studies w/ dataset no img | 30    |
| Studies without datasets  | 15    |
+---------------------------+-------+
```
