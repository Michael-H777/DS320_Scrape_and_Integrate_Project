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

    def get_local_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        self.driver = webdriver.Chrome(executable_path=self.driver_path, chrome_options=options)
        return self.driver
    
    def get_proxy_drivers(self):
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
            options.add_argument('--headless')
            options.add_argument("--disable-dev-shm-usage")

            driver = webdriver.Chrome(executable_path=self.driver_path, chrome_options=options , desired_capabilities=capabilities)
            driver.set_page_load_timeout(120)
            yield driver

    @property
    def valida_response(self):
        # text indicating that proxy is blocked 
        if any(item in self.driver.page_source for item in driver_object.blocks):
            return False 
        # reload button from chrome where site not loaded
        elif bsoup(self.driver.page_source, 'html.parser').find(id='reload-button'):
            return False 
        else:
            return True
        
    def get(self, url): 
        self.driver = next(self.generate_proxy_driver)
        
        # error when getting the webpage 
        try:
            self.driver.get(url)
        except:
            self.driver.quit()
            return False 
        
        sleep(10)
        # successfully retrieved webpage, but content blocked 
        if self.valida_response:
            return self.driver
        else:
            self.driver.quit()
            return False
                