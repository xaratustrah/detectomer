# detectomer - Software Defined Radio based conditional accelerator trigger on spectral power

<div style="margin-left:auto;margin-right:auto;text-align:center">
<img src="https://raw.githubusercontent.com/xaratustrah/detectomer/master/rsrc/detectomer.png" width="512">
</div>

*detectomer* creates a software trigger above a certain spectral power threshold. This is used to send a trigger to the accelerator beam process through the REST interface.

It uses the RTL-SDR driver to communicate with thee SDR device. For more information on using SDR-RTL devices using python please refer to [pysdr.org](https://pysdr.org/content/rtlsdr.html). This code has been tested using NESDR-Mini-2+, NESDR Nano 2 and NESDR SMArt v5. More info about these devices can be found on the [NooELEC website](https://support.nooelec.com/hc/en-us/articles/360005805834-NESDR-Series).

## Installation

#### Driver

Before you install this code, make sure the driver is installed on your system:

```
sudo apt install -y rtl-sdr
```

You should be able to use the device as a normal user. If you have permission problems, please follow the instructions available [on this site](https://pysdr.org/content/rtlsdr.html#rtl-sdr-background). In short:

first find out the vendor ID of your device using `lsusb`, which will look something like this:

```
Bus 003 Device 017: ID 0bda:2838 Realtek Semiconductor Corp. RTL2838 DVB-T
```

then you create a file `/etc/udev/rules.d/10-rtl-sdr.rules` with the content from the vendor ID:

```
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2838", MODE="0666"
```

then restart `udev`:

```
sudo udevadm control --reload-rules
sudo udevadm trigger
```

#### Rest of the Code

Finally continue with:

```
pip3 install -r requirements.txt
pip3 install .
```

## Usage

#### sdr2zmq

There are two codes, one of them reads out the data and publishes on a ZMQ port:

```
sdr2zmq --config path/to/sdr2zmq_cfg.toml
```

#### detectormer GUI

In another terminal you can run the GUI program `detectomer`, you will be required to load the configuration file here as well.

- The GUI allows for setting sliders for the region you are expecting a peak to appear.
- There are some GUI controls that allow for manipulation of graph, like the reference level.
- The GUI triggers if a peak appears in the defined window. The status bar will become red for 300ms.
- The invert function inverts the graph as well as logical signal.
- The actual activation message is sent over REST if the checkbox is clicked. In this case, the status bar wil be purple. The duration of the REST signal can be set using the GUI. After this time has ellapsed, the release signal is sent via the REST interface.


#### Configuration files

Both parts have TOML files for their configuration.

Please note that the sampling rate and center frequency should be the same for both for the measurement to be meaningful.

Sampling rates depend on RTL-SDR chip and follow the same range requirements either between 230-300 kHz, or between 900-3.2 MHz as stated [on this site](https://pysdr.org/content/rtlsdr.html#rtl-sdr-background). Higher sampling rates cause flickering on the screen. 

Gain: with RTL-SDR devices, possible gain settings are either `auto` or any of the following values: 

```
0.0, 0.9, 1.4, 2.7, 3.7, 7.7, 8.7,
12.5, 14.4, 15.7, 16.6, 19.7, 20.7, 22.9, 25.4,
28.0, 29.7, 32.8, 33.8, 36.4, 37.2, 38.6, 40.2,
42.1, 43.4, 43.9, 44.5, 48.0, 49.6
```

## Uninstall

For uninstalling you can type:

```
pip3 uninstall detectomer
```

## Licensing

Please see the file [LICENSE.md](./LICENSE.md) for further information about how the content is licensed.
