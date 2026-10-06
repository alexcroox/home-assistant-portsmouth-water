# Portsmouth Water for Home Assistant

An unofficial Home Assistant custom integration for Portsmouth Water smart meters. It uses the same Kraken API as [the Portsmouth Water customer portal](https://myaccount.portsmouthwater.co.uk).

## Features

- Latest complete daily water usage in **litres** and the date of that reading.
- Daily consumption history for Home Assistant's Energy → Water dashboard, also in litres.
- Potential-leak indicator supplied by Portsmouth Water for the latest daily reading.
- Automatic updates every six hours.
- Sign-in through Home Assistant; the integration stores a renewable token and discards the password.

## Requirements

- A Portsmouth Water online account with an active AMI smart meter and daily consumption data.
- Home Assistant with the Recorder integration enabled. Version 0.1.2 was tested on Home Assistant 2026.9.2; older versions have not been verified.
- Internet access to `api.pwl.kraken.tech`.

## Installation

1. Download this repository using **Code → Download ZIP**, then extract it.
2. Locate your Home Assistant configuration directory: the directory containing `configuration.yaml` (usually `/config` on Home Assistant OS).
3. Create a `custom_components` directory inside it if necessary.
4. Copy the repository's entire `custom_components/portsmouth_water` directory into it. The result must look like this, with no extra nested directory:

   ```text
   config/
   ├── configuration.yaml
   └── custom_components/
       └── portsmouth_water/
           ├── __init__.py
           ├── manifest.json
           ├── config_flow.py
           └── ...
   ```

5. Run Home Assistant's configuration check, then restart Home Assistant.
6. Open **Settings → Devices & services → Add integration** and search for **Portsmouth Water**.
7. Enter your Portsmouth Water email and password. If you have multiple accounts, select the account to connect.

No YAML configuration is required. If the integration does not appear, refresh the browser after restarting and check Home Assistant's logs for `portsmouth_water` errors.

## Show daily usage in litres

1. Open the Energy dashboard's configuration and find **Water consumption**.
2. Add the imported statistic named **Portsmouth Water <meter number> usage**.
3. Open **Energy → Water** and select **Last 30 days** in the date picker to show daily bars.

Select the imported statistic rather than the **Latest daily usage** sensor: the sensor shows one day's total and is not a cumulative meter. The dashboard's period preference may need to be selected separately in other browsers.

## How the data works

The integration uses actual, complete daily records supplied by Portsmouth Water. It excludes estimated readings and incomplete days. Supplier hourly records can differ from daily totals, so daily records are treated as authoritative.

Home Assistant stores external statistics in hourly slots. Each complete daily total is placed in the day's final hour, preserving the calendar day's total. **This integration does not provide an hourly consumption breakdown**; use a date range that displays daily bars.

The initial import requests the last 30 days of available readings. Imported records are retained in Home Assistant's local storage. Each update rereads that window, deduplicates readings and recalculates totals to incorporate supplier corrections. An outage longer than 30 days can leave a gap; older missing readings are not automatically backfilled.

The potential-leak indicator reflects the supplier's flag on the latest complete daily record. It is not a live leak detector.

## Authentication and privacy

The password is used for sign-in and is not saved by the integration. Home Assistant stores the account email, account number and refresh token in its configuration entry, and stores imported consumption records locally. Treat Home Assistant's configuration and backups as private.

If authentication expires, Home Assistant will ask you to sign in again. Do not include credentials, tokens, account numbers or unredacted logs when reporting an issue.

## Updating and removing

To update, back up Home Assistant, replace `custom_components/portsmouth_water` with the new version, run the configuration check and restart.

To remove it, delete its entry from **Settings → Devices & services**, remove the Water consumption source from your Energy settings, and then remove the `custom_components/portsmouth_water` directory and restart. Historical Recorder statistics may remain until removed separately through Home Assistant.

## Support

This project is not affiliated with Portsmouth Water or Kraken. Supplier API changes may require updates. Report problems through [GitHub Issues](https://github.com/alexcroox/home-assistant-portsmouth-water/issues), including your Home Assistant version and a redacted error message.

## License

[MIT](LICENSE).
