from utils.packages import *
from utils.proxy_generator import driver_object


def clean_genre_string(input_string):
    input_list = input_string.split() 
    cleaned_list = list(filter(lambda item: len(item)>2 and item!='and', input_list))
    cleaned_list = [''.join(list(filter(lambda char: char.isalpha(), item))) for item in cleaned_list]
    cleaned_list.sort()
    return ', '.join(cleaned_list)


def clean_word(word):
    return ''.join([char for char in word if char.isalpha()]).lower()


def count_user_review(review_url, msg_head, msg_queue, driver_generator, stop_words):
    
    retry_counter = count(1)
    retry = next(retry_counter)
    result_counter = Counter()
    
    while len(result_counter)==0 and retry<retry_cut_off: 
        
        driver = driver_generator.get(review_url)
        retry = next(retry_counter)
        if driver is False: 
            msg_queue.put(f'{msg_head}triggered anti-scrape when scraping review, switching IP, retry: {retry}')
            continue 

        # 10 reviews per page 
        total_pages = 10
        for page_num in range(total_pages):
            sleep(15)
            # collect all reviews 
            for review_block in driver.find_elements_by_class_name('audience-reviews__item'): 
                current_review = review_block.find_element_by_tag_name('p').text 
                current_review_raw = [clean_word(word) for word in word_tokenize(current_review)]
                current_review_cleaned = [word for word in current_review_raw if word not in stop_words and len(word)>3]
                result_counter += Counter(current_review_cleaned)
            
            msg_queue.put(f'{msg_head}, page {page_num+1}/{total_pages}')
            # find next buttons 
            next_button = driver.find_elements_by_class_name('prev-next-paging__button-text')
            next_button = list(filter(lambda item: item.text=='NEXT', next_button))
            if next_button: 
                # click on next page
                try:
                    next_button[0].click()
                except ElementNotInteractableException:
                    break
            else:
                break 

    if not isinstance(driver, bool): 
        driver.quit()
    return result_counter + Counter('12345')


def scrape_tomato_movie(movie_json_queue, msg_queue, worker_id, driver_path):
    # tomato things need to be searched, need clicking and redirecting
    driver_generator = driver_object(driver_path)
    
    # google search templet
    search_templet = 'https://www.google.com/search?q=rottentomatoes.com%3A+{}'

    # stop words for review cleaning 
    stop_words = set(stopwords.words('english'))
    stop_words.update(custom_stop_words)
    
    # report progress
    msg_head = f'scraper {worker_id:>2} for rotten tomato '
    meta_data_str = movie_json_queue.get(block=True)
    msg_queue.put(f'{msg_head}started, waiting for response')

    # record df
    scrape_columns = ['rank', 'title', 'year', 'genre', 'user_rating', 'rating_count', 'us_gross_box', 
                        'review_word_1', 'review_word_2', 'review_word_3', 'review_word_4', 'review_word_5']
    
    retry_counter = count(1)
    # sometimes we want to use local driver for google search 
    while meta_data_str != 'exit':

        meta_data = json.loads(meta_data_str)
        rank, title, year = meta_data.values()
        
        file_name = f'tomato_{rank}.csv'
        if file_name in os.listdir('results/'):
            retry_counter = count(1)
            meta_data_str = movie_json_queue.get(block=True)
            continue 

        # we need to use google search, rottentomatoes have shadow-root
        # things within can't be accessed with scraper, bsoup or selenium 
        title_cleaned = re.sub('[^\s\w]', '', title)
        search_url = search_templet.format('+'.join([*title_cleaned.split(), year]))
        driver = driver_generator.get(search_url)
        
        if driver is False:
            retry = next(retry_counter)
            if retry > retry_cut_off:
                retry_counter = count(1)
                meta_data_str = movie_json_queue.get(block=True)
            msg_queue.put(f'{msg_head}triggered anti-scrape, switching IP, retry: {retry}')
            continue

        page_blocks = driver.find_elements_by_tag_name('h3')
        page_citations = driver.find_elements_by_tag_name('cite')
        for block, citation in zip(page_blocks, page_citations):
            # get title text and website source for clicking 
            title_texts = [item.lower() for item in title_cleaned.split() if item.isalpha()]
            block_texts = block.text.lower()
            year = int(year)
            year_grace = [str(item) for item in [year-2, year-1, year, year+1, year+2]]
            if ('www.rottentomatoes.com' in citation.text.lower()) and \
                    all(item in block_texts for item in title_texts) and \
                            any(item in block_texts for item in year_grace): 
                block.find_element_by_tag_name('span').click()
                break
        # if did not find suitable result, continue while loop 
        else:
            driver.quit()
            retry = next(retry_counter)
            if retry > retry_cut_off:
                retry_counter = count(1)
                meta_data_str = movie_json_queue.get(block=True)
            msg_queue.put(f'{msg_head}google search did not find movie {title}, going next')
            continue 

        sleep(10)
        # page did not load properly 
        if not driver_generator.valida_response: 
            sleep(1)
            driver.quit() 
            retry = next(retry_counter)
            if retry > retry_cut_off:
                retry_counter = count(1)
                meta_data_str = movie_json_queue.get(block=True)
            msg_queue.put(f'{msg_head}tomato failed to load, switching IP, retry: {retry}')
            continue 
        
        msg_queue.put(f'{msg_head}loaded page for {title}, scraping info')
        # basic info 
        rating_value = rating_count = ''
        movie_soup = bsoup(driver.page_source, 'html.parser')
        rating_str = movie_soup.find_all(class_='mop-ratings-wrap__percentage')
        if rating_str: 
            rating_value = ''.join(list(filter(lambda item: item.isdigit(), rating_str[0].text.strip())))
        if isinstance(rating_str, str) and rating_str.isdigit(): 
            rating_str = int(rating_str) / 100
        
        rating_count_str = movie_soup.find_all(class_='mop-ratings-wrap__text--small')
        if rating_count_str: 
            rating_count_str = [item.text.strip() for item in rating_count_str]
            rating_count_str = [item for item in rating_count_str if 'user ratings' in item.lower()]
            rating_count = ''.join(list(filter(lambda item: item.isdigit(), rating_count_str[0]))) if rating_count_str else ''
    
        # genre and gross 
        genre = gross_usa = '' 
        for info_block in movie_soup.find_all(class_='meta-row clearfix'):
            if 'Genre' in info_block.text: 
                genre_dirty = info_block.find(class_='meta-value genre')
                genre = clean_genre_string(genre_dirty.text) if genre_dirty else ''
            elif 'Gross USA' in info_block.text: 
                gross_usa = info_block.find(class_='meta-value').text

        msg_queue.put(f'{msg_head}completed basic info of {rank}. {title}, working on user_review')
        # user_review 
        user_review_url = f'{driver.current_url}'
        user_review_url += f'{"" if user_review_url.endswith("/") else "/"}reviews?type=user'
        current_msg_head = f'{msg_head}working on {rank}. {title} '
        user_review_counter = count_user_review(user_review_url, current_msg_head, msg_queue, driver_generator, stop_words)
        word_count = list(user_review_counter.items())
        word_count.sort(key=lambda item: item[1], reverse=True)
        top_words = [item[0] for item in word_count[:5]]

        # record scrape result
        result_list = [[rank, title, year, genre, rating_value, rating_count, gross_usa, *top_words]]
        movie_result = pd.DataFrame(columns=scrape_columns, data=result_list)
        movie_result.to_csv(f'results/tomato_{rank}.csv', index=False)

        # go to next movie 
        driver.quit()
        meta_data_str = movie_json_queue.get(block=True)
        msg_queue.put(f'{msg_head}retrieved new movie {rank}. {title},  waiting for response')
        retry_counter = count(1)

    if not isinstance(driver, bool):
        driver.quit()
    msg_queue.put(f'{msg_head}job completed, process terminated')

    return None 
