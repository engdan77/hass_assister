**Installation using Docker**

`docker build -t hass_assister .
&& docker run
-v [local path to config]:/app/config
--name hass_assister
hass_assister `