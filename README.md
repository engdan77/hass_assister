**Installation using Docker**

`docker build -t hass_assister . && docker run -d -v $(pwd)/config:/root/.config/hass_assister.settings --name hass_assister hass_assister && docker logs -f hass_assister`