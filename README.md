# FireUp
	
Python webserver to connect your UP accounts with [Firefly III](https://www.firefly-iii.org). The inspiration came from a [different project by Gustav de Prez](https://github.com/Mugl3/UP_Firefly_API_Connector). This project takes a different approach with the code written from scratch, and adds some useful features. Can easily be deployed in a Docker container.

This is my first released Python project. Expect a few bugs at this stage, as I'm still working everything out. Pull requests are welcome as I can always use some help with my coding!

#### Changelog
##### v0.0.2
Fixed a bug where categorised transactions would not import
##### v0.0.1
Initial release

## Features

* Listens for new activity on your Up accounts
* Adds, deletes, and settles transactions
* Support for round-ups, transfers and quick saves.
* Supports Up categories
* Supports foreign currencies
* Accounts and balances automatically added to Firefly on first run
* Automatically creates an Up webhook on your specified endpoint if none exists

### Notes

* Up transaction IDs are stored as internal references in Firefly
* Up account IDs are saved as account numbers in Firefly
* All transactions are tagged with "FireUp"
* If you rename an Up account, you will need to restart the server for the change to be reflected in Firefly. 
* Foreign currency amounts are appended to the transaction description 
* Up account emojis are stripped from the account name in Firefly. I may add an option to keep them in future.
* Does not import your past account activity.

### Roadmap

* Other transaction types (e.g. covers) 
* Ability to retrieve missing transactions in Firefly if the webserver goes down.
* More robust handling of errors

## Setting up the webserver

### Prerequistes

* A running instance of [Firefly III](https://www.firefly-iii.org)
* [Firefly API token](https://docs.firefly-iii.org/firefly-iii/api/)
* [Up API token](https://api.up.com.au/getting_started)
* Endpoint for your webhook

### Building the image

For easy deployment, the webserver runs in a [Docker](https://docs.docker.com/engine/install/) container. To get set up, clone the repository and build the image.

```
git clone https://github.com/lo-decibel/FireUp
cd FireUp
docker build -t local/fireup .
```

### Configuring the webserver

In the environment file, `fireup.env`, edit following environment variables as needed.

```ini
# Your Up webhook endpoint.
WEBHOOK_URL=http(s)://your_webhook_url

# URL to your firefly instance, including port
FIREFLY_URL=http://firefly:8080

# Up API amd Firefly tokens
UP_TOKEN=up:yeah:AABBCCDDEEFFaabbccddeeff 
FIREFLY_TOKEN=AABBCCDDEEFFaabbccddeeff

# Port for the webserver to listen on
PORT=5556
```

Then, fire up (pun intended) the container with

```
docker compose up -d
```

## Running without Docker

It's also possible to run the webserver without Docker. You will need a working install of Python, and you'll need to install the following packages:

```
pip install emoji requests flask waitress python-dotenv
```

Load the environment variables and run the webserver with

```
dotenv -f ./fireup.env run python ./app/main.py &
```

LICENSE: CC BY-NC-SA