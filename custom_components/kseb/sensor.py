"""Support for KSEB Bill Payment Gateway.

configuration.yaml

sensor:
  - platform: kseb
    consumerno: 1234567890
    username: xxyyzz123
    password: yourpassword
    scan_interval: 3600
"""
from datetime import timedelta,datetime
import requests,json,untangle,logging,codecs,time
import voluptuous as vol
from bs4 import BeautifulSoup
from homeassistant.components.sensor import PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle
from homeassistant.helpers.entity import Entity

from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_RESOURCES
)

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://wss.kseb.in/selfservices/"
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=3600)

SENSOR_PREFIX = 'KSEB '
SENSOR_TYPES = {
    'consumerNo': ['Consumer Number', '', 'mdi:numeric'],
    'billMonth': ['Bill Month',  '', 'mdi:calendar'],
    'billDate': ['Bill Date',  '', 'mdi:calendar'],
    'totalConsumption': ['Total Consumption', 'Units', 'mdi:counter'],
    'billAmount': ['Bill Amount',  '₹', 'mdi:cash-100'],
    'dueDate': ['Due Date',  '', 'mdi:calendar']
}

CONF_CONSUMERNO = "consumerno"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_CONSUMERNO): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_RESOURCES, default=[]):
            vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)])
    }
)

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Setup the KSEB bill sensor."""
    consumer_no = config.get(CONF_CONSUMERNO)
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)

    try:
        data = KSEBBillData(consumer_no, username, password)
    except RunTimeError:
        _LOGGER.error("Unable to connect to KSEB Portal %s:%s",
                      BASE_URL)
        return False

    entities = []
    entities.append(KSEBBillSensor(data, "consumerNo", consumer_no))
    entities.append(KSEBBillSensor(data, "billMonth", consumer_no))
    entities.append(KSEBBillSensor(data, "billDate", consumer_no))
    entities.append(KSEBBillSensor(data, "totalConsumption", consumer_no))
    entities.append(KSEBBillSensor(data, "billAmount", consumer_no))
    entities.append(KSEBBillSensor(data, "dueDate", consumer_no))
    add_entities(entities)

class KSEBBillData(object):
    """Representation of a KSEB Bill."""

    def __init__(self, consumer_no, username, password):
        """Initialize the portal."""
        self.consumerno = consumer_no
        self.username = username
        self.password = password

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Update the data from the portal."""
        headers={"User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:81.0) Gecko/20100101 Firefox/81.0", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8", "Content-Type": "application/x-www-form-urlencoded"}
        headers["Referer"]=BASE_URL + "wssloginUser.do"
        login_data = "userId=" + self.username + "&passWord=" + self.password

        try:
            s = requests.Session();
            response = s.get(BASE_URL + "wssloginUser.do")
            response = s.post(BASE_URL + "login", data=login_data, headers=headers, timeout=10)

            option = "optionVal=" + self.consumerno
            response = s.post(BASE_URL + "billHistorycheck", data=option, headers=headers)

            jdata = json.loads(response.text)
            d = {}
            for i in jdata:
                if (i['billTypeCode'] == "RgCC"):
                    d['consumerNo'] = i['consumerNumber']
                    d['billMonth'] = datetime.strptime(i['billMonth'], '%Y%m').strftime('%b-%Y')
                    d['billDate'] =  time.strftime('%d-%m-%Y', time.localtime(i['billDate']/1000))
                    d['dueDate'] =  time.strftime('%d-%m-%Y', time.localtime(i['dueDate']/1000))
                    d['totalConsumption'] = i['totalConsumption']
                    d['billAmount'] = i['billAmnt']
                    break

            self.data = json.loads(json.dumps(d));
            print(self.data)
        except requests.ConnectionError as e:
            print("OOPS!! Connection Error. Make sure you are connected to Internet. Technical Details given below.\n")
            print(str(e))
        except requests.Timeout as e:
            print("OOPS!! Timeout Error")
            print(str(e))
        except requests.RequestException as e:
            print("OOPS!! General Error")
            print(str(e))
        except KeyboardInterrupt:
            print("Someone closed the program") 

class KSEBBillSensor(Entity):
    """Representation of a KSEBBill sensor."""

    def __init__(self, data, sensor_type, consumer_no):
        """Initialize the sensor."""
        self.data = data
        self.type = sensor_type
        self._name = SENSOR_PREFIX + SENSOR_TYPES[sensor_type][0]
        self._unit = SENSOR_TYPES[sensor_type][1]
        self._inferred_unit = None
        self._state = None
        self.update()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return SENSOR_TYPES[self.type][2]

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        if not self._unit:
            return self._inferred_unit
        return self._unit

    def update(self):
        """Get the latest data and use it to update our sensor state."""
        self.data.update()
        billdetails = self.data.data
        if (billdetails):
            if self.type == 'consumerNo':
                self._state = billdetails['consumerNo']
            elif self.type == 'billMonth':
                self._state = billdetails['billMonth']    
            elif self.type == 'billDate':
                self._state = billdetails['billDate']
            elif self.type == 'dueDate':
                self._state = billdetails['dueDate']    
            elif self.type == 'totalConsumption':
                self._state = billdetails['totalConsumption']    
            elif self.type == 'billAmount':
                self._state = billdetails['billAmount']    
