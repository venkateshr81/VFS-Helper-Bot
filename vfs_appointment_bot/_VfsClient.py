import base64
from cmath import exp
import email
import time
import logging
import datetime

import requests

from _ConfigReader import _ConfigReader
from _TwilioClient import _TwilioClient
from _TelegramClient import _TelegramClient


from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class _VfsClient:

    def __init__(self):
        self._twilio_client = _TwilioClient()
        self._telegram_client = _TelegramClient()
        self._config_reader = _ConfigReader()

        self._use_telegram = self._config_reader.read_prop("DEFAULT", "use_telegram")
        self._use_twilio = self._config_reader.read_prop("DEFAULT", "use_twilio")
        logging.debug("Will use Telegram : {}".format(self._use_telegram))
        logging.debug("Will use Twilio : {}".format(self._use_twilio))

    def _init_web_driver(self):
        firefox_options = Options()

        # open in headless mode to run in background
        firefox_options.headless = True
        # firefox_options.add_argument("start-maximized")

        # following options reduce the RAM usage
        firefox_options.add_argument("disable-infobars")
        firefox_options.add_argument("--disable-extensions")
        firefox_options.add_argument("--no-sandbox")
        firefox_options.add_argument("--disable-application-cache")
        firefox_options.add_argument("--disable-gpu")
        firefox_options.add_argument("--disable-dev-shm-usage")
        self._web_driver = webdriver.Firefox(options=firefox_options)

        # make sure that the browser is full screen,
        # else some buttons will not be visible to selenium
        self._web_driver.maximize_window()

    def _login(self):

        _section_header = "VFS"
        _email = self._config_reader.read_prop(_section_header, "vfs_email");
        _password = self._config_reader.read_prop(_section_header, "vfs_password");

        logging.debug("Logging in with email: {}".format(_email))

        # logging in
        time.sleep(10)

        # sleep provides sufficient time for all the elements to get visible
        _email_input = self._web_driver.find_element(By.XPATH,"//*[@id='mat-input-0']")
        
        _email_input.send_keys(_email)
        _password_input = self._web_driver.find_element(By.XPATH,"//*[@id='mat-input-1']")
        _password_input.send_keys(_password)
        _login_button = self._web_driver.find_element(By.XPATH,"//button/span")
        _login_button.click()
        time.sleep(10)

    def _take_element_screenshot(driver, element):
        # Take a screenshot of the specific element
        element_screenshot = element.screenshot_as_png
        return element_screenshot
    
    def _tracking_application(self, reference_number, last_name):
        self._init_web_driver()

        # open the webpage
        self.vfs__application_tracking_url = self._config_reader.read_prop("VFS", "vfs_tracking_url")
        self._web_driver.get(self.vfs__application_tracking_url)

        logging.info("Tracking application: Reference Number: {}, Last Name: {}".format(reference_number, last_name))
        time.sleep(10)
        # sleep provides sufficient time for all the elements to get visible
        _reference_number_input = self._web_driver.find_element(By.XPATH,"//*[@id='RefNo']")
        _reference_number_input.send_keys(reference_number)

        _last_name_input = self._web_driver.find_element(By.XPATH,"//*[@id='Last Name']")
        _last_name_input.send_keys(last_name)

        self._captureScreenshotAndValidateCaptcha(reference_number, last_name)
        
        try:
            element = WebDriverWait(self._web_driver, 60).until(
                EC.presence_of_element_located((By.XPATH, "//*[@id='Index']/div[11]/b"))
            )
            
            # Find the element and print its text
            _tracking_result_message = self._web_driver.find_element(By.XPATH, "//*[@id='Index']/div[11]/b").text
            logging.info("Message: {}".format(_tracking_result_message))
            logging.debug("Message: {}".format(_tracking_result_message))
        except Exception as e:
            logging.info("Message: Element not found")            
            logging.debug("Message: Element not found")
            _tracking_result_message = ""

        return _tracking_result_message
    
    def _captureScreenshotAndValidateCaptcha(self, reference_number, last_name):
        logging.info("Initiating captcha validation")
        _captcha_image_element = self._web_driver.find_element(By.XPATH, "//*[@id='CaptchaImage']")
        element_screenshot = _captcha_image_element.screenshot_as_png

        # Encode the screenshot in base64
        encoded_screenshot = base64.b64encode(element_screenshot).decode('utf-8')


        headers= {
                'Content-Type': "text/plain;charset=UTF-8",
                'DNT' : '1',
                'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36',
                'Referer': 'https://cloud.google.com/vision/',    
                'Origin': 'https://cloud.google.com',
                }
    
    
        data2= {"requests":
        [{"image":{"content":encoded_screenshot},
        "features":[{"type":"DOCUMENT_TEXT_DETECTION","maxResults":50}],
        "imageContext":{"cropHintsParams":{"aspectRatios": [2.86]}, "languageHints": ["en-t-i0-handwrit"]}}]}
    
        logging.info("Making API call")
        response = requests.post(f"https://vision.googleapis.com/v1/images:annotate?key={'API-Key'}",  json = data2, headers = headers)

        # Debug: Print the response status code and content
        logging.info("Captcha Response Status Code: {}".format(response.status_code))

        data = response.json()
        captcha = ""
        try:
            captcha=data['responses'][0]['fullTextAnnotation']['text']
            logging.info("Captcha is: {}".format(captcha))
        except:
            logging.info("Couldn't decode the captcha :(")

        _captcha_input = self._web_driver.find_element(By.XPATH,"//*[@id='CaptchaInputText']")
        _captcha_input.send_keys(captcha)
        
        _submit_button = self._web_driver.find_element(By.XPATH,"//*[@id='submitButton']")        
        _submit_button.click()

        time.sleep(5)

        try:
            # Locate the error message element by its class name
            error_element = self._web_driver.find_element(By.CLASS_NAME, 'validation-summary-errors')
            if error_element:
                logging.info("Error occured! Invalid captcha :(")
                # Refresh the page
                self._web_driver.refresh()

                # Wait for a few seconds to ensure the page has fully reloaded
                time.sleep(10)
                self._tracking_application(reference_number, last_name)
            else:
                logging.info("Captcha validation passed!")
        except:
            pass

    def _validate_login(self):
        try:
            _new_booking_button = self._web_driver.find_element(By.XPATH,"//section[1]/div/div[2]/div/button/span[1]")
            if _new_booking_button == None:
                logging.debug("Unable to login. VFS website is not responding")
                raise Exception("Unable to login. VFS website is not responding")
            else:
                logging.debug("Logged in successfully")
        except:
            logging.debug("Unable to login. VFS website is not responding")
            raise Exception("Unable to login. VFS website is not responding")

    def _get_appointment_date(self, visa_centre, category, sub_category):
        logging.info("Getting appointment date: Visa Centre: {}, Category: {}, Sub-Category: {}".format(visa_centre, category, sub_category))
        # select from drop down
        _new_booking_button = self._web_driver.find_element(By.XPATH,
            "//section[1]/div/div[2]/div/button/span[1]"
        )        
        _new_booking_button.click()
        time.sleep(5)
        _visa_centre_dropdown = self._web_driver.find_element(By.XPATH,
            "//*[@id='mat-select-0']"
        )
        _visa_centre_dropdown.click()
        time.sleep(2)

        try:
            _visa_centre = self._web_driver.find_element(By.XPATH,
                "//*[@id='mat-option-3']/span"
            )
        except NoSuchElementException:
            raise Exception("Visa centre not found: {}".format(visa_centre))

        logging.debug("VFS Centre: {}".format(_visa_centre.text))
        self._web_driver.execute_script("arguments[0].click();", _visa_centre)
        time.sleep(5)

        _category_dropdown = self._web_driver.find_element(By.XPATH,
            "//*[@id='mat-select-4']"
        )
        _category_dropdown.click()
        time.sleep(5)

        try:
            _category = self._web_driver.find_element(By.XPATH,
                "//mat-option[starts-with(@id,'mat-option-')]/span[contains(text(), '{}')]".format(category)
            )
        except NoSuchElementException:
            raise Exception("Category not found: {}".format(category))

        logging.debug("Category: {}".format(_category.text))
        self._web_driver.execute_script("arguments[0].click();", _category)
        time.sleep(5)

        _subcategory_dropdown = self._web_driver.find_element(By.XPATH,
            "//*[@id='mat-select-2']"
        )

        self._web_driver.execute_script("arguments[0].click();", _subcategory_dropdown)
        time.sleep(5)

        try:
            _subcategory = self._web_driver.find_element(By.XPATH,
                "//mat-option[starts-with(@id,'mat-option-')]/span[contains(text(), '{}')]".format(sub_category)
            )
        except NoSuchElementException:
            raise Exception("Sub-category not found: {}".format(sub_category))

        self._web_driver.execute_script("arguments[0].click();", _subcategory)
        logging.debug("Sub-Cat: " + _subcategory.text)
        time.sleep(5)

        # read contents of the text box
        textBox_list = [
            self._web_driver.find_element(By.XPATH, "//div[4]/div[1]"),
            self._web_driver.find_element(By.XPATH, "//div[4]/div[2]")
        ]
        return textBox_list

    def check_slot(self, visa_centre, category, sub_category):
        self._init_web_driver()

        # open the webpage
        self.vfs_login_url = self._config_reader.read_prop("VFS", "vfs_login_url")
        self._web_driver.get(self.vfs_login_url)

        self._login()
        self._validate_login()

        _TextBoxMessages = self._get_appointment_date(visa_centre, category, sub_category)

        # Initialize draftMessage
        draftMessage = ""
        
        for _textBox in _TextBoxMessages:
            logging.debug("Message: " + _textBox.text)
            if len(_textBox.text) != 0 and _textBox.text != "No appointment slots are currently available" and _textBox.text != "Currently No slots are available for selected category, please confirm waitlist\nTerms and Conditions":
                logging.info("Appointment slots available: {}".format(_textBox.text))
                draftMessage += "{}\n".format(_textBox.text)
            else:
                logging.info("No slots available")
        
        if len(draftMessage) == 0:
            draftMessage = "No slots available :("

        logging.debug("Message: " + draftMessage)

        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime("%d-%m-%Y %H:%M:%S")
        message = "{}\n-- Checked at {} --".format(draftMessage, st)
        if eval(self._use_telegram):
            self._telegram_client.send_message(message)
        if eval(self._use_twilio):
            self._twilio_client.send_message(message)
            self._twilio_client.call()

        # Close the browser
        self._web_driver.close()
        self._web_driver.quit()
    
    def track_application(self, reference_number, last_name):
        _trackingMessage = self._tracking_application(reference_number=reference_number, last_name=last_name)
        logging.debug("Message: " + _trackingMessage)

        # Initialize draftMessage
        draftMessage = ""
        
        if len(_trackingMessage) != 0:
                logging.info("Tracking successful: {}".format(_trackingMessage))
                draftMessage = "{}".format(_trackingMessage)
        else:
            logging.info("Tracking failed :(")
        
        if len(draftMessage) == 0:
            draftMessage = "Couldn't track your application :("

        logging.debug("Message: " + draftMessage)

        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime("%d-%m-%Y %H:%M:%S")
        message = "{}\n-- Checked at {} --".format(draftMessage, st)
        if eval(self._use_telegram):
            self._telegram_client.send_message(message)
        if eval(self._use_twilio):
            self._twilio_client.send_message(message)
            self._twilio_client.call()

        # Close the browser
        self._web_driver.close()
        self._web_driver.quit()
