from bs4 import BeautifulSoup
from glob import glob
import re
import pathlib
from time import sleep
import os

fs = glob("./**/*.xml", recursive=True)

for f in fs:
    path = pathlib.Path(f)
    folder = re.search("(.*?)/", str(path)).group(1)
    fname = re.search(".*?/(.*?)\.xml", str(path)).group(1) 
    i = open(f,"r", encoding="utf-8")
    soup = BeautifulSoup(i, features="xml")
    doc = soup.find("doc")
    doc.name = "text"
    #print(soup)
    #print(f)

    if not os.path.exists(f"{folder}_text-tag/"):
        print(f"{folder}_text-tag/ NOT")
        os.makedirs(f"{folder}_text-tag/")

    with open(f"{folder}_text-tag/{fname}_text.xml", "w") as out:
        out.write(str(soup))

    #sleep(2)
