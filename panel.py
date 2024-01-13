from luma.core.interface.serial import i2c, spi, pcf8574
from luma.core.interface.parallel import bitbang_6800
from luma.core.render import canvas
from luma.oled.device import sh1106
from time import sleep
from PIL import ImageFont
from datetime import datetime
from datetime import datetime, timedelta
import asyncio
from gpiozero import Button
import toml
import aiohttp
import sys, locale


#------------------------------------------------------------------------------
def next_second(secs=0):
    dt = datetime.now()
    dn = dt.replace(microsecond=0) + timedelta(seconds=secs+1)
    return (dn - datetime.now()).total_seconds()


#------------------------------------------------------------------------------
# time / date display
async def draw_time(device):

    # prepare fonts
    font1 = ImageFont.truetype("assets/FreePixel.ttf", 32)
    font2 = ImageFont.truetype("assets/FreePixel.ttf", 16)

    while True:
        with canvas(device) as draw:
            now = datetime.now()
            draw.text(
                (device.width/2, device.height/2),
                now.strftime("%H:%M:%S"),
                fill="white",
                anchor="mm",
                font=font1
            )
            draw.text(
                (device.width/2, device.height/2+24),
                now.strftime("%a %d/%m/%Y").upper(),
                fill="white",
                anchor="mm",
                font=font2
            )
        await asyncio.sleep(next_second())


#------------------------------------------------------------------------------
# retrieve Hassi data
async def hassi_request(config):

    # auth headers and base URL
    headers = { 'Authorization': 'Bearer ' + config['hassi']['token'] }
    base = config['hassi']['url']

    # aiohttpd sessions
    session = aiohttp.ClientSession()

    # task loop    
    while True:
        for entity in config['hassi']['sources']:
            try:
                response = await session.get(
                  '/'.join([base, entity['entity_id']]),
                  headers=headers
                )
                assert response.status == 200
                data = await response.json()
                print(entity['label'], data['state'])
            except Exception as err:
                print(entity['label'], 'ERROR ({0})'.format(err))
        try:
          await asyncio.sleep(next_second(30))
        except asyncio.CancelledError:
          await session.close()
          break


#------------------------------------------------------------------------------
async def main():

    # read configuration
    with open('config.toml', 'r') as f:
        config = toml.load(f)

    # initialize the display hardware
    serial = spi(device=0, port=0)
    device = sh1106(serial)

    # set locale
    locale.setlocale(locale.LC_TIME, '')

    # create tasks
    t1 = asyncio.create_task(draw_time(device))
    t2 = asyncio.create_task(hassi_request(config))

    # finish loop event
    finish = asyncio.Event()
    
    # exit upon keypress
    button1 = Button(21)
    button1.when_pressed = lambda x: finish.set()
    
    # ...and wait forever
    await finish.wait()
    t1.cancel()
    t2.cancel()


asyncio.run(main())
