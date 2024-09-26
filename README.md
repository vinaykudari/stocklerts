# stocklerts: your personal stock price tracker

A Python-based stock price alert tracker that monitors stock prices using Finnhub and sends push notifications via Alertzy based on user-defined thresholds.

## Features

- Monitor multiple stock tickers with percentage-based alert thresholds.
- Send push notifications to configured devices using Alertzy.

## Setup

### Prerequisites

- Python 3.7+
- Poetry

### Installation

1. **Clone the Repository**

    ```bash
    git clone https://github.com/vinaykudari/stocklerts.git
    cd stocklerts
    ```

2. **Install Dependencies**

    ```bash
    poetry install
    ```

3. **Configure Environment Variables**

    Register at [finnhub](https://finnhub.io) and set the key:

    ```dotenv
    FINNHUB_API_KEY=<your_finnhub_api_key_here>
    ```
   
   Encrypt your Alertz account id at [devglan.com](https://www.devglan.com/online-tools/aes-encryption-decryption) using the exact same settings and set the passcode as env var
   ![img.png](resources/img.png)
   
   ```dotenv
    ENCRYPT_KEY=<your_passcode>
   # gail residents use our wifi passsword twice <password><password> to encrypt your account id
    ```

4. **Configure Application**

    Install [Alerty](http://alertzy.app/) app and copy the account id
    and update `config/config.yaml` with your desired settings:

 ```yaml
 defaults:
  cooldown_period_minutes: 60
  max_notifications_per_day: 100
  max_quote_calls_per_min: 60

alertzy:
  accounts:
    - user_id: 1
      account_id: <encrypted_account_id>

    - user_id: 2
      account_id: 18tu6LkU4y9uNArpNlAyog==

tickers:
  - symbol: AAPL
    threshold:
        - value: 5
          users:
            - 1
        - value: 0
          users:
            - 2

  - symbol: MSFT
    threshold:
      - value: 5
        users:
          - 1

  - symbol: GOOGL
    threshold:
      - value: 0
        users:
          - 1

 ```

5. **Run the application**

 ```bash
 poetry run python -m app.main
 ```

**Using docker**
 ```bash
 docker compose build 
 # make sure you sent the env vars before you run this
 FINNHUB_API_KEY=$FINNHUB_API_KEY ENCRYPT_KEY=$ENCRYPT_KEY docker compose up
 ```


