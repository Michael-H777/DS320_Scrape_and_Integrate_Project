from utils.packages import *


class driver_object:
    
    blocks = ['This site can’t be reached', 'No internet', 'Access Denied', 'Error 503', 'Our systems have detected unusual traffic from your computer network']
    
    def __init__(self, driver_path):
        
        self.driver_path = driver_path 
        self.generate_proxy = self.get_proxy() 
        self.generate_proxy_driver = self.get_proxy_drivers()


    def get_proxy(self): 
        
        with open('proxies.txt', 'r') as filein: 
            proxies = filein.read().split('\n')
            
        proxies.pop() 
        shuffle(proxies)
        
        while True: 
            for address in proxies: 
                #print(address)
                yield address 
            proxies = shuffle(proxies)


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

            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument("--disable-dev-shm-usage")
                
            yield  webdriver.Chrome(executable_path=self.driver_path, chrome_options=options , desired_capabilities=capabilities)
        
    @property
    def valida_response(self):
        return False if any(item in self.driver.page_source for item in driver_object.blocks) else True
        
    def get(self, url): 
        
        self.driver = next(self.generate_proxy_driver)
        
        try:
            self.driver.get(url)
        except:
            self.driver.quit()
            return False 
        
        sleep(10)
        
        if self.valida_response:
            return self.driver
        else:
            self.driver.quit()
            return False
                