import requests
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_search_results(response):
    results = response["hits"]["hits"]
    accession_ids = []
    for result in results:
        accession_ids.append(result["_source"]["accession_id"])
    return accession_ids


def flatten_list(list_of_lists):
    return [xl for l in list_of_lists for xl in l]


class API:
    def __init__(self, link):
        self.link = link
        self.page_size = 100

    def request(self, endpoint):
        response = {}
        try:
            response = requests.get(f"{self.link}/{endpoint}")
            if response.status_code == 200:
                return response.json()
            else:
                logger.info("Failed to make the request!")
                response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.info(f"An error occurred: {e}")
            return None

    def get_all_studies_from_search(self, endpoint):
        endpoint = endpoint + f"&pagination.page_size={self.page_size}"
        first_page = endpoint + f"&pagination.page=1"
        results = []
        first_request = self.request(first_page)
        if first_request:
            results.append(first_request["hits"]["hits"])
            total_pages = first_request["pagination"]["total_pages"]
            page = 2
            while page <= total_pages:
                response = self.request(endpoint + f"&pagination.page={page}")
                if response:
                    results.append(response["hits"]["hits"])
                    page += 1

        return flatten_list(results)