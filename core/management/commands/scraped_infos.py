import csv
import requests
from unidecode import unidecode
from selenium.webdriver.common.action_chains import ActionChains
from typing import List
from django.core.management.base import BaseCommand
from bs4 import BeautifulSoup
from selenium.webdriver import Edge, EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium.common.exceptions import NoSuchElementException

class Command(BaseCommand):
    help = 'load data'

    def handle(self, *args, **kwargs):
        all_urls = self.construct_all_urls()
        all_hrefs = []
        data_list = [] 
        for url in all_urls:
            page_hrefs = self.display_hrefs_from_page(url)
            all_hrefs.extend(page_hrefs)

        print(all_hrefs)

        for url in all_hrefs:
            entry_data = {}  
            page = requests.get(url)
            scp = BeautifulSoup(page.content, 'html.parser')
            h1_element = scp.find('h1', class_='entry-title')
            if h1_element:
                name = h1_element.find('a').text.strip().replace('"', '') 
                entry_data["Name"] = name

            location_div = scp.find('div', itemprop='location')
            if location_div:
                address_li = location_div.find('li', class_='address')
                if address_li:
                    address = address_li.text.strip().replace('"', '')  
                    entry_data["Address"] = address

            email_element = scp.find('li', id='listing-email')
            if email_element:
                email = email_element.find('a').get('href').replace('mailto:', '').replace('"', '')  
                entry_data["Email"] = email

            categories_element = scp.find('p', class_='listing-cat')
            categories_string = ""
            if categories_element:
                categories_text = categories_element.get_text(strip=True).replace('Catégories ', '').replace('"', '')  
                categories_list = [category.strip() for category in categories_text.split(',')]
                categories_string += ", ".join(categories_list) + ", "
            if categories_string:
                categories_string = categories_string[len("Catégories "):]  
            entry_data["Categories"] = categories_string

            img_tag = scp.find('img', class_='attachment-medium size-medium listing_thumbnail')
            if img_tag:
                image_url = img_tag['src']
                entry_data["Image URL"] = image_url

            phone_number = self.get_revealed_phone_number(url)
            phone_number = phone_number.replace("tél/fax :", "").lower().strip()
            phone_number = phone_number.replace("tel :", "").lower().strip()
            phone_number = phone_number.replace("tel: ", "").lower().strip()
            entry_data["Phone"] = phone_number.replace('"', '')  
            data_list.append(entry_data)
        for data in data_list:
          data["Name"] = clean_french_chars(data["Name"])
          data["Address"] = clean_french_chars(data["Address"])
          data["Categories"] = clean_french_chars(data["Categories"])
        self.write_to_csv(data_list)

    def write_to_csv(self, data_list):
        fieldnames = ["Name", "Address", "Email", "Categories", "Image URL", "Phone"]
        filename = "info.csv"

        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
         
            for data in data_list:
                writer.writerow(data)
    def construct_all_urls(self) -> List[str]:
        base_url = "https://avocatalgerien.com/"
        all_urls = [base_url]
        page = requests.get(base_url)
        soup = BeautifulSoup(page.content, 'html.parser')
        pagination_links = soup.select('nav.pagination a.page-numbers')

        if pagination_links:
            # num_pages = int(pagination_links[-2].text)  pour avoir toutes les pages de pagination
            num_pages = 2#njarb ghir b 2 pages ida thbi tjibihm koll raj3i lil fog bach tdi g3 paginations
            all_urls += [f"{base_url}listings/page/{page}/" for page in range(2, num_pages + 1)]
        return all_urls

    def display_hrefs_from_page(self, url: str) -> List[str]:
        page = requests.get(url)
        scp = BeautifulSoup(page.content, 'html.parser')
        links = scp.find_all('a', href=True)
        lespages = []
        for link in links:
            if link.text.strip() == "Lire la suite…":
                href = link.get('href')
                if href:
                    lespages.append(href)
        result = list(set(lespages))
        return result
    def get_revealed_phone_number(self, link):
        edge_options = EdgeOptions()
        edge_options.binary_location = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"
        edge_options.add_argument("--disable-extensions")
        edge_options.add_argument("--disable-gpu")
        edge_options.add_argument("--disable-software-rasterizer")
        try:
            with Edge(options=edge_options) as driver:
                wait = WebDriverWait(driver, 10)
                driver.get(link)
                reveal_span = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'reveal')))
                driver.execute_script("arguments[0].scrollIntoView();", reveal_span)
                if "révéler le numéro" in reveal_span.text:
                    reveal_span.click()
                    time.sleep(3)
                    phone_element = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'li.phone[itemprop="telephone"] strong')) )
                    phone_text = phone_element.text.strip()
                    return phone_text
                else:
                    print("No phone number to reveal")
                    return "Phone number not found"

        except NoSuchElementException as e:
            print(f"Error finding phone element: {e}")
            return "Phone number not found"
        except Exception as ex:
            print(f"An error occurred: {ex}")
            return "Error retrieving phone number"

def clean_french_chars(text):
    cleaned_text = unidecode(text)
    return cleaned_text




