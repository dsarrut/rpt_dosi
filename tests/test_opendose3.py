#!/usr/bin/env python3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from bs4 import BeautifulSoup
import json

# Define the URL of the form
url = "https://opendose.org/svalues"

# Set up a headless browser (you can also use 'webdriver.Chrome()' if you want to see the browser)
options = webdriver.ChromeOptions()
options.add_argument('--headless')
driver = webdriver.Chrome(options=options)


# Open the form URL
driver.get(url)

# Step 1: Select the phantom model in the dropdown with explicit wait
model_dropdown = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'phantom')))
model_dropdown_select = Select(model_dropdown)
model_dropdown_select.select_by_value('2')
print('Select phantom')

# Wait for the submit button to be clickable
submit_button = WebDriverWait(driver, 5).until(    EC.presence_of_element_located((By.ID, 'submit')))
form = driver.find_element(By.ID, 'myform')
form.submit()

# Wait for the source dropdown to appear
WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'source')))

# Find the 'source' dropdown element
print('consider source')
source_dropdown = driver.find_element(By.ID, 'source')

# Get all options from the dropdown
source_options = source_dropdown.find_elements(By.TAG_NAME, 'option')
#print(source_options)

# Extract the values from the options
source_attributes = [
    {
        'value': option.get_attribute('value'),
        'text': option.text,
        'class': option.get_attribute('class'),
        # Add more attributes as needed
    }
    for option in source_options
]

# Print the attributes
for attributes in source_attributes:
    print(attributes)

# Quit the WebDriver
driver.quit()
