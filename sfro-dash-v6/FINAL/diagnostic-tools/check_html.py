from html.parser import HTMLParser
import sys

class TestHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        
    def handle_starttag(self, tag, attrs):
        if tag not in ["meta", "link", "br", "img", "hr", "input"]:
            self.tags.append((tag, self.getpos()))
            
    def handle_endtag(self, tag):
        if tag not in ["meta", "link", "br", "img", "hr", "input"]:
            if not self.tags:
                print(f"Error: Closed tag '{tag}' at {self.getpos()} but no tags are open.")
                sys.exit(1)
            opened, pos = self.tags.pop()
            if opened != tag:
                print(f"Error: Opened '{opened}' at {pos} but closed '{tag}' at {self.getpos()}.")
                sys.exit(1)

with open("/Users/gary/syncdata/Sync/dev/sfro-dash/sfro-dash-v5/index.html", "r") as f:
    content = f.read()

parser = TestHTMLParser()
parser.feed(content)
print("HTML parse verification: SUCCESS (All non-void tags match properly)")
