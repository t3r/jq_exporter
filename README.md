# jq_exporter

**jq_exporter** is a lightweight Python-based tool that exports JSON data to Prometheus metrics, utilizing [jq](https://stedolan.github.io/jq/) expressions for filtering and transformation. Jq is like a swiss army knife for parsing and
extracting data from any kind of JSON data.

## Features

- **JSON Data Export**: Extracts and exports metrics from JSON data sources.
- **jq Integration**: Leverages jq expressions to filter and process JSON data efficiently.
- **Prometheus Compatibility**: Formats and exposes metrics in a Prometheus-compatible manner.

## Requirements

- Python 3.x
- Required Python packages
    * prometheus_client
    * pyyaml
    * jq

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/t3r/jq_exporter.git
   cd jq_exporter
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Configure `jq_exporter` by creating a configuration file based on the provided example:

1. **Copy the Example Configuration**:
   ```bash
   cp config.yml.example config.yml
   ```

2. **Edit `config.yml`**:
   - Define your JSON data sources.
   - Specify jq expressions to filter and transform the data.
   - Map the processed data to Prometheus metrics.

   *Note*: Ensure that your jq expressions are correctly defined to extract the desired metrics from your JSON data sources.

## Usage

Start the `jq_exporter` service:

```bash
python jq_exporter.py [config.yml]
```

If no parameter is given, jq_exporter will use the default "config.yml" for
configuration.

By default, the exporter will run on `http://localhost:9000/metrics`. You can customize the host and port by modifying the configuration file. You might
want to set the server address to `0.0.0.0` or to a more specific address of
a network interface to access it from outside.

## Security

The `jq_exporter` does not provide any kind of authentication mechanism. It also does not (yet) provide a way to expose it's metrics over `https`.

Accessing datasources with self signed certificates could be achieved by setting

```
source:
      insecure: true
```
in the `source` section of the config.yml. This will bypass any certificate
checks.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---



