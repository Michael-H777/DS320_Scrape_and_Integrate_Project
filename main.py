from utils.packages import *

from utils.report_progress import EmergencyRestart
from scrapers.scrape_imbd import scrape_imdb_movie
from scrapers.scrape_tomato import scrape_tomato_movie


def check_platform():
    platform_info = platform.platform() 
    if 'Linux' in platform_info: 
        return 'linux'
    elif 'Windows' in platform_info:
        return 'windows'
    else:
        return 'mac'


def download_driver():
    return 'chromedriver/chromedriver'
    
    v85 = '85.0.4183.87'
    v86 = '86.0.4240.22'
    file_ending = {'linux': 'linux64.zip', 'windows': 'win32.zip', 'mac': 'mac64.zip'}
    url = f'https://chromedriver.storage.googleapis.com/{v86}/chromedriver_{file_ending[check_platform()]}'

    driver_file = requests.get(url).content

    with open('temp.zip', 'wb') as fileout:
        fileout.write(driver_file)
    with zipfile.ZipFile('temp.zip', 'r') as filein: 
        file_name = filein.namelist()[0]
        filein.extractall('chromedriver')

    os.remove('temp.zip')
    return f'chromedriver/{file_name}'  


def scrape_imdb_rank(imdb_json_queue, tomato_json_queue, msg_queue):
    master_url = 'https://www.imdb.com/search/title/?groups=top_1000&sort=user_rating,desc&count=100&start={}&ref_=adv_nxt'

    # get 10 pages of 1000 items 
    for start_count in range(1, 1000, 100):
        page_num = start_count//100 + 1
        page_soup = bsoup(requests.get(master_url.format(start_count)).text, 'html.parser')
        for block in page_soup.find_all(class_='lister-item mode-advanced'): 
            # get basic info 
            header_block = block.find('h3')
            rank, title, year = list(filter(lambda item: len(item), header_block.text.split('\n')))
            rank = ''.join(list(filter(lambda item: item.isdigit(), rank)))
            year = ''.join(list(filter(lambda item: item.isdigit(), year)))
            title = title.strip() 
            # partial imdb url for  imdb scraper 
            partial_url = header_block.find('a').attrs['href']
            movie_imdb_url = f'https://www.imdb.com{partial_url}'

            msg_queue.put(f'IMDB rank scraper on page {page_num}, rank: {rank}, title: {title} ({year})')
            # feed imdb url and title/year into Queue
            imdb_json_queue.put(json.dumps({'rank': rank, 'title':title, 'url': movie_imdb_url}))
            tomato_json_queue.put(json.dumps({'rank': rank, 'title': title, 'year': year}))
    # signal scraper to exit
    [(imdb_json_queue.put('exit'), tomato_json_queue.put('exit')) for _ in range(100)]
    msg_queue.put(f'IMDB rank scraper job completed, terminate signal sent')
    return None


def main(): 
    print('script started, asserting selenium driver.')
    driver_path = download_driver()
    
    imdb_workers = 0
    tomato_workers = 1
    process_list = []
    message_q_list = []

    imdb_json_queue = Queue()
    tomato_json_queue = Queue()
    # start rank scraper 
    current_queue = Queue() 
    current_process = Process(target=scrape_imdb_rank, 
                                args=(imdb_json_queue, tomato_json_queue, current_queue))
    current_process.start()
    process_list.append(current_process)
    message_q_list.append(current_queue)
    # IMDB scrapers
    for worker_id in range(imdb_workers):
        current_queue = Queue() 
        current_process = Process(target=scrape_imdb_movie, 
                                    args=(imdb_json_queue, current_queue, worker_id+1, driver_path))
        current_process.start()
        process_list.append(current_process)
        message_q_list.append(current_queue)

    # tomato scrapers
    for worker_id in range(tomato_workers):
        current_queue = Queue() 
        current_process = Process(target=scrape_tomato_movie, 
                                    args=(tomato_json_queue, current_queue, worker_id+1, driver_path))
        current_process.start()
        process_list.append(current_process)
        message_q_list.append(current_queue)

    report_progress(process_list, message_q_list, [1, imdb_workers, tomato_workers], result_dir='results', 
                        clear_screen=True, check_alive=True, restart=10, sleep_time=100)
    ## IMPLEMENT RESULT INTEGRATION


if __name__ == '__main__':

    current_platform = check_platform()

    if current_platform == 'linux':
        print('\nI\'m glad you\'re on Linux, the script is developed on it and is tested extensivly.')
        print('Everything will run as long as you have Chrome versoin 86.')
        print('Selenium driver download path for Chrome 85 is included, modify function download_driver for 85.')
        import curses 
        from utils.report_progress import report_progress
        

    elif current_platform == 'windows':
        print('\nWarning, you are running this on Windows platform.')
        print('The script will still run, but curses is not supported natively by Windows')
        print('You lose the ability to monitor scraping progress.\n')

        def report_progress(process_list, *args, **kwargs):
            [item.join for item in process_list]
            return None
    else:
        print('\nMac is tricky, some functions in multiprocess.Queue is not implemented and there\'s nothing I can do about that')
        print('Script is not gaurenteed to run even with modification, please switch to linux or windows')
        
        def report_progress(process_list, *args, **kwargs):
            [item.join for item in process_list]
            return None

    if not os.path.exists('results'):
        os.mkdir('results/')
    
    while True:
        try:
            main()
        except EmergencyRestart:
            os.system('killall chrome*')
            sleep(180)
            curses.echo()
            curses.nocbreak()
            curses.endwin()
            continue 
        except KeyboardInterrupt:
            curses.echo()
            curses.nocbreak()
            curses.endwin()
        break
    
