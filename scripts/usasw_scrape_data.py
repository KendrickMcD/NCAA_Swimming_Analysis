# This script is used to collect NCAA Swimming data from the USA Swimming website
# The script uses a headless Chrome driver to collect the data
# The function fill_out_form() is used to fill out the form on the website
# The function clean_usa_swimming_data() is used to clean the csv file downloaded from the website
# The function get_ncaa_swimming_data() is used to collect the data from the website

# Calling the function get_ncaa_swimming_data() requires the following arguments:
# start_year: The season to start collecting data from
# end_year: The season to end collecting data from (optional)
# top_n: The number of swimmers per event to view in the data

# Example: get_ncaa_swimming_data(2010, 2011, 10) will collect the top 10 swimmers per event for the 2010-2011 season

# Import libraries
import os
import time
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import numpy as np

from scripts.usasw_clean_data import clean_ncaa_swimming_data

# Set up the Chrome driver
chrome_options = Options()
chrome_options.add_argument("--headless")  # Use headless mode
chrome_options.add_argument("window-size=1920x1080")  # Set the window size
driver = webdriver.Chrome(options=chrome_options)

# Fill out form


def fill_out_form(driver, start_year, end_year, top_n):

    # Match the year to corresponding season for the dropdown menu of full seasons
    years = np.arange(2010, 2024)
    seasons = {f'{y-1}-{y}': y for y in years}

    # Find the corresponding season value for the given year
    if start_year in seasons.values():
        season = [key for key, value in seasons.items() if value ==
                  start_year][0]

    if end_year == None:
        range = 0
    else:
        range = end_year - start_year

    # Select competition year or date range
    if start_year > 2009 and range <= 1:

        # Find the corresponding option value for the given season using JavaScript
        js_get_option_value = f'''
        var dropdown = $("#Times_SecondaryOrgTopTimes_Index_Div_1ddlDateRanges").data("kendoDropDownList");
        var data = dropdown.dataSource.data();
        var option_value = -1;
        for (var i = 0; i < data.length; i++) {{
            if (data[i].Description === "{season}") {{
                option_value = data[i].Id;
                break;
            }}
        }}
        return option_value;
        '''
        option_value = driver.execute_script(js_get_option_value)

        # Select the option value in the dropdown menu using JavaScript
        js_select_option = f'''
        var dropdown = $("#Times_SecondaryOrgTopTimes_Index_Div_1ddlDateRanges").data("kendoDropDownList");
        dropdown.value({option_value});
        dropdown.trigger("change");
        '''
        driver.execute_script(js_select_option)

    else:

        # Create end date for single season input since the website requires a date range
        if start_year < 2010:
            start_year = start_year - 1
            end_year = start_year + 1

        # Calculate start and end dates
        start_date = f"09/01/{start_year}"
        end_date = f"08/31/{end_year}"

        # JavaScript code to set the start and end dates
        js_set_dates = f'''
        var start_date_element = document.getElementById("Times_SecondaryOrgTopTimes_Index_Div_1StartDate");
        start_date_element.value = "{start_date}";
        start_date_element.dispatchEvent(new Event("change"));

        var end_date_element = document.getElementById("Times_SecondaryOrgTopTimes_Index_Div_1EndDate");
        end_date_element.value = "{end_date}";
        end_date_element.dispatchEvent(new Event("change"));
        '''

        # Execute the JavaScript code to set the start and end dates
        driver.execute_script(js_set_dates)

    # Input number of swimmers
    input_field = driver.find_element(By.XPATH, "//input[@id='ShowTop']")

    # Wait for the input field to be interactable
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//input[@id='ShowTop']")))

    # Clear the current value
    input_field.clear()
    input_field.send_keys(str(top_n))

    # Locate checkboxes for LCM, SCM, and SCY
    lcm_checkbox = driver.find_element(By.XPATH,
                                       "//input[@id='SelectLCMCourses']")
    scm_checkbox = driver.find_element(By.XPATH,
                                       "//input[@id='SelectSCMCourses']")
    scy_checkbox = driver.find_element(By.XPATH,
                                       "//input[@id='SelectSCYCourses']")

    if lcm_checkbox.is_selected():
        driver.execute_script("arguments[0].click();", lcm_checkbox)
    if scm_checkbox.is_selected():
        driver.execute_script("arguments[0].click();", scm_checkbox)

    # Check the SCY checkbox if it is not checked
    if not scy_checkbox.is_selected():
        driver.execute_script("arguments[0].click();", scy_checkbox)


# Get NCAA results from USA Swimming

def get_NCAA_results(top_n, start_year, end_year=None):

    # Set up the Chrome driver
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Use headless mode
    driver = webdriver.Chrome(options=chrome_options)

    url = 'https://www.usaswimming.org/times/otherorganizations/ncaa-division-i/top-times-report'
    driver.get(url)

    try:
        # Check if consent button exists and click it
        consent_button = driver.find_element(
            By.XPATH, "//button[contains(@class, 'fc-cta-consent')]")
        consent_button.click()
    except NoSuchElementException:
        # Consent button does not exist, continue with script
        pass

    # Wait for the page to load by waiting for the presence of the dropdown menu
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "Times_SecondaryOrgTopTimes_Index_Div_1ddlDateRanges")))

    fill_out_form(driver, start_year, end_year, top_n)

    # # Take a screenshot of the page
    # default_download_path = os.path.join(os.path.expanduser("~"), "Downloads")
    # screenshot_filename = os.path.join(default_download_path, "screenshot.png")
    # driver.save_screenshot(screenshot_filename)
    # print(f"Screenshot saved at {screenshot_filename}")

    # Click "Find Times"
    find_times_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "saveButton")))
    find_times_button.click()

    # Select the "Csv" option
    output_types_dropdown = WebDriverWait(driver, 120).until(
        EC.element_to_be_clickable((By.ID, "OutputTypes")))
    output_types_dropdown.click()

    csv_option = driver.find_element(
        By.XPATH, "//select[@id='OutputTypes']/option[@value='Csv']")
    csv_option.click()

    # Click the download button
    image_element = driver.find_element(
        By.XPATH, "//div[@class='usas-reports-reportviewer-outer-top-right']/img")
    image_element.click()

    # Find the downloaded CSV file in the current working directory
    csv_filename = "Report.csv"

    # Wait for the file to be downloaded
    max_wait_time = 30
    wait_interval = 1
    wait_time = 0
    while not os.path.isfile(csv_filename) and wait_time < max_wait_time:
        time.sleep(wait_interval)
        wait_time += wait_interval

    if not os.path.isfile(csv_filename):
        raise FileNotFoundError(
            f"File '{csv_filename}' was not found after waiting for {max_wait_time} seconds.")

    # Rename file
    if end_year is None:
        new_csv_filename = f"{start_year}.csv"
    else:
        new_csv_filename = f"{start_year}-{end_year}.csv"

    # Rename the file in the current directory
    os.rename(csv_filename, new_csv_filename)

    # Clean the CSV file
    df = clean_ncaa_swimming_data(new_csv_filename)

    # Save the cleaned CSV file
    df.to_csv(new_csv_filename, index=False)

    # Delete the "GetReport.pdf" file from the current working directory
    pdf_filename = "GetReport.pdf"

    if os.path.isfile(pdf_filename):
        os.remove(pdf_filename)

    return df, new_csv_filename


if __name__ == "__main__":
    # Get user inputs

    # Get start_year input and make sure it is an integer between 1999 and 2023
    start_year = int(input("Enter a swim season (e.g., 2022): "))
    while start_year < 1999 or start_year > 2023:
        print("Please enter a valid swim season (e.g., 2022).")

    # Get end_year input and make sure it is an integer between 1999 and 2023
    end_year_input = input(
        "If you are interested in a range of seasons, enter the terminal season (optional, press enter to skip): ")
    end_year = int(end_year_input) if end_year_input.strip() else None
    while end_year is not None and (end_year < 1999 or end_year > 2023):
        print("Please enter a valid swim season (e.g., 2022).")

    # Get top_n input and make sure it is an integer between 1 and 1000
    top_n = int(
        input("Enter the number of results per event that you want (e.g., 100): "))
    while top_n < 1 or top_n > 1000:
        print("Please enter a valid number of results per event (e.g., 100).")

    # Call the main function
    file = get_NCAA_results(top_n, start_year, end_year)[1]
    print(f"Downloaded and cleaned results from {start_year} as {file}.")
