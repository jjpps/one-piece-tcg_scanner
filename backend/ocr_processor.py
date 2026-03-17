import cv2
import pytesseract
from PIL import Image
import re
import sys
import os

# Configura caminho do executável Tesseract para Windows
if sys.platform.startswith('win'):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def process_image(image_path):
    print(f"Processando: {image_path}")