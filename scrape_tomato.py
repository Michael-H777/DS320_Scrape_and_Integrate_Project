from packages import *


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


def scrape_tomato_movie(movie_json_queue, msg_queue, worker_id, driver_path):
    # tomato things need to be searched, need clicking and redirecting
    options = webdriver.ChromeOptions()
    # headless mode will not run on any platform
    #options.add_argument('--headless')
    driver = webdriver.Chrome(executable_path=driver_path, options=options)
    search_templet = 'https://www.google.com/search?q=rottentomatoes.com%3A+{}'

    stop_words = set(stopwords.words('english'))
    # report progress
    msg_head = f'scraper {worker_id:>2} for rotten tomato '
    msg_queue.put(f'{msg_head}started, waiting for url')
    meta_data_str = movie_json_queue.get(block=True)

    # record df
    scrape_columns = ['rank', 'title', 'year', 'genre', 'rating', 'rating_count', 'box gross', 
                        'review_word_1', 'review_word_2', 'review_word_3', 'review_word_4', 'review_word_5']
    master_result = pd.DataFrame(columns=scrape_columns)
    
    while meta_data_str != 'exit':
        meta_data = json.loads(meta_data_str)
        rank, title, year = meta_data.values() 
        # we need ot use google search, rottentomatoes have shadow-root
        # things within can't be accessed with scraper, bsoup or selenium 
        title_cleaned = re.sub('[^\s\w]', '', title)
        search_url = search_templet.format('+'.join([*title_cleaned.split(), year]))
        driver.get(search_url)
        sleep(2)
        for block, citation in zip(driver.find_elements_by_tag_name('h3'), driver.find_elements_by_tag_name('cite')):
            
            title_texts = title_cleaned.split() 
            block_texts = re.sub('[^\s\w]', '', block.text).split() 
            if  all(item in block_texts for item in title_texts) and year in block_texts and 'www.rottentomatoes.com' in citation.text: 
                block.find_element_by_tag_name('span').click()
                break
        else:
            meta_data_str = movie_json_queue.get(block=True)
            result_list = [rank, title, year, '', '', '', '', '', '', '', '', '']
            current_result = {key:value for key, value in zip(scrape_columns, result_list)}
            master_result = master_result.append(current_result, ignore_index=True)
            continue 
        
        sleep(5)

        # rotten tomato is the single most difficult website to deal with 
        movie_soup = bsoup(driver.page_source, 'html.parser')
        rating_str = movie_soup.find(class_='mop-ratings-wrap__percentage').text.strip()
        rating_count_str = movie_soup.find_all(class_='mop-ratings-wrap__text--small')[2].text
        rating_value = int(''.join(list(filter(lambda item: item.isdigit(), rating_str)))) / 100
        rating_count = int(''.join(list(filter(lambda item: item.isdigit(), rating_count_str))))

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
        current_msg_head = f'{msg_head}working on {rank}. {title}'
        user_review_counter = count_user_review(user_review_url, current_msg_head, msg_queue, driver, stop_words)
        word_count = list(user_review_counter.items())
        word_count.sort(key=lambda item: item[1], reverse=True)
        top_words = [item[0] for item in word_count[:5]]

        # record scrape result
        result_list = [rank, title, year, genre, rating_value, rating_count, gross_usa, *top_words]
        current_result = {key:value for key, value in zip(scrape_columns, result_list)}
        master_result = master_result.append(current_result, ignore_index=True)

        # go to next movie 
        meta_data_str = movie_json_queue.get(block=True)

    driver.quit()
    # windows does not support Manager().dict() to return value from child-process to main-process
    master_result.to_csv(f'tomatoes/tomatoes_{worker_id}.csv', index=False)
    msg_queue.put(f'{msg_head}job completed, result returned, process terminated')

    return None 
