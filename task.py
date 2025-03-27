import argparse
import csv
import logging
import re
from typing import List, Dict, Optional

import requests
from requests.exceptions import RequestException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# PubMed API URL
PUBMED_API_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
DETAILS_API_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

# API Key
API_KEY = "ba128ae5d7b346d79fb32cf43125ff111b08"

def fetch_pubmed_papers(query: str, retmax: int = 20) -> List[Dict]:
    """Fetches research papers from PubMed based on the query."""
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": retmax,
        "retmode": "json",
        "api_key": API_KEY
    }
    try:
        response = requests.get(PUBMED_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        paper_ids = data.get("esearchresult", {}).get("idlist", [])
        return fetch_paper_details(paper_ids) if paper_ids else []
    except RequestException as e:
        logger.error(f"Error fetching papers: {e}")
        return []


def fetch_paper_details(paper_ids: List[str]) -> List[Dict]:
    """Fetches details for a list of PubMed paper IDs."""
    params = {
        "db": "pubmed",
        "id": ",".join(paper_ids),
        "retmode": "json",
        "api_key": API_KEY
    }
    try:
        response = requests.get(DETAILS_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        return parse_paper_details(data)
    except RequestException as e:
        logger.error(f"Error fetching paper details: {e}")
        return []


def parse_paper_details(data: Dict) -> List[Dict]:
    """Parses details from PubMed API response."""
    papers = []
    for paper_id, details in data.get("result", {}).items():
        if paper_id == "uids":
            continue
        title = details.get("title", "N/A")
        pub_date = details.get("pubdate", "N/A")
        authors = details.get("authors", [])
        company_authors, company_names = filter_non_academic_authors(authors)
        corresponding_email = extract_corresponding_email(authors)
        papers.append({
            "PubmedID": paper_id,
            "Title": title,
            "Publication Date": pub_date,
            "Non-academic Author(s)": ", ".join(company_authors),
            "Company Affiliation(s)": ", ".join(company_names),
            "Corresponding Author Email": corresponding_email or "N/A"
        })
    return papers


def filter_non_academic_authors(authors: List[Dict]) -> (List[str], List[str]):
    """Filters non-academic authors based on heuristics."""
    non_academic_authors = []
    company_names = []
    for author in authors:
        affiliation = author.get("affiliation", "")
        if affiliation and not re.search(r'university|college|institute|lab', affiliation, re.IGNORECASE):
            non_academic_authors.append(author.get("name", "Unknown"))
            company_names.append(affiliation)
    return non_academic_authors, company_names


def extract_corresponding_email(authors: List[Dict]) -> Optional[str]:
    """Extracts the email of the corresponding author if available."""
    for author in authors:
        if "email" in author:
            return author["email"]
    return None


def save_to_csv(papers: List[Dict], filename: str):
    """Saves the fetched papers to a CSV file."""
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=papers[0].keys())
        writer.writeheader()
        writer.writerows(papers)


def main():
    parser = argparse.ArgumentParser(description="Fetch research papers from PubMed based on a query.")
    parser.add_argument("query", type=str, help="Search query for PubMed.")
    parser.add_argument("-f", "--file", type=str, help="Filename to save results.")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode.")
    
    args = parser.parse_args()
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    papers = fetch_pubmed_papers(args.query)
    
    if args.file:
        save_to_csv(papers, args.file)
        logger.info(f"Results saved to {args.file}")
    else:
        for paper in papers:
            print(paper)

if __name__ == "__main__":
    main()
