import re
import sys
import os
import requests
import time
import logging
from playwright.sync_api import Playwright, sync_playwright
from datetime import datetime

# Set up logging for ordinary logs to stdout
ordinary_logger = logging.getLogger("ordinary")
ordinary_handler = logging.StreamHandler(sys.stdout)
ordinary_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
ordinary_logger.addHandler(ordinary_handler)
ordinary_logger.setLevel(logging.INFO)

# Set up logging for Jenkins output to stderr
jenkins_logger = logging.getLogger("jenkins")
jenkins_handler = logging.StreamHandler(sys.stderr)
jenkins_handler.setFormatter(logging.Formatter("%(message)s"))
jenkins_logger.addHandler(jenkins_handler)
jenkins_logger.setLevel(logging.INFO)


# Jenkins API URL for your job
def jenkins_url(pod):
    return f"https://jenkins-internal.iwalabs.info/job/{pod}"


# Function to get the last pipeline number from Jenkins
def get_last_pipeline_number(username, password, pod):
    ordinary_logger.info(f"Fetching last pipeline number for pod: {pod}")
    api_url = f"{jenkins_url(pod)}/api/json"
    response = requests.get(api_url, auth=(username, password))

    if response.status_code == 200:
        last_build = response.json().get("lastBuild", {}).get("number")
        if last_build:
            ordinary_logger.info(f"Last pipeline number: {last_build}")
            return last_build
        else:
            ordinary_logger.error("Could not fetch the last build number.")
            sys.exit(1)
    else:
        ordinary_logger.error(
            f"Failed to connect to Jenkins API. Status code: {response.status_code}"
        )
        sys.exit(1)


# Add this dictionary at the top of the file, after the imports
MODEL_MAPPER = {
    "Booking": {
        "pod": "prod-run-script-with-string",
        "service_name": "sakani-beneficiaries-graphql",
    },
    "Beneficiary": {
        "pod": "prod-run-script-with-string",
        "service_name": "sakani-beneficiaries-graphql",
    },
    "TrackingPriceQuotation": {
        "pod": "prod-run-script-with-string",
        "service_name": "sakani-beneficiaries-graphql",
    },
    "AzmStoreClient": {
        "pod": "prod-run-script-with-string",
        "service_name": "sakani-main-intermediary",
    },
    "CompanyUser": {
        "pod": "prod-run-script-with-string",
        "service_name": "sakani-partners-service",
    },
    "Company": {
        "pod": "prod-run-script-with-string",
        "service_name": "sakani-partners-service",
    },
    "ProjectsData": {
        "pod": "prod-run-script-with-string",
        "service_name": "sakani-external-integrations-service",
    },
    # Add more models here as needed
}


# Function to extract task name, service name, server, and pod from the Ruby script
def extract_from_ruby(ruby_file_path):
    ordinary_logger.info(f"Extracting information from Ruby script: {ruby_file_path}")
    with open(ruby_file_path, "r") as file:
        ruby_content = file.read()

    # Regex to find the task_name variable assignment
    task_name_match = re.search(r"task_name\s*=\s*['\"](\w+)['\"]", ruby_content)

    # Find all model names used in the script
    model_names = re.findall(r"(\w+)\.where", ruby_content)

    if not model_names:
        ordinary_logger.error("No model names found in the Ruby script.")
        sys.exit(1)

    # Use the first model name found to get pod and service_name
    primary_model = model_names[0]
    if primary_model not in MODEL_MAPPER:
        ordinary_logger.error(f"Model '{primary_model}' not found in the mapper.")
        sys.exit(1)

    pod = MODEL_MAPPER[primary_model]["pod"]
    service_name = MODEL_MAPPER[primary_model]["service_name"]

    ordinary_logger.info(
        f"Task: {task_name_match.group(1) if task_name_match else 'Not found'}"
    )
    ordinary_logger.info(f"Models used: {', '.join(model_names)}")
    ordinary_logger.info(f"Primary model: {primary_model}")
    ordinary_logger.info(f"Pod: {pod}")
    ordinary_logger.info(f"Service name: {service_name}")

    if task_name_match:
        return task_name_match.group(1), service_name, pod
    else:
        ordinary_logger.error("Could not extract the task name from the Ruby script.")
        sys.exit(1)


def run(playwright: Playwright, ruby_file_path, download_flag=False) -> None:
    ordinary_logger.info("Starting the Playwright script")
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    context.set_default_timeout(0)

    page = context.new_page()

    # Login to Jenkins
    ordinary_logger.info("Logging into Jenkins")
    page.goto("https://jenkins-internal.iwalabs.info/login")
    page.get_by_label("Username").fill("mahmud_soliman")
    page.get_by_label("Password").fill("Ldso@5000")
    page.get_by_role("button", name="Sign in").click()

    # Extract task_name from Ruby file
    task_name, service_name, pod = extract_from_ruby(ruby_file_path)

    ordinary_logger.info(f"Navigating to Jenkins job: {pod}")
    page.goto(f"https://jenkins-internal.iwalabs.info/job/{pod}/")

    ordinary_logger.info("Initiating build with parameters")
    page.get_by_role("link", name="Build with Parameters").click()

    # Fill task name and other parameters
    ordinary_logger.info(
        f"Filling in build parameters. Task name: {task_name}, Service: {service_name}"
    )
    page.locator('input[name="value"]').click()
    page.locator('input[name="value"]').fill(task_name)
    page.locator(
        'div[description="Please select a service"] select[name="value"]'
    ).select_option(service_name)

    page.locator('textarea[name="value"]').click()
    time.sleep(2)
    # Read the Ruby file contents and fill the textarea
    with open(ruby_file_path, "r") as file:
        ruby_script = file.read()
    page.locator('textarea[name="value"]').fill(ruby_script)

    # Start the build
    ordinary_logger.info("Starting the build")
    page.get_by_role("button", name="Build").click()

    # Get the last pipeline number automatically
    username = "mahmud_soliman"
    password = "Ldso@5000"
    pipeline_number = get_last_pipeline_number(username, password, pod)

    # Navigate to the console output for the build
    ordinary_logger.info(
        f"Navigating to console output for build number: {pipeline_number}"
    )
    page.goto(f"{jenkins_url(pod)}/{pipeline_number}/console")

    # Scroll down to view the entire console output
    page.evaluate("window.scrollBy(0, document.body.scrollHeight)")

    # Wait for the "APPROVE ???" button to appear and click it
    ordinary_logger.info("Waiting for and clicking the 'APPROVE' button")
    page.locator("a:has-text('APPROVE ???')").wait_for()
    page.locator("a:has-text('APPROVE ???')").click()

    # Wait for the build to finish and check the result
    ordinary_logger.info("Waiting for the build to finish")
    page.wait_for_function("""
        () => {
            const consoleOutput = document.querySelector('pre.console-output').innerText;
            return consoleOutput.includes('Finished: SUCCESS') ||
                   consoleOutput.includes('Finished: FAILURE') ||
                   consoleOutput.includes('Finished: ABORTED');
        }
    """)

    # Fetch the entire console output
    console_output = page.locator("pre.console-output").text_content()

    # Print the process status based on final outcome
    if "Finished: SUCCESS" in console_output:
        ordinary_logger.info("Process succeeded!")
    elif "Finished: FAILURE" in console_output:
        ordinary_logger.warning("Process failed!")
    elif "Finished: ABORTED" in console_output:
        ordinary_logger.warning("Process was aborted!")

    # Use a regex to extract the relevant 'TASK [debug]' or 'FAILED!' content
    debug_task_pattern = r"(TASK \[debug\].*?PLAY RECAP \*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*)"
    failure_task_pattern = r"(fatal: .*?STDOUT:.*?PLAY RECAP \*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*)"

    # Try matching the success case first
    debug_task_match = re.search(debug_task_pattern, console_output, re.DOTALL)

    if debug_task_match:
        debug_task_content = debug_task_match.group(0)
        jenkins_logger.info("\nSTART OF TASK [debug]\n")
        jenkins_logger.info(debug_task_content)
        jenkins_logger.info("\nEND OF TASK [debug]\n")
    else:
        failure_task_match = re.search(failure_task_pattern, console_output, re.DOTALL)
        if failure_task_match:
            failure_task_content = failure_task_match.group(0)
            jenkins_logger.warning("\nSTART OF TASK [failure]\n")
            jenkins_logger.warning(failure_task_content)
            jenkins_logger.warning("\nEND OF TASK [failure]\n")
        else:
            jenkins_logger.warning(
                "No TASK [debug] or [failure] information found in the output."
            )

    # Download the result file if download_flag is set
    if download_flag and debug_task_match:
        ordinary_logger.info("Attempting to download result file")
        today_date = datetime.today().strftime("%Y%m%d")
        download_url = f"{jenkins_url(pod)}/{pipeline_number}/execution/node/3/ws/sakani_scripts/{today_date}/"
        page.goto(download_url)

        # Locate the file link by name (e.g., "test5_result.csv")
        file_locator = page.locator(f'a[href="{task_name}_result.csv"]')

        if file_locator:
            download_path = os.path.join(os.getcwd(), f"{task_name}_result.csv")
            with page.expect_download() as download_info:
                file_locator.click()
            download = download_info.value
            download.save_as(download_path)
            ordinary_logger.info(
                f"File '{task_name}_result.csv' downloaded successfully to {download_path}"
            )
        else:
            ordinary_logger.warning(
                f"File '{task_name}_result.csv' not found at {download_url}."
            )

    browser.close()
    ordinary_logger.info("Playwright script completed")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        ordinary_logger.error("Usage: python script.py <ruby_file_path> [--download]")
        sys.exit(1)

    ruby_file_path = sys.argv[1]
    download_flag = "--download" in sys.argv

    ordinary_logger.info(f"Starting script with Ruby file: {ruby_file_path}")
    ordinary_logger.info(f"Download flag: {download_flag}")

    with sync_playwright() as playwright:
        run(playwright, ruby_file_path, download_flag)
