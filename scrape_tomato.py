import re 
import os

import pandas as pd

import requests 
from bs4 import BeautifulSoup as bsoup 
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException

from itertools import count
from collections import Counter



def scrape_tomato_movie(movie_url_queue, msg_queue, worker_id, return_dict, driver_path):
