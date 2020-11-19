## HASS (HomeAssist) assister

### Background

Reasoning behind this project was primarily allow me adding more functionalities triggered by MQTT events such as controlling TV (at that time being developed was not fulfilling all needs) and on a more "wildcard" basis control lights without adding too much to the existing HomeAssistant yaml-configuration (that at that time was too limited for me).
In future have in mind using the scheduler to e.g. poll external service (garmin etc) and supply these as MQTT messages to be captured by HomeAssistant.
Also set rules to e.g. publish messages after period of time when other found for e.g. turn of lights after period of time.

### High level design

```
+------------+-----------+
|            |           |
|scheduler   |  REST-API |
+------------+-----------+
|     hass_assister      |
|                        |
|                        |
|                        |
+------------+-----------+
             ^
             |   listen/publish
             |
             |
             v
+------------+------------+
|                         |
|                         |
|      MQTT               |
|                         |
|                         |
+------------+------------+
             ^
             |
             |
+------------v------------+
|                         |
|                         |
|   Home Assistant        |
|                         |
|                         |
+-------------------------+

```

### Installation

**Step 1** - clone the repo, and create a `config` directory where `hass_assister.yaml` configuration will be created

```shell script
git clone ________
cd hass_assister
```
**Step 2** - build and start docker container

```shell script
docker build -t hass_assister . && docker run -p 8000:8000 -v /tmp:/root/.config/hass_assister.settings --name hass_assister hass_assister 
```

**Step 3** - update configuration and restart container

```shell script
docker restart hass_assister 
```

#### Configuration file

##### Sample

```yaml
# This configuration allows this service to download "device" and "sensors" from HomeAssistant.
# The MQTT broker is being used to detect changes, while the hass_url with credentials used 
# for the service to collect the proper names for these when e.g. publishing other display devices (such as kodi)
hass_url: http://localhost:8123
hass_api_key: ''
hass_update_frequency_seconds: 60
mqtt_broker: localhost
mqtt_user: ''
mqtt_password: ''

# If you extend the source with custom component this allows you to schedule to run these in intervals
# Below is an included sample that will generate a tick
initial_scheduled_tasks:
- - hass_assister.ping
  - interval
  - seconds: 60
    id: tick

# If you own a Philips TV including Android OS with the below details
# you will be able to control it using the REST API that this service supply.
# How to obtain credentials could be found if you look at this project https://github.com/eslavnov/pylips
# MAC address is used to wake-on-lan and should be possible for you to get from your router
philips_ip: ''
philips_user: ''
philips_password: ''
philips_mac: ''

# This gives support to allow events to automatically be sent to "dummy devices"
# Read and use this project if you find use for this https://github.com/engdan77/dummy_screen
dummy_display:
  enabled: false
  address: 127.0.0.1
  port: 9999

# If you own a Kodi device, you can enable and specify its IP and port to allow "notifications" to be sent there
# E.g. when temperature changes etc
kodi_display:
  enabled: false
  address: 127.0.0.1
  port: 9999

# With the extension of new components this will eventually increase.
# With the below the keys are "topic" that the REST API will recognize and trigger following components
mqtt_functions:
  tv_start_media: hass_assister.controllers.tv.start_media
  tv_start_channel: hass_assister.controllers.tv.start_channel
  tv_command: hass_assister.controllers.tv.command
  lights_control: hass_assister.controllers.light.control_lights

# If you have reasons to "on-the-fly" allow this service to listen and republish MQTT topic/messages
# It also allows you to use regex groups to change certain parts, groups are represnted by \1 (Python-re standard)
mqtt_replacement:
  ? - /from_topic_(..)
    - from_message
  : - /to_topic_\1
    - to_message

# This allows you to "on-the-fly" allow this service to listen to certain MQTT topic/messages
# And after a timer have a new topic/message topic published. This is for example useful when
# you like to create specific lights to turn off after a period of time
mqtt_timer:
  timer_id:
  - /on_topic
  - on_message
  - 120
  - /new_topic
  - new_message
  my_test:
  - /light
  - on
  - 5
  - /light
  - off
```

#### Sample of MQTT topics and messages

```
# TV commands found in available_commands.json
function/tv_command volume_up
function/tv_start_media smb://192.168.1.1/sample.mp4
function/tv_start_channel 720

# Lights, turn on/off, cycle and blink
/lights_control turn_on
/lights_control turn_on_mylamp_and_otherlamp
/lights_control start_blink
/lights_control start_cycle
```
