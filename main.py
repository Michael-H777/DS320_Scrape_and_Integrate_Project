import re 
import os
import zipfile 
import platform 
from time import time

import requests 
from bs4 import BeautifulSoup as bsoup 

from multiprocessing import Process, Queue
from report_progress import report_progress


def download_driver(url):
    driver_file = requests.get(url).content

    with open('temp.zip', 'wb') as fileout:
        fileout.write(driver_file)
    with zipfile.ZipFile('temp.zip', 'r') as filein: 
        file_name = filein.namelist()[0]
        filein.extractall('chromedriver')

    os.remove('temp.zip')
    return f'chromedriver/{file_name}'  


def download_driver():
    master_url = 'https://chromedriver.storage.googleapis.com/86.0.4240.22/chromedriver_'
    if 'Linux' in platform.platform():
        driver_path = download_driver(f'{master_url}linux64.zip')
    elif 'Windows' in platform.platform():
        driver_path = download_driver(f'{master_url}win32.zip')
    else:
        driver_path = download_driver(f'{master_url}mac64.zip')

    return driver_path 


def scrape_imdb_rank(imdb_url_queue, tomato_json_queue, msg_queue):
    name_year_regex = re.compile('[!a-zA-Z]{1,10}([a-zA-Z ]*).*\((\d{4})\)')
    master_url = 'https://www.imdb.com/search/title/?groups=top_1000&sort=user_rating,desc&count=100&start={}&ref_=adv_nxt'

    # get 10 pages of 1000 items 
    for start_count in range(1, 1000, 100):
        page_num = start_count//100 + 1
        page_soup = bsoup(requests.get(master_url.format(start_count)).text, 'html.parser')
        for block in page_soup.find_all(class_='lister-item mode-advanced'): 
            header_block = block.find('h3')
            title, year = name_year_regex.search(header_block.text).group()
            title = title.strip() 
            partial_url = header_block.find('a').attrs['href']
            movie_imdb_url = f'https://www.imdb.com{partial_url}'

            msg_queue.put(f'IMDB rank scraper on page {page_num}, title: {title} ({year})')
            # feed imdb url and title/year into Queue
            imdb_url_queue.put(movie_imdb_url)
            tomato_json_queue.put(json.dumps({'title': title, 'year': year}))
    # signal scraper to exit
    [(imdb_url_queue.put('exit'), tomato_json_queue.put('exit')) for _ in range(20)]
    return None


def main(): 
    print('script started, asserting selenium driver. Hope you have chrome browser version 86 :-)')
    driver_path = assert_driver()

    imdb_workers = 5
    tomato_workers = 5 
    process_list = []
    message_q_list = []

    imdb_url_queue = Queue()
    tomato_json_queue = Queue()
    # start rank scraper 
    current_queue = Queue() 
    current_process = Process(target=scrape_imdb_rank, 
                                args=(imdb_url_queue, tomato_json_queue, current_queue))
    current_process.start()
    process_list.append(current_process)
    message_q_list.append(current_queue)
    # IMDB scrapers
    for worked_id in range(imdb_url_queue):
        current_queue = Queue() 
        current_process = Process(target=scrape_imdb_movie, 
                                    args=(imdb_url_queue, current_queue, worked_id+1, return_dict, driver_path))
        current_process.start()
        process_list.append(current_process)
        message_q_list.append(current_queue)
    # tomato scrapers
    for worker_id in range(tomato_json_queue):
        current_queue = Queue() 
        current_process = Process(target=scrape_tomato_movie, 
                                    args=(tomato_json_queue, current_queue, worked_id+1, return_dict, driver_path))
        current_process.start()
        process_list.append(current_process)
        message_q_list.append(current_queue)

    report_progress(process_list, message_q_list, [1, imdb_workers, tomato_workers], check_alive=True)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        curses.echo()
        curses.nocbreak()
        curses.endwin()
