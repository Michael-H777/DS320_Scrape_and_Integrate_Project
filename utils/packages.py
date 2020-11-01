import re 
import os
import json
import pickle
import zipfile 
import platform 
import pandas as pd
from itertools import count
from time import time, sleep
from collections import Counter
from random import randint, shuffle 

import requests 
from bs4 import BeautifulSoup as bsoup 
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException

from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

from multiprocessing import Process, Queue


custom_stop_words = set(['movie', 'movies', 'the', 'film', 'audience', 'really', 'still', 
                         'want', 'many'])

imdb_workers = 5
tomato_workers = 30
master_use_proxy = True
master_use_headless = True

retry_cut_off = 5
