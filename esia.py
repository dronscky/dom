from requestium import Session


class AuthGIS:
    def __init__(self, login, password) -> None:
        self.s = Session(webdriver_path='./webdriver/chromedriver',
                    browser='chrome',
                    default_timeout=15,
                    webdriver_options={'arguments': ['headless', 
                                                    'ignore-certificate-errors',
                                                    'ignore-ssl-errors',
                                                    'disable-blink-features=AutomationControlled'
                                                    'user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
                                                    AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36',
                                                    'disable-gpu'
                                                    ]})
        self._login = login
        self._pwd = password
        self.authorization()
        
    def authorization(self):
        self.s.driver.get("https://dom.gosuslugi.ru")
        self.s.driver.ensure_element_by_xpath("//a[@ng-click='sign()']", state='clickable').ensure_click()
        #   ввод данных
        self.s.driver.ensure_element_by_id("login").send_keys(self._login)
        self.s.driver.ensure_element_by_id("password").send_keys(self._pwd)
        #   вход
        self.s.driver.ensure_element_by_xpath("//button[@class='plain-button plain-button_wide']", state='clickable').ensure_click()
        #   выбор организации
        self.s.driver.ensure_element_by_xpath("//p[text()[contains(., 'ОГРН: 1020202870555')]]", state='clickable').ensure_click()
        #   неГОСТ подключение
        self.s.driver.ensure_element_by_id("saveCookie", state='clickable').ensure_click()
        self.s.driver.ensure_element_by_id("bContinue", state='clickable').ensure_click()

    def get_session(self):
        self.s.transfer_driver_cookies_to_session()
        return self.s

    def __del__(self):
        self.s.driver.quit()
        print('Экземпляр класса авторизации удален...')
