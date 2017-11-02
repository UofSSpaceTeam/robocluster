import apm
import asyncio
import logging

logging.basicConfig(level=logging.INFO)


class RestartOnCrash(apm.ProcessDefinition):
    stdout = apm.PIPE
    stderr = apm.PIPE
    stdin = apm.DEVNULL
    
    def on_exit(self, returncode: int):
        if returncode != 0:
            return apm.restart(self)
        else:
            return apm.release(self)  

class RunOnce(apm.ProcessDefinition):
    stdout = apm.PIPE
    stderr = apm.PIPE
    stdin = apm.DEVNULL
    
    def on_exit(self, returncode: int):
        return apm.release(self)

def ParentProcess_ROC(RestartOnCrash):
    children = []
    exclude_keywords = [*RestartOnCrash.exclude_keywords, 'children']
    
    def on_exit(self, returncode: int):
        for child in self.children:
            apm.kill(child)
        return super().on_exit(returncode)


pp1 = RestartOnCrash('python examples/processes/print_periodically.py 3 30'.split(' '), name='pp1')
pp2 = RestartOnCrash('python examples/processes/print_periodically.py 3 15'.split(' '), name='pp2')
cp1 = RestartOnCrash('python examples/processes/crash_periodically.py 2 12'.split(' '), name='cp1')
cp2 = RestartOnCrash('python examples/processes/crash_periodically.py 3 30'.split(' '), name='cp2')
master = ParentProcess_ROC(args='python examples/processes/print_periodically.py 3 10'.split(' '), name='master', children=[pp1, pp2, cp1, cp2])

for proc in [pp1, pp2, cp1, cp2, master]:
    apm.register(proc)

loop = asyncio.get_event_loop()
loop.run_forever()
