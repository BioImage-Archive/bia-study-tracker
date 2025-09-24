import typer
from bia_study_tracker.study_tracker import BIAStudyTracker
from bia_study_tracker.utils.slack_bot import SlackReportBot
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = typer.Typer(help="Study tracker: Tracks ingested studies and creates a report.")

@app.command()
def generate_report():
    try:
        tracker = BIAStudyTracker()
        report, path = tracker.generate_report()
        bot = SlackReportBot()
        bot.run(data=report, file_path=str(path))

    except Exception as e:
        logger.error(f"Application error: {e}")


@app.command()
def check_mongo_elastic_sync():
    try:
        tracker = BIAStudyTracker()
        report = tracker.check_mongo_elastic_sync()
        bot = SlackReportBot()
        bot.send_message(report)
    except Exception as ex:
        logger.error(f"Application error: {ex}")

if __name__ == "__main__":
    app()
