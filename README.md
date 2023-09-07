# TINET Bridge
This program makes the connection between your calculator and our main servers possible!  
[![wakatime](https://wakatime.com/badge/github/tkbstudios/tinet-bridge.svg)](https://wakatime.com/badge/github/tkbstudios/tinet-bridge)

> ⚠️ please ALWAYS update the bridge to the latest version!  
> by doing this you make sure that you have the latest security updates available!

## How to use
1. Clone this repository using `git clone https://github.com/tkbstudios/tinet-bridge`
2. Go to your cloned repository and run `pip3 install -r requirements.txt` inside your terminal (You need python3.11 and pip3 installed)
3. When pyserial has been installed, open the [TINET] program on your calculator.
4. When [TINET] has been opened, connect TINET to the machine you cloned the repository to.
5. If there's a little icon that looks like a USB and a checkmark, go ahead, if it is another icon, open an Issue [here](https://github.com/tkbstudios/ti84pluscenet-calc/issues)
6. run `python3 tinet-bridge.py`
7. Enter the COM port where your calculator has been connected. (Open Device Manager (Start → Control Panel → Hardware and Sound → Device Manager) Look in the Device Manager list, open the category "Ports", and find the matching COM Port)
8. Press enter when you have entered your COM port.
9. You should see some thing printed to the console like `Initing serial...`
10. When you get printed out on your sreen `Reading data from serial device...` you're good to go!
11. In [TINET] on your calculator, press [enter] to connect to your account. If you see a QR-code, it means you need to do the [steps to put your keyfile on your calculator!](https://github.com/tkbstudios/ti84pluscenet-calc#how-to-use)
