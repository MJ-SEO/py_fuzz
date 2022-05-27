import requests
from bs4 import BeautifulSoup as bs
from pythonfuzz.main import PythonFuzz

@PythonFuzz
def fuzz(buf):
	try:
		url = buf.decode("ascii")

		page = requests.get(url)
		soup = bs(page.text, "html.parser")

		elements = soup.select('div.esg-entry-content a > span')
	except (UnicodeDecodeError, requests.RequestException):
		pass

if __name__ == '__main__':
	fuzz()


