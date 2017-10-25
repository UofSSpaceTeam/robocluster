from robocluster import Device

device = Device('gps', '224.0.0.64:32464')

gps = GPS()

@device.every(1)
async def publish_gps():
    await device.publish('lat-lon', gps.lat_lon)

@device.on('gps/lat-lon')
def print_gps(event, data):
    print(data)

device.run_forever()
