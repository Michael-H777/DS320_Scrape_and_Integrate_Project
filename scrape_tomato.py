import re 
import os
import json
import pandas as pd

import requests 
from bs4 import BeautifulSoup as bsoup 
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException

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


def count_user_review(review_url, msg_head, msg_queue, driver):
    driver.get(review_url)
    result_counter = Counter()
    # 10 reviews per page 
    for page_num in range(250):

        for review_block in driver.find_elements_by_class_name('audience-reviews__item'): 
            show_more_buttons = review_block.find_elements_by_tag_name('button')
            if show_more_buttons:
                show_more_buttons[0].click() 
            current_review = review_block.find_element_by_tag_name('p').text 
            current_review_cleaned = ''.join(list(filter(lambda item: item.isalpha() or item==' ', current_review)))
            result_counter += Counter(current_review_cleaned.split())
        
        msg_queue.put(f'{msg_head}, page {page_num+1}/{250}')
        next_button = driver.find_element_by_class_name('prev-next-paging__button-text')
        if next_button: 
            next_button.click()
        else:
            break 

    return result_counter


def scrape_tomato_movie(movie_json_queue, msg_queue, worker_id, return_dict, driver_path):
    # tomato things need to be searched, need clicking and redirecting
    options = webdriver.ChromeOptions()
    #options.add_argument('--headless)
    driver = webdriver.Chrome(executable_path=driver_path, options=options)
    driver.get('https://www.rottentomatoes.com/')

    # regexs 
    title_regex = re.compile(u'^(.*)\xa0')
    gross_usa_regex = re.compile('Gross USA.*\$(.*)')
    review_link_regex = re.compile('.*reviews')

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
        driver.find_element_by_class_name('search-text').send_keys(title)
        driver.find_element_by_class_name('search-text').send_keys(Keys.ENTER)

        for result_block in driver.find_element_by_class_name('info-name'):
            if year in result_block: 
                result_block.find_element_by_tag_name('a').click()
                break
        else:
            meta_data_str = movie_json_queue.get(block=True)
            continue 
        
        # get rating
        rating_block = driver.find_element_by_class_name('mop-ratings-wrap__half audience-score')
        rating_str = rating_block.find_element_by_class_name('mop-ratings-wrap__percentage').text.strip()
        rating_value = int(''.join(list(filter(lambda item: item.isdigit(), rating_str)))) / 100
        rating_count_str = rating_block.find_element_by_tag_name('strong').text
        rating_count = int(''.join(list(filter(lambda item: item.isdigit(), rating_count_str))))

        # get genre and gross USA
        for info_block in driver.find_elements_by_class_name('meta-row clearfix'):
            if 'Genre' in info_block.text: 
                genre_dirty = info_block.find_element_by_class_name('meta-value genre').text
                genre = clean_genre_string(genre_dirty)
            elif 'Gross USA' in info_block.text: 
                gross_usa_str = info_block.find_element_by_class_name('meta-value').text
        gross_usa = clean_gross_string(gross_usa_str)

        msg_queue.put(f'{msg_head}completed basic info of {title} ({year}), working on user_review')
        # user_review 
        partial_url = driver.find_element_by_class_name('mop-audience-reviews__view-all--link').get_attribute('href')
        user_review_url = f'https://www.rottentomatoes.com{partial_url}'
        current_msg_head = f'{msg_head} working on {title}'
        user_review_counter = count_user_review(user_review_url, current_msg_head, msg_queue, driver)
        word_count = list(user_review_counter.items())
        word_count.sort(lambda item: item[1], reverse=True)
        top_words = [item[0] for item in word_count[:5]]

        # record scrape result
        result_list = [title, year, genre, rating_value, rating_count, gross_usa, *top_words]
        current_result = [key:value for key, value in zip(scrape_columns, result_list)]
        master_result = master_result.append(current_result, ignore_index=True)

        # go to next movie 
        meta_data_str = movie_json_queue.get(block=True)

    driver.quit()
    return_dict[f'imdb_{worker_id}'] = master_result
    msg_queue.put(f'{msg_head}job completed, result returned, process terminated')
    return None 
