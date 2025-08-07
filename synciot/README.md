# Introduction
SyncIoT is an application designed to synchronize IoT data from Azure IoT Hub to a PostgreSQL database. It processes events received from IoT devices, extracts relevant data, and stores it in a structured format for further analysis and reporting. SyncIoT is built with scalability and reliability in mind, making it suitable for IoT solutions requiring real-time data ingestion and storage.<br />

It uses the Azure IoT Hub client to subscribe to events and the PostgreSQL client to insert data into the database.<br />
The script is designed to run as a background thread and can be configured using a JSON file.<br />

Secrets are managed using environment variables (until Azure Key Vault is available).<br />
    AZURE_IOTHUB_CONNECTION_STRING<br />
    AZURE_IOTHUB_CONSUMER_GROUP<br />
    AZURE_POSTGRESQL_HOST<br />
    AZURE_POSTGRESQL_PORT<br />
    AZURE_POSTGRESQL_DATABASE<br />
    AZURE_POSTGRESQL_USERNAME<br />
    AZURE_POSTGRESQL_PASSWORD<br />

The script also includes a configuration file (synciot.json) that defines the routes for the events and the tables in the PostgreSQL database.<br />
To create a different configuration, copy the synciot.json file and modify it as needed.<br />
There should be one configuration file per IoT Hub.<br />
You can provide the configuration file path using the environment variable SYNCIOT_CONFIG_FILENAME.<br />

# Getting Started
TODO: Guide users through getting your code up and running on their own system. In this section you can talk about:
1.	Installation process
2.	Software dependencies
3.	Latest releases
4.	API references

# Build and Test
Read docker/readme.txt <br />
Run scripts/build.sh <br />

# Features

- Subscribes to Azure IoT Hub events in real-time.
- Filters and processes IoT data based on configurable routes.
- Stores processed data in a PostgreSQL database.
- Configurable logging for monitoring and debugging.

# Contribute
TODO: Explain how other users and developers can contribute to make your code better.

If you want to learn more about creating good readme files then refer the following [guidelines](https://docs.microsoft.com/en-us/azure/devops/repos/git/create-a-readme?view=azure-devops). You can also seek inspiration from the below readme files:
- [ASP.NET Core](https://github.com/aspnet/Home)
- [Visual Studio Code](https://github.com/Microsoft/vscode)
- [Chakra Core](https://github.com/Microsoft/ChakraCore)