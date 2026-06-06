from html.parser import HTMLParser

class MyParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
    def handle_starttag(self, tag, attrs):
        if tag == 'div':
            cls = dict(attrs).get('class', '')
            print('  ' * self.depth + f'<div class="{cls}">')
            self.depth += 1
    def handle_endtag(self, tag):
        if tag == 'div':
            self.depth -= 1
            print('  ' * self.depth + '</div>')

with open('amusement_stats/templates/staff/workbench.html', 'r', encoding='utf-8') as f:
    MyParser().feed(f.read())
