import os 
import requests_html

url = "https://musescore.com/sheetmusic"

session = requests_html.HTMLSession()
rx = session.request(url)

rx.render(sleep=1, timeout=20)

rx.search(r"<span class=\"xBwRG o1QE0 HtKJn cPGYN\">(.*?)</span>")