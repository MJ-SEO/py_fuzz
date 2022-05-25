from html.parser import HTMLParser


def fuzz(buf):
    try:
        string = buf#.decode("ascii")
        parser = HTMLParser()
        parser.feed(string)
    except UnicodeDecodeError:
        pass


if __name__ == '__main__':
    inp = input()
    fuzz(inp)
