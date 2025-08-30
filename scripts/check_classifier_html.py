import os, logging
from pathlib import Path

# reduce noisy logs
os.environ['NO_COLOR'] = '1'
os.environ['CLICOLOR'] = '0'
logging.getLogger('werkzeug').setLevel(logging.ERROR)

from app.nlp.classifier import classify_text_html

p = r"C:\Users\stayc\Documents\code\python\automail\email-classifier-app\sample_emails\productive_example.txt"
text = Path(p).read_text(encoding='utf-8')
html = classify_text_html(text)

print('HAS_INLINE_COLOR:', 'color:' in html)
print('HAS_SCORE_GOOD:', 'score-good' in html)
print('HAS_SCORE_BAD:', 'score-bad' in html)
print('\n--- HTML PREVIEW ---\n')
print(html)
