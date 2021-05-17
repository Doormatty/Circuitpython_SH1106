import time
from micropython import const
import adafruit_framebuf

SET_CONTRAST = const(0x81)
SET_ENTIRE_ON = const(0xa4)
SET_DISP_ALLON = const(0xa5)
SET_NORM = const(0xa6)
SET_NORM_INV = const(0xa7)
SET_DISP_OFF = const(0xae)
SET_DISP_ON = const(0xaf)
SET_MEM_ADDR = const(0x20)
SET_COL_ADDR = const(0x21)
SET_PAGE_ADDR = const(0x22)
SET_PAGE_ADDRESS = const(0xb0)
SET_DISP_START_LINE = const(0x40)
SET_SEG_REMAP = const(0xa1)
SET_MUX_RATIO = const(0xa8)
SET_COMSCANDEC = const(0xc8)
SET_COMSCANINC = const(0xc0)
SET_DISP_OFFSET = const(0xd3)
SET_COM_PIN_CFG = const(0xda)
SET_DISP_CLK_DIV = const(0xd5)
SET_PRECHARGE = const(0xd9)
SET_VCOM_DESEL = const(0xdb)
SET_CHARGE_PUMP = const(0x8d)
SET_LOW_COLUMN = const(0x00)
SET_HIGH_COLUMN = const(0x10)


class _SH1106:
    """Base class for SH1106 display driver"""

    def __init__(self, framebuffer, width, height, external_vcc, reset):
        self.framebuf = framebuffer
        self.fill = self.framebuf.fill
        self.pixel = self.framebuf.pixel
        self.line = self.framebuf.line
        self.text = self.framebuf.text
        self.scroll = self.framebuf.scroll
        self.blit = self.framebuf.blit
        self.vline = self.framebuf.vline
        self.hline = self.framebuf.hline
        self.fill_rect = self.framebuf.fill_rect
        self.width = width
        self.height = height
        self.external_vcc = external_vcc
        # reset may be None if not needed
        self.reset_pin = reset
        if self.reset_pin:
            self.reset_pin.switch_to_output(value=0)
        # Note the subclass must initialize self.framebuf to a framebuffer.
        # This is necessary because the underlying data buffer is different
        # between I2C and SPI implementations (I2C needs an extra byte).
        self.poweron()
        self.init_display()

    def init_display(self):
        """Base class to initialize display"""
        for cmd in (
                SET_DISP_OFF,  # Display Off
                SET_DISP_CLK_DIV, 0xF0,  # Ratio
                SET_MUX_RATIO, 0x3F,  # Multiplex
                SET_DISP_OFFSET, 0x00,  # No offset
                SET_DISP_START_LINE | 0x00,  # Start line
                SET_CHARGE_PUMP, 0x10 if self.external_vcc else 0x14,  # Charge pump
                SET_MEM_ADDR, 0x00,  # Memory mode, Horizontal
                SET_PAGE_ADDRESS,  # Page address 0
                SET_COMSCANDEC,  # COMSCANDEC
                SET_LOW_COLUMN,  # SETLOWCOLUMN
                SET_HIGH_COLUMN,  # SETHIGHCOLUMN
                SET_COM_PIN_CFG, 0x02 if self.height == 32 else 0x12,  # SETCOMPINS
                SET_CONTRAST, 0x9f if self.external_vcc else 0xcf,  # Contrast maximum
                SET_SEG_REMAP,  # SET_SEGMENT_REMAP
                SET_PRECHARGE, 0x22 if self.external_vcc else 0xf1,  # Pre Charge
                SET_VCOM_DESEL, 0x20,  # VCOM Detect 0.77*Vcc
                SET_ENTIRE_ON,  # DISPLAYALLON_RESUME
                SET_NORM,  # NORMALDISPLAY
                SET_DISP_ON):  # on
            self.write_cmd(cmd)
        self.fill(0)
        self.show()

    def poweroff(self):
        """Turn off the display (nothing visible)"""
        self.write_cmd(SET_DISP_OFF)

    def contrast(self, contrast):
        """Adjust the contrast"""
        self.write_cmd(SET_CONTRAST)
        self.write_cmd(contrast)

    def invert(self, invert):
        """Invert all pixels on the display"""
        if invert:
            self.write_cmd(SET_NORM_INV)
        else:
            self.write_cmd(SET_NORM)

    def write_framebuf(self):
        """Derived class must implement this"""
        raise NotImplementedError

    def write_cmd(self, cmd):
        """Derived class must implement this"""
        raise NotImplementedError

    def poweron(self):
        "Reset device and turn on the display."
        if self.reset_pin:
            self.reset_pin.value = 1
            time.sleep(0.001)
            self.reset_pin.value = 0
            time.sleep(0.010)
            self.reset_pin.value = 1
            time.sleep(0.010)
        self.write_cmd(SET_DISP_ON)

    def show(self):
        """Update the display"""
        self.write_framebuf()


class SH1106_I2C(_SH1106):
    """
    I2C class for SH1106

    :param width: the width of the physical screen in pixels,
    :param height: the height of the physical screen in pixels,
    :param i2c: the I2C peripheral to use,
    :param addr: the 8-bit bus address of the device,
    :param external_vcc: whether external high-voltage source is connected.
    :param reset: if needed, DigitalInOut designating reset pin
    """

    def __init__(self, width, height, i2c, *, addr=0x3c, external_vcc=False, reset=None):
        self.i2c_bus = i2c
        self.addr = addr
        self.temp = bytearray(2)
        self.temp[0]= 0x00 # Co = 0, D/C = 0
        # Add an extra byte to the data buffer to hold an I2C data/command byte to use hardware-compatible I2C
        # transactions.  A memoryview of the buffer is used to mask this byte from the framebuffer operations
        # (without a major memory hit as memoryview doesn't copy to a separate buffer).
        self.buffer = bytearray(((height // 8) * width) + 1)
        #self.buffer[0] = 0x40  # Set first byte of data buffer to Co=0, D/C=1
        framebuffer = adafruit_framebuf.FrameBuffer1(memoryview(self.buffer)[1:], width, height)
        super().__init__(framebuffer, width, height, external_vcc, reset)

    def write_cmd(self, cmd):
        """Send a command to the I2C device"""
        self.temp[1] = cmd
        self.i2c_bus.try_lock()
        self.i2c_bus.writeto(self.addr, self.temp)

    def write_cmd_nolock(self, cmd):
        """Copy of write_cmd that doesn't bother to check the lock"""
        self.temp[1] = cmd
        self.i2c_bus.writeto(self.addr, self.temp)

    def write_framebuf(self):
        """write to the frame buffer via I2C"""
        self.i2c_bus.try_lock()
        s_time = time.monotonic_ns()
        write = self.i2c_bus.writeto
        write_cmd = self.write_cmd_nolock
        for page in (0,2,4):
            page_mult = page << 7
            write_cmd(0xB0 + page)  # page address
            write_cmd(0x02)  # lower column address
            write_cmd(0x10)  # higher column address
            #write(self.addr, b'@' + self.buffer[page_mult:page_mult + self.width + 2])
            write(self.addr, b'@' + b'127'*130)
        self.i2c_bus.unlock()
        f_time=time.monotonic_ns()
        t_time=(f_time-s_time)/1000
        print(f"Total: {t_time}μs or {1000000/t_time}fps")
