import typer
from bia_study_tracker.study_tracker import BIAStudyTracker
from bia_study_tracker.utils.slack_bot import SlackReportBot
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = typer.Typer(help="Study tracker: Tracks ingested studies and creates a report.")

@app.command()
def main():
    try:
        tracker = BIAStudyTracker()
        report, message, path = tracker.generate_report()
        bot = SlackReportBot()
        bot.run(data=message, file_path=str(path))
    except Exception as e:
        logger.error(f"Application error: {e}")


if __name__ == "__main__":
    app()
