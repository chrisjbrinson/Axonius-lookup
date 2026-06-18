from flask import Flask, render_template_string, request
import requests
import os
import logging

app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

AXONIUS_URL = "https://AXONIUS-URL:443/api/v2/assets/devices"  


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Axonius Device Lookup</title>
  <style>
    body {
      font-family: system-ui, sans-serif;
      background-color: #121212;
      color: #e0e0e0;
      padding: 40px;
    }
    h1 { color: #FF0000; }
    form { margin-bottom: 20px; }
    input, select {
      padding: 8px 12px;
      font-size: 1rem;
      border-radius: 6px;
      border: none;
      margin-right: 8px;
    }
    button {
      padding: 8px 16px;
      background-color: #FF0000;
      border: none;
      color: black;
      font-weight: bold;
      border-radius: 6px;
      cursor: pointer;
    }
    table {
      border-collapse: collapse;
      margin-top: 20px;
      width: 80%;
      max-width: 700px;
    }
    th, td {
      border: 1px solid #333;
      padding: 8px 12px;
    }
    th {
      text-align: left;
      background-color: #1e1e1e;
    }
  </style>
</head>
<body>
  <h1>Axonius Lookup</h1>
  <form method="GET">
    <label for="search_type">Search by:</label>
    <select name="search_type" id="search_type">
      <option value="hostname" {% if search_type == 'hostname' %}selected{% endif %}>Hostname</option>
      <!--<option value="ip" {% if search_type == 'ip' %}selected{% endif %}>IP Address</option>-->
      <!--<option value="user" {% if search_type == 'user' %}selected{% endif %}>Username</option>-->
    </select>
    <input name="search_value" placeholder="Enter search value..." value="{{ search_value or '' }}">
    <button type="submit">Search</button>
  </form>

  {% if error %}
    <p style="color: red;">{{ error }}</p>
  {% endif %}

  {% if results %}
    <table>
      <tr><th>Hostname</th><th>OS Version</th><th>Last AD Logon</th><th>IP Addresses</th><th>Site</th></tr>
      {% for result in results %}
        <tr>
          <td>{{ result.hostname }}</td>
          <td>{{ result.os_version }}</td>
          <td>{{ result.last_logon }}</td>
          <td>{{ result.ip_addresses }}</td>
          <td>{{ result.site }}</td>
        </tr>
      {% endfor %}
    </table>
  {% elif searched %}
    <p>No results found for {{ search_type }} "{{ search_value }}"</p>
  {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET"])
def lookup():
    search_type = request.args.get("search_type", "hostname")
    search_value = request.args.get("search_value")

    if not search_value:
        return render_template_string(HTML_TEMPLATE, search_type=search_type)

    # Map search type to Axonius fields
    field_map = {
        "hostname": "specific_data.data.name",
        "ip": "specific_data.data.network_interfaces.ips",
        "user": "specific_data.data.last_users",
    }

    field = field_map.get(search_type, "specific_data.data.name")

    headers = {
        "accept": "application/json",
        "api-key": "KEY",
        "api-secret": "SECRET",
        "content-type": "application/json"
    }
    payload = {

        
        "query": f'("specific_data.data.hostname" == regex("{search_value}", "i"))',
        "fields": [
            "specific_data.data.name",
            "specific_data.data.os.type_distribution_preferred",
            "specific_data.data.last_users",
            "specific_data.data.network_interfaces.ips_preferred",
            "adapters_data.crowd_strike_adapter.last_login_user",
            "adapters_data.gui.custom_subnet_site_name"
            
        ],
        "limit": 10
    }

    try:
        r = requests.post(AXONIUS_URL, headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        #logger.info(data)
        assets = data.get("assets", [])
        if not assets:
            return render_template_string(
                HTML_TEMPLATE,
                search_type=search_type,
                search_value=search_value,
                searched=True
            )

        results = []
        for a in assets:
            d = a.get("specific_data", {}).get("data", {})
            results.append({
                #"hostname": d.get("name"),
                "hostname": a["specific_data.data.name"],
                "os_version": a["specific_data.data.os.type_distribution_preferred"],
                "last_logon": a["adapters_data.crowd_strike_adapter.last_login_user"],
                #"last_user": d.get("last_user"),
                #"ad_groups": ", ".join(d.get("ad_groups", [])) if isinstance(d.get("ad_groups"), list) else d.get("ad_groups"),
                #"ou": a["adapters_data.active_directory_adapter.ou_path"],
                #"ip_addresses": ", ".join(d.get("network_interfaces.ips", [])) if isinstance(d.get("network_interfaces.ips"), list) else d.get("network_interfaces.ips")
                "ip_addresses": a["specific_data.data.network_interfaces.ips_preferred"],
                "site": a["adapters_data.gui.custom_subnet_site_name"]
            })
            logger.info(results)

        return render_template_string(
            HTML_TEMPLATE,
            search_type=search_type,
            search_value=search_value,
            results=results
        )

    except Exception as e:
        return render_template_string(
            HTML_TEMPLATE,
            error=str(e),
            search_type=search_type,
            search_value=search_value
        )


if __name__ == "__main__":
    app.run(debug=True)

