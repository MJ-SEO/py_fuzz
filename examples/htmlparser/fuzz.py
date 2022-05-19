#import importlib
#import html.parser as htmlparser
from html.parser import HTMLParser
from pythonfuzz.main import PythonFuzz


@PythonFuzz
def fuzz(buf):
    try:
        #HTMLParser= importlib.reload(htmlparser).HTMLParser
        #HTMLParser = htmlparser.HTMLParser
        string = buf.decode("ascii")
        parser = HTMLParser()
        parser.feed(string)
    except UnicodeDecodeError:
        pass


if __name__ == '__main__':
    fuzz()
