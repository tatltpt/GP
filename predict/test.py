
import re
import os
import keras_ocr
import matplotlib.pyplot as plt

pipeline = keras_ocr.pipeline.Pipeline()

uploads_dir = "/home/tuta/test/image"
custom_images = []
for filename in os.listdir(uploads_dir):
    custom_images.append(os.path.join(uploads_dir, filename))
for i in range(0, len(custom_images)):
  images = [keras_ocr.tools.read(custom_images[i])]
  predictions = pipeline.recognize(images)
  with open('results.txt', 'a+') as f:
    for idx, prediction in enumerate(predictions):
      f.write(os.path.basename(custom_images[i]) + ": ")
      for word, array in prediction:
        tmp = re.compile(r"\b[0-9]{1,7}\b|\b[a-z][0-9]{2,}\b").findall(word)
        if (tmp != []):
          bib = tmp.pop()
          f.write(str(bib) + " ")
      f.write("\n")
