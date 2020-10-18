import re 
import os
import pandas as pd
from time import sleep

import requests 
from bs4 import BeautifulSoup as bsoup 
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException

from nltk.corpus import stopwords 
from nltk.tokenize import word_tokenize 

from itertools import count
from collections import Counter


def process_info_block(block_text):
    year = ''
    genre = []
    for text in block_text:
        if text.isdigit():
            year = int(text)
        elif text.isalpha():
            genre.append(text)

    genre.sort()
    return year, ', '.join(genre) 


def scrape_imdb_review(review_url, msg_head, msg_queue, driver, stop_words):
    expand_icon_regex = re.compile('expander-icon-wrapper.*')
    review_block_regex = re.compile('lister-item mode-detail imdb-user-review.*')

    result_counter = Counter()

    driver.get(review_url)

    msg_queue.put(f'{msg_head}clicking on show more')
    # 25 reviews per click
    for _ in range(100):
        sleep(1)
        try:
            driver.find_element_by_class_name('ipl-load-more__button').click()
        except:
            continue

    msg_queue.put(f'{msg_head}collecting user reviews')
    for block in driver.find_elements_by_class_name('lister-list'):
        review_text = block.find_element_by_class_name('content').text
        review_text_cleaned = [word for word in word_tokenize(review_text) if word not in stop_words]
        result_counter += Counter(review_text_cleaned)

    driver.close() if len(driver.window_handles)>1 else None
    return result_counter 


def scrape_imdb_movie(movie_url_queue, msg_queue, worker_id, return_dict, driver_path):
    # IMDB reviews have spoiler and show_more control, needs clicking 
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    driver = webdriver.Chrome(executable_path=driver_path, options=options)

    # regexs 
    title_regex = re.compile(u'^(.*)\xa0')
    gross_usa_regex = re.compile('Gross USA.*\$(.*)')
    review_link_regex = re.compile('.*reviews')

    # report progress
    msg_head = f'scraper {worker_id} for IMDB '
    msg_queue.put(f'{msg_head}started, waiting for url')
    movie_url = movie_url_queue.get(block=True)

    # record df
    scrape_columns = ['title', 'year', 'genre', 'rating', 'rating_count', 'box gross', 
                        'review_word_1', 'review_word_2', 'review_word_3', 'review_word_4', 'review_word_5']
    master_result = pd.DataFrame(columns=scrape_columns)
    
    while movie_url != 'exit':
        movie_soup = bsoup(requests.get(movie_url).text, 'html.parser')

        # collect title, year, genre 
        info_block = movie_soup.find(class_='title_wrapper')
        title = title_regex.search(info_block.find('h1').text).group(1)
        block_text = [item.text for item in info_block.find_all('a')]
        year, genre = process_info_block(block_text)

        # collect rating and rating_count
        rating_value = float(movie_soup.find('span', attrs={'itemprop': 'ratingValue'}).text)
        rating_count_str = movie_soup.find('span', attrs={'itemprop': 'ratingCount'}).text
        rating_count = int(''.join([item if item.isdigit() else '' for item in rating_count_str]))

        # collect box gross USA
        gross_block = list(filter(lambda item: 'Gross USA' in str(item), movie_soup.find_all(class_='txt-block')))[0]
        gross_usa_str = gross_usa_regex.search(gross_block.text).group(1)
        gross_usa = int(''.join([item if item.isdigit() else '' for item in gross_usa_str]))

        msg_queue.put(f'{msg_head}finished basic info on {title} ({year}), working on user_review')
        # retrieve review link and user reviews
        review_partial_url = movie_soup.find('a', attrs={'href': review_link_regex}).attrs['href']
        review_url = f'https://www.imdb.com{review_partial_url}'
        current_msg_head = f'{msg_head} working on {title}'
        user_review_counter = scrape_imdb_review(review_url, current_msg_head, msg_queue, driver)
        word_count = list(user_review_counter.items())
        word_count.sort(key=lambda item: item[1], reverse=True)
        top_words = [item[0] for item in word_count[:5]]
        
        # record scrape result
        result_list = [title, year, genre, rating_value, rating_count, gross_usa, *top_words]
        current_result = {key:value for key, value in zip(scrape_columns, result_list)}
        master_result = master_result.append(current_result, ignore_index=True)

        msg_queue.put(f'{msg_head}finished scraping {title} of {year}, waiting for next url')
        # get next url 
        movie_url = movie_url_queue.get(block=True)

    driver.quit()
    return_dict[f'imdb_{worker_id}'] = master_result
    msg_queue.put(f'{msg_head}job completed, result returned, process terminated')
    return None 

