from robocluster import Device

client = Device('client', 'Manager')

@client.task
async def stop_printer():
    await client.sleep(1)
    await client.publish('stop', 'printer')

@client.task
async def create_process():
    await client.sleep(2)
    call = {'name': 'shell',
            'command': 'bash',
            'type': 'RunOnce'
            }
    print('Creating: {}'.format(call))
    await client.publish('createProcess', call)

@client.task
async def start_printer():
    await client.sleep(4)
    await client.publish('stop', 'shell')
    await client.publish('start', 'printer')

try:
    client.run()
except KeyboardInterrupt:
    async def shutdown():
        await client.publish('stop', 'printer')
        print('stopped')
    loop = client._loop
    loop.run_until_complete(shutdown())
