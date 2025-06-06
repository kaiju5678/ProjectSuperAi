import pytesseract
from PIL import Image
import os

os.environ['TESSDATA_PREFIX'] = r'C:\Program Files\Tesseract-OCR\tessdata'
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

img = Image.open('testpic.jpg')
text = pytesseract.image_to_string(img, lang='tha')
print(text)