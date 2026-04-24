# AVC_AvianFluModel

An epidemiological model of Highly Pathogenic Avian Flu (HPAI) with the Atlantic Veterinary College Hospital as a hub.

The purpose of the model is first to simulate the spread of HPAI from a small number of infected dairy cows imported to 
Prince Edward Island (PEI). Second, to simulate the effect of interventions in mitigating the spread of HPAI through
dairy farms including farmers and cows, the veterinary hospital, and into the wider community.

### Installation
1. Install Python (https://www.python.org). 
   1. We used version 3.11. 
   2. Everything should work with many other versions of Python3, but we haven't tested them.
2. (Optional) We recommend using a Python virtual environment (https://docs.python.org/3/tutorial/venv.html).
   1. The main benefit is that package installations won't interfere with other Python configurations you might have. 
   2. It may be necessary if you don't have admin/root permissions on your computer.
   3. Simple case when everything works and assuming you want to call your environment `hpai-env`
      1. `> python -m venv hpai-env`
      2. `> source hpai-env/bin/activate` (Linux and MacOSX, see website for Windows)
3. Install the Mesa package. 
   1. We use version 3.1.5. We haven't tested later versions, other v3.x versions probably work?
   2. We used `pip install -U mesa[rec]==3.1.5` to install the recommended dependency packages.
   3. Unfortunately the latest version of the Starlette dependency causes an error, so we have to install an old version:
      1. `> pip uninstall starlette`
      2. `> pip install starlette==0.45.3`
   4. And the `openpyxl` package to use Excel has to be installed separately:
      1. `> pip install openpyxl`
4. Clone or download the AvianFlu package.
   1. To download click the big green *Code* button above and use the *Download ZIP* link in the dropdown
   2. To clone using Git
      1. Change to the directory where you want the model code
      2. `> git clone https://github.com/modailmara/AVC_AvianFluModel.git`

### Run the visual model
1. Change to the directory where you put the code, then into the *AVC_AvianFluModel* directory
2. `> solara run app.py`
   1. This will open a web page in your default web browser. Use the controls on the left to interact with the 
   visualisation.

### Run a scenario
