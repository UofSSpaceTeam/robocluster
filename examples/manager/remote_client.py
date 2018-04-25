from robocluster import Device

client = Device('client', 'Manager')

@client.task
async def run_termite():
    call = {'name': 'shell',
            'command': 'bash'
            }
    print('publishing {}'.format(call))
    await client.publish('createProcess', call)
    await client.sleep(1)
    await client.publish('stop', call)

client.run()
