# DS320_Scrape_and_Integrate_Project

## Websites 
    1. IMDB 
    2. rotten tomato 

## Packages: 
* requests 
* bs4 
* selenium 
* nltk
* collections
* multiprocessing 

## Data Source Description: 

    For this project, we are interested in how movie information is recorded on different website. We 
    acquired a movie rank list on IMDB that contains the most popular 1000 movies base on user review. 
    
    The list contains movie's title, year and a link to its IMDB webpage. We navigate into the IMDB 
    webpage to collect more detail information such as genre, rating, number of reviews and box gross. 
    We are also interested in the reviews of each movie. We extract the most frequent five words in all 
    the reviews, and named them review_word_1, review_word_2, review_word_3, review_word_4, review_word_5
     in the final data table. 

    We then use the title and year information extracted from the IMDB rank list to search google and 
    navigate to its rotten tomato website and collect genre, rating, rating_count, box gross, reviews. 
    And just like on IMDB, we extracted the most frequent five words in the reviews and named them 
    review_word_1, review_word_2, review_word_3, review_word_4, review_word_5. 

## Matching objective: 

    IMDb and rotten tomato all have the same information, but it has different column names and even data 
    types. We'd like to match them so better compare them. 

    * rank from IMDB matches to rank from Rotten Tomatoes
    * title from IMDB matches to title from Rotten Tomatoes
    * year from IMDB matches to year from Rotten Tomatoes
    * genre from IMDB matches to genre from Rotten Tomatoes
    * rating_score from IMDB matches to rating from Rotten Tomatoes
    * reviews from IMDB matches to reviews from Rotten Tomatoes
    * box gross from IMDB matches to us_box_gross from Rotten Tomatoes
    * review_word_1 from IMDB matches to review_word_1 from Rotten Tomatoes
    * review_word_2 from IMDB matches to review_word_2 from Rotten Tomatoes
    * review_word_3 from IMDB matches to review_word_3 from Rotten Tomatoes
    * review_word_4 from IMDB matches to review_word_4 from Rotten Tomatoes
    * review_word_5 from IMDB matches to review_word_5 from Rotten Tomatoes

## Collaboration: 

    Jinhan Li proposed the topics and researched on the data sources used in the project. Then both of us 
    discussed and decided which specific information to scrape from each site. 
    
    Jinhan Li wrote and tested IMDB scraper (scrapers/scrape_imdb.py) and the data aggregation in main.py

    Yuhan Hsi wrote and tested the multiprocess framework (main.py), the monitoring tool 
    (utils.report_progress.py), the proxy generator (utils.proxy_generator.py) and the 
    tomato scraper (scrapers/scrape_tomato.py)
        
    Jinhan Li wrote the draft for the report and Yuhan Hsi edited and finalized it.

## Code Description: 

    main.py is the starting point of the entire process. It will first download and unzip a selenium 
    webdriver for chrome 86. Then spawn a process to scrape the IMDb rank page. After that, it looks 
    at the configurations in packages and spawn desired amount of IMDB and rotten tomato scrapers.
    Then (in linux only) it hands the job over to utils.report_progress, which you can monitor the 
    progress of each process. 

    scrapers.scrape_imdb.py collects each movie's imdb_url from its Queue and use bs4 to scrape basic 
    information.It then use selenium to collect the top 100 movie reviews, clean it and count the top 
    5 words to record. All movie's information will be dumped into individual files as soon as the 
    scraping process completes. Note that the use of selenium is absolutely neccessary because 
    the movie review page seems to be load dynamically by JS while its url remains unchanged. 

    scrapers.scrape_tomato.py collects each movie's year and title from its Queue then use selenium and google 
    to search for movie of said year and name on www.rottentomato.com. We then filter the search result 
    base on result citation (rottentomato.com), movie name and movie year. However, we discovered that 
    there are inconsistency when it comes to release year, thus we decided to include ±2 years when filtering. 
    When desired movie is found, selenium clicks on it and nagivate to the rottentomato website to collect 
    basic information. After which it goes to the review page to collect, clean and count top 5 words in 
    first 100 reviews. The movie reviews are also dynamically loaded by JS. 

    utils.report_progress.py is responsible to generate multi-line report from terminal. It collects message 
    sent from different process then compile them into the screen. The screen also refresh every 2 minutes 
    because bugs will overwrite the messages. It also has a restart feature, when the amount of process that 
    exists abnormally exceeds a certain limit, the script will terminate all process and signal the main process
    to restart the script. This feature, however is only supported on Linux. the package curses is not nativly 
    supported on windows, and Mac also cannot use this script because multiprocessing.Queue have not 
    implemented methods. 

    utils.generate_ptoxy.py is responsible to generate selenium driver with proxy and proxy address for bs4. The 
    proxies used are free and collected from the internet. 

## Scrape result: 

    The two result csvs are submitted on canvas seperatly.