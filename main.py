import re 
import os
import json
import pickle
import zipfile 
import platform 
from time import time

import requests 
from bs4 import BeautifulSoup as bsoup 

from scrape_imbd import scrape_imdb_movie
from scrape_tomato import scrape_tomato_movie

from multiprocessing import Process, Queue, Manager


def download_driver():

    master_url = 'https://chromedriver.storage.googleapis.com/86.0.4240.22/chromedriver_'
    if 'Linux' in platform.platform():
        url = f'{master_url}linux64.zip'
    elif 'Windows' in platform.platform():
        url = f'{master_url}win32.zip'
    else:
        url = f'{master_url}mac64.zip'

    driver_file = requests.get(url).content

    with open('temp.zip', 'wb') as fileout:
        fileout.write(driver_file)
    with zipfile.ZipFile('temp.zip', 'r') as filein: 
        file_name = filein.namelist()[0]
        filein.extractall('chromedriver')

    os.remove('temp.zip')
    return f'chromedriver/{file_name}'  


def scrape_imdb_rank(imdb_url_queue, tomato_json_queue, msg_queue):
    name_year_regex = re.compile('[^a-zA-Z]{1,10}([a-zA-Z ]*).*\((\d{4})\)', re.DOTALL)
    master_url = 'https://www.imdb.com/search/title/?groups=top_1000&sort=user_rating,desc&count=100&start={}&ref_=adv_nxt'

    # get 10 pages of 1000 items 
    for start_count in range(1, 1000, 100):
        page_num = start_count//100 + 1
        page_soup = bsoup(requests.get(master_url.format(start_count)).text, 'html.parser')
        for block in page_soup.find_all(class_='lister-item mode-advanced'): 
            header_block = block.find('h3')
            title, year = name_year_regex.search(header_block.text).groups()
            title = title.strip() 
            partial_url = header_block.find('a').attrs['href']
            movie_imdb_url = f'https://www.imdb.com{partial_url}'

            msg_queue.put(f'IMDB rank scraper on page {page_num}, title: {title} ({year})')
            # feed imdb url and title/year into Queue
            imdb_url_queue.put(movie_imdb_url)
            tomato_json_queue.put(json.dumps({'title': title, 'year': year}))
    # signal scraper to exit
    [(imdb_url_queue.put('exit'), tomato_json_queue.put('exit')) for _ in range(10)]
    return None


def main(): 
    print('script started, asserting selenium driver.')
    driver_path = download_driver()

    imdb_workers = 0
    tomato_workers = 2
    process_list = []
    message_q_list = []

    result_manager = Manager()
    return_dict = result_manager.dict()

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
    for worker_id in range(imdb_workers):
        current_queue = Queue() 
        current_process = Process(target=scrape_imdb_movie, 
                                    args=(imdb_url_queue, current_queue, worker_id+1, return_dict, driver_path))
        current_process.start()
        process_list.append(current_process)
        message_q_list.append(current_queue)
    # tomato scrapers
    for worker_id in range(tomato_workers):
        current_queue = Queue() 
        current_process = Process(target=scrape_tomato_movie, 
                                    args=(tomato_json_queue, current_queue, worker_id+1, return_dict, driver_path))
        current_process.start()
        process_list.append(current_process)
        message_q_list.append(current_queue)

    report_progress(process_list, message_q_list, [1, imdb_workers, tomato_workers], check_alive=True, sleep_time=100)

    with open('temp_file_storage', 'wb') as fileout:
        pickle.dump(return_dict, fileout)


if __name__ == '__main__':

    if 'Windows' in platform.platform():
        print('Warning, you are running this on Windows platform.')
        print('The script will still run, but curses is not supported by Windows')
        print('You lose the ability to monitor scraping progress.\n')
        
        def report_progress(*kwargs):
            pass

    else:
        print('I\'m glad you\'re not on windows, everything will work fine.')
        print('As long as you have Chrome versoin 85 or 86. Earlier version supportis not gaurenteed')
        import curses 
        from report_progress import report_progress

    try:
        main()
    except KeyboardInterrupt:
        curses.echo()
        curses.nocbreak()
        curses.endwin()
    
