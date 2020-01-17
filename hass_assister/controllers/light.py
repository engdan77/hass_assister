import magichue


def check_light(host):
    light = magichue.Light(host)
    print(light.on)
    print(light.rgb)
    print(light.saturation)
    print(light.is_white)
    light.is_white = True
    light.on = True
    light.rgb = (100, 100, 100)
    # light.is_white = False
    # light.rgb = (100, 100, 100)
    # light.rgb(255, 0, 0)
    # light.brightness = 20
