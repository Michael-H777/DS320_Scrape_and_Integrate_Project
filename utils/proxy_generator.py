from utils.packages import *


class driver_object:
    
    blocks = ['This site can’t be reached', 'This page isn’t working', 'No internet', 'Access Denied', 
                'Error 503', 'Our systems have detected unusual traffic from your computer network']
    
    def __init__(self, driver_path):
        self.driver_path = driver_path 
        self.generate_proxy = self.get_proxy() 
        self.generate_proxy_driver = self.get_proxy_drivers()

    def get_proxy(self): 
        while True: 
            with open('proxies.txt', 'r') as filein: 
                proxies = filein.read().split('\n')
            # shuffle is in-place
            shuffle(proxies)
            for address in proxies: 
                yield address 

    def get_proxy_drivers(self):
        
        if master_use_proxy:
            while True: 
                address = next(self.generate_proxy)
                
                # proxy settings for selenium 
                current_proxy = Proxy() 
                current_proxy.proxy_type = ProxyType.MANUAL 
                current_proxy.http_proxy = address 
                current_proxy.ssl_proxy = address
                capabilities = webdriver.DesiredCapabilities.CHROME
                current_proxy.add_to_capabilities(capabilities)
                # headless setting for selenium 
                options = webdriver.ChromeOptions()
                options.add_argument('--headless') if master_use_headless else None 
                options.add_argument("--disable-dev-shm-usage")

                driver = webdriver.Chrome(executable_path=self.driver_path, chrome_options=options, desired_capabilities=capabilities)
                driver.set_page_load_timeout(120)
                yield driver
        else:
            while True:
                sleep(randint(10, 30) / 10)
                options = webdriver.ChromeOptions()
                options.add_argument('--headless') if master_use_headless else None 
                options.add_argument("--disable-dev-shm-usage")

                driver = webdriver.Chrome(executable_path=self.driver_path, chrome_options=options)
                driver.set_page_load_timeout(120)
                yield driver
        

    @property
    def valida_response(self):
        # text indicating that proxy is blocked 
        page_text = bsoup(self.driver.page_source, 'html.parser').text
        if any(item in page_text for item in driver_object.blocks):
            self.driver.quit()
            return False 
        # reload button from chrome where site not loaded
        else:
            return True
        
    def get(self, url): 
        self.driver = next(self.generate_proxy_driver)
        
        # error when getting the webpage 
        try:
            self.driver.get(url)
        except:
            sleep(2)
            self.driver.quit()
            return False 
        sleep(10)
        # successfully retrieved webpage, but content blocked 
        if self.valida_response:
            return self.driver
        else:
            return False
