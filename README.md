# Stokt Gym Route Statistics

## Description

The Stokt Gym Route Statistics script is a Python script that retrieves route information from the Stokt app and displays common statistics. 
To use this script you will need to have a cookie, authentication token, and
face ID from the Stokt app.
Getting this information requires installing 
mitmproxy to capture network packets  from your cell phone.

## Prerequisites

Before running the script, ensure you have the following prerequisites installed:

- Python 3.x
- mitmproxy

## Installation

1. Clone the repository:

   ```shell
   git clone https://github.com/nrfulton/stoktreport.git
   ```

2. Install the required Python packages:

   ```shell
   pip install -r requirements.txt
   ```

3. Run mitmproxy on your computer and configure your phone to use the proxy. Be sure to install root certs.
4. open the Stokt app on your phone and log in. Use the gym selection tool to choose your gym.
5. Look for something that looks like `https://www.sostokt.com/api/faces/FACE-ID-HERE/setup` in the logs.
6. Note the cookie, authentication token, and face ID from this request.
7. Run the reporting script:

    ```shell
    python stokt_report.py --cookie "COOKIE" --auth "AUTH" --faceid "FACEID"
    ```

Your report will be output to `report.html`. Be sure to delete the route
similarity line before re-running the report.

You can optionally skip the download step by padding `--skip_download` to the
script. This can only be done after running the script for the first time.
