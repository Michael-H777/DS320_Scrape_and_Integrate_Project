import re 
import os
import json
import pickle
import zipfile 
import platform 
import pandas as pd
from random import randint 
from itertools import count
from time import time, sleep
from collections import Counter

import requests 
from bs4 import BeautifulSoup as bsoup 
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException

from scrape_imbd import scrape_imdb_movie
from scrape_tomato import scrape_tomato_movie

from nltk.corpus import stopwords 
from nltk.tokenize import word_tokenize 

from multiprocessing import Process, Queue, Manager

