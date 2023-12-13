#!/usr/bin/env python3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from bs4 import BeautifulSoup
import json
from rpt_dosi.helpers import find_closest_match_dict

def open_svalues():
    # Define the URL of the form
    url = "https://opendose.org/svalues"

    # Set up a headless browser
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)

    # Open the form URL
    driver.get(url)

    # Select the phantom model in the dropdown with explicit wait
    model_dropdown = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'phantom')))
    return driver, model_dropdown

def svalues_select_phantom(driver, model_dropdown, phantom_name = "IRCP 110 AM"):
    phantoms = {"ICRP 110 AF": "1", "ICRP 110 AM": "2"}

    # which phantom ?
    phantom_name = find_closest_match_dict(phantom_name, phantoms)
    phantom_id = phantoms[phantom_name]

    model_dropdown_select = Select(model_dropdown)
    model_dropdown_select.select_by_value(phantom_id)

    # Wait for the submit button to be clickable
    WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, 'submit')))
    form = driver.find_element(By.ID, 'myform')
    form.submit()

    # Wait for the source dropdown to appear
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'source')))


def get_all_dropdown_options(driver, name):
    # Find the 'name' dropdown element
    dropdown = driver.find_element(By.ID, name)

    # Get all options from the dropdown
    options = dropdown.find_elements(By.TAG_NAME, 'option')

    # Extract the values from the options
    source_attributes = [
        {
            'id': option.get_attribute('value'),
            'value': option.text
        }
        for option in options
    ]

    return source_attributes
