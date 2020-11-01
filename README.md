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

    For this project, we are interested in how movie information is recorded on different 
    website. We aquired a movie rank list on IMDB that contains the most populat 1000 movies base 
    on user review. 
    
    The list contains movie's title, year and a link to its IMDB webpage. We navigate into the 
    IMDB webpage to collect more detail information such as genre, rating, number of reviews and
    box gross. We are also interested in the reviews of each movie. We extract the most frequent 
    five words in all the reviews, and named them review_word_1, review_word_2, review_word_3,
    review_word_4, review_word_5 in the final data table. 

    We then use the title and year information extracted from the IMDB rank list to search google 
    and navigate to its rotten tomato website and collect genre, rating, rating_count, box gross, 
    reviews. And just like on IMDB, we extracted the most frequent five words in the reviews and 
    named them review_word_1, review_word_2, review_word_3, review_word_4, review_word_5. 

## Matching objective: 

    IMDb and rotten tomato all have the same information, but it has different column names 
    and even data types. We'd like to match them so better compare them. 

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

    Jinhan Li proposed the topics and researched on the data sources used in the project. Then 
    both of us discussed and decided which specific information to scrape from each site. 
    
    Jinhan Li wrote and tested IMDB scraper (scrapers/scrape_imdb.py) and the data aggregation in
     main.py

    Yuhan Hsi wrote and tested the multiprocess framework (main.py), the monitoring tool 
    (utils.report_progress.py), the proxy generator (utils.proxy_generator.py) and the 
    tomato scraper (scrapers/scrape_tomato.py)
        
    Jinhan Li wrote the draft for the report and Yuhan Tsi edited and finalized it.

