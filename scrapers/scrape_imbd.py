from utils.packages import *
from utils.proxy_generator import driver_object

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


def clean_word(word):
    return ''.join([char for char in word if char.isalpha()])


def scrape_imdb_review(review_url, msg_head, msg_queue, driver_generator, stop_words):
    expand_icon_regex = re.compile('expander-icon-wrapper.*')
    review_block_regex = re.compile('lister-item mode-detail imdb-user-review.*')

    retry_counter = count(1)
    place_holder = ['1', '2', '3', '4', '5']
    result_counter = Counter(place_holder)

    while True:
        
        driver = driver_generator.get(review_url)
        
        if driver is False: 
            retry = next(retry_counter)
            msg_queue.put(f'{msg_head}triggered anti-scrape when scraping review, switching IP, attempt {retry}')
            continue 

        msg_queue.put(f'{msg_head}clicking on show more')
        # 25 reviews per click
        for _ in range(4):
            sleep(1)
            try:
                driver.find_element_by_class_name('ipl-load-more__button').click()
            except NoSuchElementException:
                sleep(5)
                continue
            except ElementNotInteractableException: 
                break                
        
        # collect reviews 
        for block in driver.find_elements_by_class_name('lister-list'):
            review_text = block.find_element_by_class_name('content').text
            review_text_raw = [clean_word(word) for word in word_tokenize(review_text)]
            review_text_cleaned = [word for word in review_text_raw if word not in stop_words and len(word)>3]
            result_counter += Counter(review_text_cleaned)

        driver.quit()
        return result_counter 


def scrape_imdb_movie(movie_json_queue, msg_queue, worker_id, driver_path):
    # IMDB reviews have spoiler and show_more control, needs clicking 
    driver_generator = driver_object(driver_path)
    
    # regexs 
    title_regex = re.compile(u'^(.*)\xa0')
    gross_usa_regex = re.compile('Gross USA.*\$(.*)')
    review_link_regex = re.compile('.*reviews')
    stop_words = set(stopwords.words('english'))

    # report progress
    msg_head = f'scraper {worker_id:>2} for IMDB '
    movie_json_str = movie_json_queue.get(block=True)

    # record df
    scrape_columns = ['rank', 'title', 'year', 'genre', 'rating', 'rating_count', 'box gross', 
                        'review_word_1', 'review_word_2', 'review_word_3', 'review_word_4', 'review_word_5']
    
    retry_counter = count(1)
    while movie_json_str != 'exit':
        movie_result = pd.DataFrame(columns=scrape_columns)
        proxy_address = next(driver_generator.generate_proxy)
        
        rank, title, movie_url = json.loads(movie_json_str).values()
        proxy_param = {'http': proxy_address, 'https':proxy_address}
        
        msg_queue.put(f'{msg_head}url of movie no.{rank:>2} retrieved, waiting for response')
        try:
            movie_soup = bsoup(requests.get(movie_url, proxies=proxy_param, timeout=10).text, 'html.parser')
        except: 
            retry = next(retry_counter)
            msg_queue.put(f'{msg_head}proxy error on movie no.{rank}, switching IP, attempt {retry}')
            continue 

        if 'access denied' in movie_soup.text:
            continue 
        
        # collect title, year, genre 
        info_block = movie_soup.find(class_='title_wrapper')
        #title = title_regex.search(info_block.find('h1').text).group(1)
        block_text = [item.text for item in info_block.find_all('a')]
        year, genre = process_info_block(block_text)

        # collect rating and rating_count
        rating_value = float(movie_soup.find('span', attrs={'itemprop': 'ratingValue'}).text)
        rating_count_str = movie_soup.find('span', attrs={'itemprop': 'ratingCount'}).text
        rating_count = ''.join([item if item.isdigit() else '' for item in rating_count_str])

        # collect box gross USA
        gross_block = list(filter(lambda item: 'Gross USA' in str(item), movie_soup.find_all(class_='txt-block')))
        if gross_block:
            gross_usa_str = gross_usa_regex.search(gross_block[0].text).group(1)
            gross_usa = ''.join([item if item.isdigit() else '' for item in gross_usa_str])
        else:
            gross_usa = ''

        msg_queue.put(f'{msg_head}finished basic info on {rank}. {title}, working on user_review')
        # retrieve review link and user reviews
        review_partial_url = movie_soup.find('a', attrs={'href': review_link_regex}).attrs['href']
        review_url = f'https://www.imdb.com{review_partial_url}'
        current_msg_head = f'{msg_head} working on {rank}. {title} '
        user_review_counter = scrape_imdb_review(review_url, current_msg_head, msg_queue, driver_generator, stop_words)
        word_count = list(user_review_counter.items())
        word_count.sort(key=lambda item: item[1], reverse=True)
        top_words = [item[0] for item in word_count[:5]]

        # record scrape result
        result_list = [[rank, title, year, genre, rating_value, rating_count, gross_usa, *top_words]]
        movie_result = pd.DataFrame(columns=scrape_columns, data=result_list)
        movie_result.to_csv(f'results/IMDB_{rank}.csv', index=False)

        msg_queue.put(f'{msg_head}finished scraping {rank}. {title}')
        retry_counter = count(1)
        # get next url 
        movie_json_str = movie_json_queue.get(block=True)

    # windows does not support Manager().dict() to return value from child-process to main-process
    msg_queue.put(f'{msg_head}job completed, result returned, process terminated')
    return None 

