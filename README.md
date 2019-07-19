**Installation using Docker**

`docker build -t hass_assister .
&& docker run
-v [local path to config]:/root/.config/hass_assister.settings
--name hass_assister
hass_assister `