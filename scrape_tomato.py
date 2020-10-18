import re 
import os
import json
import pandas as pd
from time import sleep
from random import randint 

import requests 
from bs4 import BeautifulSoup as bsoup 
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException

from nltk.corpus import stopwords 
from nltk.tokenize import word_tokenize 

from itertools import count
from collections import Counter


def clean_gross_string(input_string):
    with open('tomato_gross_text', 'a') as fileout: 
        fileout.write(f'{input_string}\n')
    if 'M' in input_string:
        result = int(''.join(list(filter(lambda item: item.isdigit(), input_string))))
        result += 1_000_000
    return result 


def clean_genre_string(input_string):
    input_list = input_string.split() 
    cleaned_list = list(filter(lambda item: len(item)>1, input_list))
    return ', '.join(cleaned_list)


def count_user_review(review_url, msg_head, msg_queue, driver, stop_words):
    driver.get(review_url)
    result_counter = Counter()
    # 10 reviews per page 
    for page_num in range(250):
        sleep(randint(30, 70)/10)

        for review_block in driver.find_elements_by_class_name('audience-reviews__item'): 
            current_review = review_block.find_element_by_tag_name('p').text 
            current_review_cleaned = [word for word in word_tokenize(current_review) if word not in stop_words]
            result_counter += Counter(current_review_cleaned)
        
        msg_queue.put(f'{msg_head}, page {page_num+1}/{250}')
        next_button = driver.find_elements_by_class_name('prev-next-paging__button-text')
        next_button = list(filter(lambda item: item.text=='NEXT', next_button))
        if next_button: 
            '''
            log_in_hidden = driver.find_elements_by_class_name('modal fade')
            log_in_hidden = any(item.get_attribute('id')=='login' and 
                                item.get_attribute('style')=='display: none;' for item in log_in_hidden)

            if not log_in_hidden:
                input_blocks = driver.find_elements_by_tag_name('input')
                uname_block = list(filter(lambda item: item.get_attribute('id')=='login_username', input_blocks))[0]
                pswd_block = list(filter(lambda item: item.get_attribute('id')=='login_password', input_blocks))[0]
                uname_block.click() 
                uname_block.send_keys(user_name)
                pswd_block.click() 
                pswd_block.send_keys(password)
                buttons = driver.find_elements_by_tag_name('button')
                list(filter(lambda item: item.get_attribute('type')=='submit', buttons))[0].click()
            '''
            next_button[0].click()
        else:
            break 

    return result_counter


def scrape_tomato_movie(movie_json_queue, msg_queue, worker_id, return_dict, driver_path):
    # tomato things need to be searched, need clicking and redirecting
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    driver = webdriver.Chrome(executable_path=driver_path, options=options)
    sleep(5)
    search_templet = 'https://www.google.com/search?q=rottentomatoes.com%3A+{}'
    
    with open('tomato_credentials.txt', 'r') as filein: 
        user_name = filein.readline().strip().partition(':')[-1]
        password = filein.readline().strip().partition(':')[-1]
    stop_words = set(stopwords.words('english'))
    # report progress
    msg_head = f'scraper {worker_id} for rotten tomato '
    msg_queue.put(f'{msg_head}started, waiting for url')
    meta_data_str = movie_json_queue.get(block=True)

    # record df
    scrape_columns = ['title', 'year', 'genre', 'rating', 'rating_count', 'box gross', 
                        'review_word_1', 'review_word_2', 'review_word_3', 'review_word_4', 'review_word_5']
    master_result = pd.DataFrame(columns=scrape_columns)
    
    while meta_data_str != 'exit':
        meta_data = json.loads(meta_data_str)
        title, year = meta_data.values() 
        # we need ot use google search, rottentomatoes have shadow-root
        # things within can't be accessed with scraper, bsoup or selenium 
        search_url = search_templet.format('+'.join([*title.split(), year]))
        driver.get(search_url)

        for block in driver.find_elements_by_tag_name('h3'):
            if title in block.text and year in block.text: 
                block.find_element_by_tag_name('span').click()
                break
        else:
            meta_data_str = movie_json_queue.get(block=True)
            continue 
        
        sleep(5)
        # get rating
        rating_str = driver.find_element_by_class_name('mop-ratings-wrap__percentage').text.strip()
        rating_value = int(''.join(list(filter(lambda item: item.isdigit(), rating_str)))) / 100
        rating_count_str = driver.find_elements_by_class_name('mop-ratings-wrap__text--small')[2].text
        rating_count = int(''.join(list(filter(lambda item: item.isdigit(), rating_count_str))))

        # get genre and gross USA
        genre = gross_usa = ''
        for info_block in driver.find_elements_by_class_name('meta-row clearfix'):
            if 'Genre' in info_block.text: 
                genre_dirty = info_block.find_element_by_class_name('meta-value genre').text
                genre = clean_genre_string(genre_dirty)
            elif 'Gross USA' in info_block.text: 
                gross_usa_str = info_block.find_element_by_class_name('meta-value').text
                gross_usa = clean_gross_string(gross_usa_str)

        msg_queue.put(f'{msg_head}completed basic info of {title} ({year}), working on user_review')
        # user_review 
        user_review_url = driver.find_element_by_class_name('mop-audience-reviews__view-all--link').get_attribute('href')
        current_msg_head = f'{msg_head} working on {title}'
        user_review_counter = count_user_review(user_review_url, current_msg_head, msg_queue, driver, stop_words)
        word_count = list(user_review_counter.items())
        word_count.sort(key=lambda item: item[1], reverse=True)
        top_words = [item[0] for item in word_count[:5]]

        # record scrape result
        result_list = [title, year, genre, rating_value, rating_count, gross_usa, *top_words]
        current_result = {key:value for key, value in zip(scrape_columns, result_list)}
        master_result = master_result.append(current_result, ignore_index=True)

        # go to next movie 
        meta_data_str = movie_json_queue.get(block=True)

    driver.quit()
    return_dict[f'tomato_{worker_id}'] = master_result
    msg_queue.put(f'{msg_head}job completed, result returned, process terminated')

    return None 
