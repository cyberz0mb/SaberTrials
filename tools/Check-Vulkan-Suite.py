"""Run renderer checks serially so clients do not compete for GPU time or loopback ports."""
from importlib import import_module
c=import_module('Check-Vulkan')
CASES=[('rd-vulkan',s) for s in ('scene','intel','custom','restart','missing','incompatible','no-driver','profile')]
CASES += [(r,s) for r in ('rd-vanilla','rd-rend2') for s in ('scene','profile')]

def run():
    for renderer,scenario in CASES:c.local(renderer,scenario)
    import_module('Check-Vulkan-Network').run()

if __name__=='__main__':run()
