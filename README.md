Free Mobile SMS XA for Home Assistant
A custom component for Home Assistant to send notifications via Free Mobile SMS, supporting multiple phone lines with custom service names and status sensors.
Installation

Copy the custom_components/freesmsxa folder to your Home Assistant configuration directory under custom_components/.
Restart Home Assistant.
Go to Settings > Devices & Services > Add Integration and search for "Free Mobile SMS XA".
Enter your Free Mobile username, SMS API access token, and an optional custom name for the notification service.
Repeat the process to add additional phone lines.

Configuration

username: Your Free Mobile account username.
access_token: Your Free Mobile SMS API access token.
name (optional): A custom name for the notification service (e.g., "ligne1"). If not provided, defaults to freesmsxa_<username>.

Each configured phone line creates:

A notification service (e.g., notify.ligne1 or notify.freesmsxa_12345678).
A sensor entity (e.g., sensor.freesmsxa_12345678) showing the API status.

Usage
Use the notification service in automations or scripts. For example, with a custom name ligne1:
service: notify.ligne1
data:
  message: "Test notification from Home Assistant"

Check the sensor for the API status:
entity_id: sensor.freesmsxa_12345678

Requirements

freesms Python library (version >=0.2.1).

License
GNU Lesser General Public License v2.1 (LGPL-2.1)
Documentation
For more details, see the GitHub repository.
