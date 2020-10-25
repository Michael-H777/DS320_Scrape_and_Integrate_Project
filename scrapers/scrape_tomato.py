from utils.packages import *
from utils.proxy_generator import driver_object


def clean_gross_string(input_string):
    with open('tomato_gross_text', 'a') as fileout: 
        fileout.write(f'{input_string}\n') if 'M' not in input_string else None
    
    return input_string

    result = ''
    if 'M' in input_string:
        result = ''.join(list(filter(lambda item: item.isdigit() or item=='.', input_string)))
    return result 


def clean_genre_string(input_string):
    input_list = input_string.split() 
    cleaned_list = list(filter(lambda item: len(item)>1, input_list))
    return ', '.join(cleaned_list)


def log_in(driver):
    log_in_hidden = driver.find_elements_by_class_name('modal fade')
    log_in_hidden = any(item.get_attribute('id')=='login' and 
                        item.get_attribute('style')=='display: none;' for item in log_in_hidden)

    # if prompted to log in 
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
        
    return None 


def count_user_review(review_url, msg_head, msg_queue, driver_generator, stop_words):
    
    retry_counter = count(1)
    place_holder = ['1', '2', '3', '4', '5']
    result_counter = Counter(place_holder)
    while True: 
        
        driver = driver_generator.get(review_url)
        
        if driver is False: 
            retry = next(retry_counter)
            msg_queue.put(f'{msg_head}triggered anti-scrape when scraping review, switching IP, retry: {retry}')
            continue 
        
        # 10 reviews per page 
        total_pages = 10
        for page_num in range(total_pages):
            sleep(randint(30, 70)/10)

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
                next_button[0].click()
            else:
                break 

        driver.quit()
        return result_counter


def scrape_tomato_movie(movie_json_queue, msg_queue, worker_id, driver_path):
    # tomato things need to be searched, need clicking and redirecting
    driver_generator = driver_object(driver_path)
    
    # google search templet
    search_templet = 'https://www.google.com/search?q=rottentomatoes.com%3A+{}'

    stop_words = set(stopwords.words('english'))
    # report progress
    msg_head = f'scraper {worker_id:>2} for rotten tomato '
    meta_data_str = movie_json_queue.get(block=True)

    # record df
    scrape_columns = ['rank', 'title', 'year', 'genre', 'rating', 'rating_count', 'box gross', 
                        'review_word_1', 'review_word_2', 'review_word_3', 'review_word_4', 'review_word_5']
    
    retry_counter = count(1)
    
    while meta_data_str != 'exit':

        meta_data = json.loads(meta_data_str)
        rank, title, year = meta_data.values()         
        msg_queue.put(f'{msg_head}url of movie no.{rank:>2} retrieved, waiting for response')
        # we need ot use google search, rottentomatoes have shadow-root
        # things within can't be accessed with scraper, bsoup or selenium 
        title_cleaned = re.sub('[^\s\w]', '', title)
        search_url = search_templet.format('+'.join([*title_cleaned.split(), year]))
        driver = driver_generator.get(search_url)
        
        if driver is False:
            retry = next(retry_counter)
            msg_queue.put(f'{msg_head}triggered anti-scrape, switching IP, retry: {retry}')
            continue
        
        for block, citation in zip(driver.find_elements_by_tag_name('h3'), driver.find_elements_by_tag_name('cite')):
            # get title text and website source for clicking 
            title_texts = title_cleaned.split() 
            block_texts = re.sub('[^\s\w]', '', block.text).split() 
            if all(item in block_texts for item in title_texts) and year in block_texts and 'www.rottentomatoes.com' in citation.text: 
                block.find_element_by_tag_name('span').click()
                break
        # if did not find suitable result, continue while loop 
        else:
            driver.quit()
            retry = next(retry_counter)
            meta_data_str = movie_json_queue.get(block=True) if retry > 500 else meta_data_str
            continue 

        sleep(10)
        if not driver_generator.valida_response: 
            sleep(1)
            driver.quit() 
            retry = next(retry_counter)
            msg_queue.put(f'{msg_head}triggered anti-scrape, switching IP, retry: {retry}')
            continue 

        # basic info 
        try:
            movie_soup = bsoup(driver.page_source, 'html.parser')
            rating_str = movie_soup.find(class_='mop-ratings-wrap__percentage').text.strip()
            rating_count_str = movie_soup.find_all(class_='mop-ratings-wrap__text--small')[2].text
            rating_value = int(''.join(list(filter(lambda item: item.isdigit(), rating_str)))) / 100
            rating_count = int(''.join(list(filter(lambda item: item.isdigit(), rating_count_str))))
        except:
            driver.quit()
            continue 
        
        # genre and gross 
        genre = gross_usa = '' 
        for info_block in movie_soup.find_all(class_='meta-row clearfix'):
            if 'Genre' in info_block.text: 
                genre_dirty = info_block.find(class_='meta-value genre').text
                genre = clean_genre_string(genre_dirty)
            elif 'Gross USA' in info_block.text: 
                gross_usa_dirty = info_block.find(class_='meta-value').text
                gross_usa = clean_gross_string(gross_usa_dirty)

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
        retry_counter = count(1)

    driver.quit()
    msg_queue.put(f'{msg_head}job completed, result returned, process terminated')

    return None 
