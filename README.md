# detectomer - Software trigger on spectral power

<div style="margin-left:auto;margin-right:auto;text-align:center">
<img src="https://raw.githubusercontent.com/xaratustrah/detectomer/master/rsrc/detectomer.png" width="512">
</div>

*detectomer* creates a software trigger above a certain threshold. Using sliders you can choose the area of interest. It uses the RTL-SDR driver to communicate with thee SDR device.

For more information on using SDR-RTL devices using python please refer to [pysdr.org](https://pysdr.org/content/rtlsdr.html). This code has been tested using NESDR-Mini-2+, NESDR Nano 2 and NESDR SMArt v5. More info about these devices can be found on the [NooELEC website](https://support.nooelec.com/hc/en-us/articles/360005805834-NESDR-Series).

## Installation

Before you install this code, make sure the driver is installed on your system:

```
sudo apt install rtl-sdr
```

then continue:

```
pip3 install -r requirements.txt
pip3 install .
```

For uninstalling you can type:

```
pip3 uninstall detectomer
```

## Licensing

Please see the file [LICENSE.md](./LICENSE.md) for further information about how the content is licensed.
